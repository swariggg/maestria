import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Usuario, VersionEvidencia, EntregaEvidencia, EvaluacionEvidencia, 
    AsignacionCurso, ActividadCurso, RegistroAuditoria, AsignacionTutor, CriterioEvaluacion, PuntajeCriterio
)
from app.schemas.pydantic_models import EvaluationCreate, EvaluationOut
from app.services.risk_engine import evaluate_applicant_risk
from app.services.process_emails import correo_evidencia_evaluada, correo_proceso_aprobado, correo_no_aprobado_por_intentos
from app.services.progress_service import (
    actualizar_estado_inscripcion, inscripcion_cerrada, CONV_PERMITE_CALIFICAR, mensaje_convocatoria,
    marcar_no_aprobado_por_intentos
)

RESULTADOS = ["APROBADO", "REQUIERE_CORRECCION", "RECHAZADO"]


def _validar_evaluador(db: Session, user: Usuario, inscripcion) -> None:
    """Califica el tutor asignado. El coordinador o el admin solo cuando el postulante no tiene tutor."""
    tutor = db.query(AsignacionTutor).filter(
        AsignacionTutor.inscripcion_id == inscripcion.id, AsignacionTutor.estado == "ACTIVO"
    ).first()
    if tutor:
        if user.id != tutor.tutor_id:
            raise HTTPException(
                status_code=403,
                detail=f"Este postulante tiene como tutor a {tutor.tutor.nombre_completo}; solo su tutor puede calificar."
            )
    elif user.rol.codigo == "TUTOR":
        raise HTTPException(status_code=403, detail="No es el tutor asignado de este postulante.")


def _puntaje_con_rubrica(db: Session, actividad: ActividadCurso, data: EvaluationCreate):
    """Con criterios, la nota es la suma de los puntajes por criterio. Sin criterios, la nota directa."""
    criterios = db.query(CriterioEvaluacion).filter(CriterioEvaluacion.actividad_id == actividad.id).all()
    if not criterios:
        if data.puntaje_obtenido is None:
            raise HTTPException(status_code=400, detail="Indique la calificación.")
        return float(data.puntaje_obtenido), []
    por_id = {c.id: c for c in criterios}
    recibidos = {p.criterio_id: p.puntaje for p in data.puntajes}
    faltan = [c.criterio for c in criterios if c.id not in recibidos]
    extra = [i for i in recibidos if i not in por_id]
    if faltan or extra:
        raise HTTPException(status_code=400, detail="Califique cada criterio de la rúbrica." + (f" Faltan: {', '.join(faltan)}." if faltan else ""))
    for cid, pts in recibidos.items():
        maximo = float(por_id[cid].puntaje_maximo)
        if pts < 0 or pts > maximo:
            raise HTTPException(status_code=400, detail=f"'{por_id[cid].criterio}' admite de 0 a {maximo:g} puntos.")
    return round(sum(recibidos.values()), 2), [(cid, pts) for cid, pts in recibidos.items()]


def _puntajes_out(evaluacion) -> list:
    return [
        {"criterio_id": p.criterio_id, "criterio": p.criterio.criterio, "puntaje": float(p.puntaje),
         "puntaje_maximo": float(p.criterio.puntaje_maximo)}
        for p in evaluacion.puntajes
    ]

router = APIRouter(prefix="/evaluaciones", tags=["Evaluaciones y Calificaciones"])

