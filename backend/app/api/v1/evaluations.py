from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Usuario, VersionEvidencia, EntregaEvidencia, EvaluacionEvidencia, 
    AsignacionCurso, ActividadCurso, RegistroAuditoria
)
from app.schemas.pydantic_models import EvaluationCreate, EvaluationOut

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

    actividad = entrega.actividad
    if data.puntaje_obtenido < 0 or data.puntaje_obtenido > float(actividad.ponderacion):
        raise HTTPException(
            status_code=400, 
            detail=f"La calificación ({data.puntaje_obtenido}) debe estar entre 0 y la ponderación de la actividad ({actividad.ponderacion})."
        )

    # Crear o actualizar evaluación
    evaluacion = db.query(EvaluacionEvidencia).filter(EvaluacionEvidencia.version_id == version.id).first()
    if not evaluacion:
        evaluacion = EvaluacionEvidencia(
            version_id=version.id,
            evaluador_id=current_user.id,
            puntaje_obtenido=data.puntaje_obtenido,
            resultado=data.resultado,
            observaciones=data.observaciones,
            recomendaciones=data.recomendaciones,
            fecha_evaluacion=datetime.now()
        )
        db.add(evaluacion)
    else:
        evaluacion.puntaje_obtenido = data.puntaje_obtenido
        evaluacion.resultado = data.resultado
        evaluacion.observaciones = data.observaciones
        evaluacion.recomendaciones = data.recomendaciones
        evaluacion.evaluador_id = current_user.id
        evaluacion.fecha_evaluacion = datetime.now()

    # Actualizar estado de la entrega
    entrega.estado_entrega = data.resultado
    entrega.actualizada_en = datetime.now()

    # Recalcular nota acumulada del curso
    todas_entregas = db.query(EntregaEvidencia).filter(EntregaEvidencia.asignacion_curso_id == asig_curso.id).all()
    nota_acumulada = 0.0
    todas_aprobadas = True

    actividades_obligatorias = db.query(ActividadCurso).filter(
        ActividadCurso.curso_id == asig_curso.curso_id,
        ActividadCurso.es_obligatorio == True
    ).all()

    for ent in todas_entregas:
        if ent.versiones:
            ult_v = ent.versiones[-1]
            if ult_v.evaluacion:
                nota_acumulada += float(ult_v.evaluacion.puntaje_obtenido)

    asig_curso.nota_final = nota_acumulada
    
    # Verificar si cumple nota mínima del curso
    curso = asig_curso.curso
    if nota_acumulada >= float(curso.nota_minima):
        asig_curso.estado_aprobacion = "APROBADO"
    else:
        asig_curso.estado_aprobacion = "PENDIENTE"

    db.commit()
    db.refresh(evaluacion)

    # Auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="EVALUAR_EVIDENCIA",
        entidad="EVALUACION_EVIDENCIA",
        entidad_id=str(evaluacion.id),
        datos_nuevos_json=f'{{"nota": {data.puntaje_obtenido}, "resultado": "{data.resultado}"}}'
    ))
    db.commit()

    return EvaluationOut(
        id=evaluacion.id,
        version_id=evaluacion.version_id,
        evaluador_id=evaluacion.evaluador_id,
        evaluador_nombre=current_user.nombre_completo,
        puntaje_obtenido=float(evaluacion.puntaje_obtenido),
        resultado=evaluacion.resultado,
        observaciones=evaluacion.observaciones,
        recomendaciones=evaluacion.recomendaciones,
        fecha_evaluacion=evaluacion.fecha_evaluacion
    )