@router.post("", response_model=EvaluationOut)
def evaluate_evidence_version(
    data: EvaluationCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    version = db.query(VersionEvidencia).filter(VersionEvidencia.id == data.version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Versión de evidencia no encontrada.")

    entrega = version.entrega
    asig_curso = entrega.asignacion_curso
    inscripcion = asig_curso.inscripcion

    # Validar permisos
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para evaluar a este postulante.")

    if inscripcion_cerrada(inscripcion):
        raise HTTPException(status_code=400, detail=f"La inscripción está cerrada ({inscripcion.estado_proceso}); ya no admite calificaciones.")
    if inscripcion.convocatoria.estado not in CONV_PERMITE_CALIFICAR:
        raise HTTPException(status_code=400, detail=f"{mensaje_convocatoria(inscripcion.convocatoria)} No se pueden registrar calificaciones.")

    _validar_evaluador(db, current_user, inscripcion)
    if data.resultado not in RESULTADOS:
        raise HTTPException(status_code=400, detail=f"Resultado inválido. Use: {', '.join(RESULTADOS)}.")
    if version.id != max(v.id for v in entrega.versiones):
        raise HTTPException(status_code=400, detail="Solo se califica la última versión enviada.")

    actividad = entrega.actividad
    puntaje, puntajes = _puntaje_con_rubrica(db, actividad, data)
    if puntaje < 0 or puntaje > float(actividad.ponderacion):
        raise HTTPException(
            status_code=400,
            detail=f"La calificación ({puntaje:g}) debe estar entre 0 y la ponderación de la actividad ({float(actividad.ponderacion):g})."
        )

    evaluacion = db.query(EvaluacionEvidencia).filter(EvaluacionEvidencia.version_id == version.id).first()
    anterior = None
    if not evaluacion:
        evaluacion = EvaluacionEvidencia(version_id=version.id, evaluador_id=current_user.id)
        db.add(evaluacion)
    else:
        # Recalificar: solo quien calificó, y explicando por qué
        if evaluacion.evaluador_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"Solo {evaluacion.evaluador.nombre_completo}, que calificó esta versión, puede recalificarla.")
        motivo = (data.motivo_recalificacion or "").strip()
        if len(motivo) < 5:
            raise HTTPException(status_code=400, detail="Para cambiar una calificación escriba el motivo.")
        anterior = {"nota": float(evaluacion.puntaje_obtenido), "resultado": evaluacion.resultado}
        evaluacion.motivo_recalificacion = motivo
        db.query(PuntajeCriterio).filter(PuntajeCriterio.evaluacion_id == evaluacion.id).delete()
    evaluacion.puntaje_obtenido = puntaje
    evaluacion.resultado = data.resultado
    evaluacion.observaciones = data.observaciones
    evaluacion.recomendaciones = data.recomendaciones
    evaluacion.fecha_evaluacion = datetime.now()
    db.flush()
    for cid, pts in puntajes:
        db.add(PuntajeCriterio(evaluacion_id=evaluacion.id, criterio_id=cid, puntaje=pts))

    # Actualizar estado de la entrega
    entrega.estado_entrega = data.resultado
    entrega.actualizada_en = datetime.now()

    # Recalcular nota y aprobación del curso, y con ello el estado de la inscripción
    db.flush()
    acaba_de_aprobar = actualizar_estado_inscripcion(db, inscripcion, current_user.id)
    # Si agotó los intentos de una actividad obligatoria sin aprobarla, el proceso termina
    motivo_no_aprobado = None if acaba_de_aprobar else marcar_no_aprobado_por_intentos(db, inscripcion, current_user.id)

    db.commit()
    db.refresh(evaluacion)

    # Auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="RECALIFICAR_EVIDENCIA" if anterior else "EVALUAR_EVIDENCIA",
        entidad="EVALUACION_EVIDENCIA",
        entidad_id=str(evaluacion.id),
        datos_anteriores_json=json.dumps(anterior) if anterior else None,
        datos_nuevos_json=json.dumps({"nota": puntaje, "resultado": data.resultado,
                                      "motivo": evaluacion.motivo_recalificacion if anterior else None}, ensure_ascii=False)
    ))
    db.commit()

    # Una evidencia aprobada o rechazada cambia el riesgo del postulante
    evaluate_applicant_risk(db, inscripcion.id)
    db.refresh(evaluacion)
    correo_evidencia_evaluada(db, inscripcion, evaluacion)
    if acaba_de_aprobar:
        correo_proceso_aprobado(db, inscripcion)
    if motivo_no_aprobado:
        correo_no_aprobado_por_intentos(db, inscripcion, motivo_no_aprobado)
    db.refresh(evaluacion)

    return EvaluationOut(
        id=evaluacion.id,
        version_id=evaluacion.version_id,
        evaluador_id=evaluacion.evaluador_id,
        evaluador_nombre=current_user.nombre_completo,
        puntaje_obtenido=float(evaluacion.puntaje_obtenido),
        resultado=evaluacion.resultado,
        observaciones=evaluacion.observaciones,
        recomendaciones=evaluacion.recomendaciones,
        fecha_evaluacion=evaluacion.fecha_evaluacion,
        puntajes=_puntajes_out(evaluacion),
    )
