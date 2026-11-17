from datetime import datetime, date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access, verify_program_access
from app.models.entities import (
    Usuario, Convocatoria, CursoPreparatorio, Inscripcion, AsignacionCurso, RegistroAuditoria, PerfilPostulante
)
from app.api.v1.profile import campos_faltantes, ETIQUETAS_CAMPO
from app.schemas.pydantic_models import EnrollmentCreate, OpenCallOut, MyEnrollmentOut
from app.services.notification_service import send_or_queue_notification
import json
from typing import Optional
from pydantic import BaseModel, Field
from app.services.process_emails import correo_proceso_aprobado, correo_retiro_solicitado, correo_retiro_resuelto
from app.services.progress_service import cerrar_alertas_inscripcion
from app.services.history_service import historial_inscripcion
from app.services.progress_service import (
    calcular_avance, ESTADOS_INSCRIPCION_CERRADA, CONV_PERMITE_INSCRIPCION,
    estado_inicial_inscripcion, marcar_documentacion_completa, inscritos_vigentes
)

router = APIRouter(prefix="/inscripciones", tags=["Postulantes e Inscripciones"])

# Solo una convocatoria ABIERTA recibe inscripciones; en EN_CURSO el preparatorio ya empezó
ESTADOS_CONVOCATORIA_ABIERTA = CONV_PERMITE_INSCRIPCION


def _cursos_activos(db: Session, convocatoria_id: int) -> List[CursoPreparatorio]:
    return db.query(CursoPreparatorio).filter(
        CursoPreparatorio.convocatoria_id == convocatoria_id,
        CursoPreparatorio.estado == "ACTIVO"
    ).all()


def _inscripciones_vigentes(db: Session, postulante_id: int) -> List[Inscripcion]:
    return db.query(Inscripcion).filter(
        Inscripcion.postulante_id == postulante_id,
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()


def _se_cruzan(a: Convocatoria, b: Convocatoria) -> bool:
    """Dos preparatorios se cruzan si sus fechas se superponen."""
    return a.fecha_inicio_preparatorio <= b.fecha_fin_preparatorio and b.fecha_inicio_preparatorio <= a.fecha_fin_preparatorio


def _impedimento(db: Session, postulante_id: int, conv: Convocatoria, vigentes: List[Inscripcion]):
    """Motivo por el que el postulante no puede inscribirse en la convocatoria, o None."""
    for v in vigentes:
        if v.convocatoria_id == conv.id:
            return "Ya se encuentra inscrito en esta convocatoria."
        if _se_cruzan(v.convocatoria, conv):
            return (f"Sus fechas se cruzan con su inscripción vigente en '{v.convocatoria.nombre}' "
                    f"({v.convocatoria.fecha_inicio_preparatorio} a {v.convocatoria.fecha_fin_preparatorio}).")
    if inscritos_vigentes(db, conv.id) >= conv.cupo_maximo:
        return "La convocatoria ya no tiene cupos disponibles."
    return None


@router.get("/convocatorias-abiertas", response_model=List[OpenCallOut])
def list_open_calls(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    hoy = date.today()
    convocatorias = db.query(Convocatoria).filter(
        Convocatoria.estado.in_(ESTADOS_CONVOCATORIA_ABIERTA),
        Convocatoria.fecha_apertura <= hoy,
        Convocatoria.fecha_cierre >= hoy
    ).order_by(Convocatoria.fecha_cierre.asc()).all()

    vigentes = _inscripciones_vigentes(db, current_user.id)

    resultado = []
    for conv in convocatorias:
        cursos = _cursos_activos(db, conv.id)
        impedimento = _impedimento(db, current_user.id, conv, vigentes)
        resultado.append(OpenCallOut(
            id=conv.id,
            codigo=conv.codigo,
            nombre=conv.nombre,
            programa_codigo=conv.programa.codigo,
            programa_nombre=conv.programa.nombre,
            fecha_apertura=conv.fecha_apertura,
            fecha_cierre=conv.fecha_cierre,
            fecha_inicio_preparatorio=conv.fecha_inicio_preparatorio,
            fecha_fin_preparatorio=conv.fecha_fin_preparatorio,
            cursos=[c.nombre for c in cursos],
            inscrito=any(v.convocatoria_id == conv.id for v in vigentes),
            modalidad=conv.modalidad or "EN_LINEA",
            cupo_maximo=conv.cupo_maximo or 0,
            cupos_disponibles=max(0, (conv.cupo_maximo or 0) - inscritos_vigentes(db, conv.id)),
            puede_inscribirse=impedimento is None,
            motivo_no_disponible=impedimento,
        ))
    return resultado


@router.get("/mias", response_model=List[MyEnrollmentOut])
def list_my_enrollments(
    current_user: Usuario = Depends(require_roles("POSTULANTE")),
    db: Session = Depends(get_db)
):
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.postulante_id == current_user.id
    ).order_by(Inscripcion.fecha_inscripcion.desc()).all()

    return [
        MyEnrollmentOut(
            id=insc.id,
            convocatoria_id=insc.convocatoria_id,
            convocatoria_nombre=insc.convocatoria.nombre,
            programa_nombre=insc.convocatoria.programa.nombre,
            fecha_inscripcion=insc.fecha_inscripcion,
            estado_proceso=insc.estado_proceso,
            cursos=[ac.curso.nombre for ac in insc.asignaciones_cursos],
            retiro_solicitado=insc.retiro_solicitado_en is not None and insc.estado_proceso != "RETIRADO",
            motivo_retiro=insc.motivo_retiro,
        )
        for insc in inscripciones
    ]


@router.get("/{inscripcion_id}/avance")
def get_enrollment_progress(
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cursos asignados a la inscripción y avance sumando todos ellos."""
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para consultar este postulante.")
    return calcular_avance(db, inscripcion)


@router.get("/{inscripcion_id}/historial")
def get_enrollment_history(
    inscripcion_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    """Todo lo que pasó con el postulante en esta inscripción, del evento más reciente al más antiguo."""
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para consultar este postulante.")
    return historial_inscripcion(db, inscripcion)


@router.patch("/{inscripcion_id}/documentacion-completa")
def mark_documentation_complete(
    inscripcion_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """El coordinador confirma que el postulante entregó los documentos obligatorios."""
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_program_access(current_user, inscripcion.convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene permiso sobre el programa de esta inscripción.")
    if inscripcion.estado_proceso != "DOCUMENTACION_PENDIENTE":
        raise HTTPException(status_code=400, detail=f"La inscripción no tiene documentación pendiente (estado {inscripcion.estado_proceso}).")
    if inscripcion.convocatoria.estado == "FINALIZADA":
        raise HTTPException(status_code=400, detail="La convocatoria está finalizada.")

    aprobado = marcar_documentacion_completa(db, inscripcion, current_user.id)
    db.commit()
    db.refresh(inscripcion)
    if aprobado:
        correo_proceso_aprobado(db, inscripcion)
    return {"inscripcion_id": inscripcion.id, "estado_proceso": inscripcion.estado_proceso, "aprobado": aprobado}


class RetiroSolicitud(BaseModel):
    motivo: str = Field(min_length=10, max_length=500)


class RetiroResolucion(BaseModel):
    aprobar: bool
    observacion: Optional[str] = Field(default=None, max_length=500)


class DatosAdministrativos(BaseModel):
    estado_pago: str = "PENDIENTE"
    tiene_beca: bool = False
    porcentaje_beca: Optional[int] = Field(default=None, ge=1, le=100)
    requiere_adaptaciones: bool = False
    nota_adaptaciones: Optional[str] = Field(default=None, max_length=500)


ESTADOS_PAGO = ["PENDIENTE", "PAGADO", "EXONERADO"]


def _inscripcion_del_programa(db: Session, user: Usuario, inscripcion_id: int) -> Inscripcion:
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_program_access(user, insc.convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene permiso sobre el programa de esta inscripción.")
    return insc


@router.post("/{inscripcion_id}/solicitar-retiro")
def request_withdrawal(
    inscripcion_id: int,
    data: RetiroSolicitud,
    current_user: Usuario = Depends(require_roles("POSTULANTE")),
    db: Session = Depends(get_db)
):
    """El postulante pide retirarse; el coordinador decide."""
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc or insc.postulante_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo puede pedir el retiro de su propia inscripción.")
    if insc.estado_proceso in ESTADOS_INSCRIPCION_CERRADA:
        raise HTTPException(status_code=400, detail=f"La inscripción ya está cerrada ({insc.estado_proceso}).")
    if insc.retiro_solicitado_en:
        raise HTTPException(status_code=400, detail="Ya tiene una solicitud de retiro pendiente.")
    insc.retiro_solicitado_en = datetime.now()
    insc.motivo_retiro = data.motivo.strip()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="SOLICITAR_RETIRO", entidad="INSCRIPCION", entidad_id=str(insc.id),
        datos_nuevos_json=json.dumps({"motivo": insc.motivo_retiro}, ensure_ascii=False)
    ))
    db.commit()
    correo_retiro_solicitado(db, insc)
    return {"mensaje": "Solicitud enviada. Coordinación le responderá por correo."}


@router.patch("/{inscripcion_id}/retiro")
def resolve_withdrawal(
    inscripcion_id: int,
    data: RetiroResolucion,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """Aprueba o rechaza la solicitud. Sin solicitud, aprobar retira al postulante directamente (con observación)."""
    insc = _inscripcion_del_programa(db, current_user, inscripcion_id)
    if insc.estado_proceso in ESTADOS_INSCRIPCION_CERRADA:
        raise HTTPException(status_code=400, detail=f"La inscripción ya está cerrada ({insc.estado_proceso}).")
    observacion = (data.observacion or "").strip() or None
    if not insc.retiro_solicitado_en:
        if not data.aprobar:
            raise HTTPException(status_code=400, detail="No hay una solicitud de retiro que rechazar.")
        if not observacion or len(observacion) < 5:
            raise HTTPException(status_code=400, detail="Para retirar al postulante sin solicitud, indique el motivo.")
        insc.motivo_retiro = observacion
    anterior = insc.estado_proceso
    if data.aprobar:
        insc.estado_proceso = "RETIRADO"
        cerrar_alertas_inscripcion(db, insc, "Cerrada automáticamente: el postulante se retiró.")
    insc.retiro_solicitado_en = None
    insc.actualizado_en = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="APROBAR_RETIRO" if data.aprobar else "RECHAZAR_RETIRO",
        entidad="INSCRIPCION", entidad_id=str(insc.id),
        datos_anteriores_json=json.dumps({"estado_proceso": anterior}),
        datos_nuevos_json=json.dumps({"estado_proceso": insc.estado_proceso, "observacion": observacion,
                                      "motivo": insc.motivo_retiro}, ensure_ascii=False)
    ))
    db.commit()
    db.refresh(insc)
    correo_retiro_resuelto(db, insc, data.aprobar, observacion)
    return {"inscripcion_id": insc.id, "estado_proceso": insc.estado_proceso}


@router.put("/{inscripcion_id}/administrativo")
def update_administrative_data(
    inscripcion_id: int,
    data: DatosAdministrativos,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """Pago, beca y adaptaciones. El pago se marca a mano: la app todavía no verifica pagos."""
    insc = _inscripcion_del_programa(db, current_user, inscripcion_id)
    if data.estado_pago not in ESTADOS_PAGO:
        raise HTTPException(status_code=400, detail=f"Estado de pago inválido. Use: {', '.join(ESTADOS_PAGO)}.")
    if data.tiene_beca and not data.porcentaje_beca:
        raise HTTPException(status_code=400, detail="Indique el porcentaje de la beca.")
    campos = ["estado_pago", "tiene_beca", "porcentaje_beca", "requiere_adaptaciones", "nota_adaptaciones"]
    antes = {c: getattr(insc, c) for c in campos}
    insc.estado_pago = data.estado_pago
    insc.tiene_beca = data.tiene_beca
    insc.porcentaje_beca = data.porcentaje_beca if data.tiene_beca else None
    insc.requiere_adaptaciones = data.requiere_adaptaciones
    insc.nota_adaptaciones = (data.nota_adaptaciones or "").strip() or None if data.requiere_adaptaciones else None
    despues = {c: getattr(insc, c) for c in campos}
    if antes != despues:
        db.add(RegistroAuditoria(
            usuario_id=current_user.id, accion="DATOS_ADMINISTRATIVOS", entidad="INSCRIPCION", entidad_id=str(insc.id),
            datos_anteriores_json=json.dumps(antes, ensure_ascii=False), datos_nuevos_json=json.dumps(despues, ensure_ascii=False)
        ))
    db.commit()
    return {"inscripcion_id": insc.id, **despues}


@router.post("", response_model=MyEnrollmentOut)
def enroll(
    data: EnrollmentCreate,
    request: Request,
    current_user: Usuario = Depends(require_roles("POSTULANTE")),
    db: Session = Depends(get_db)
):
    convocatoria = db.query(Convocatoria).filter(Convocatoria.id == data.convocatoria_id).first()
    if not convocatoria:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")

    hoy = date.today()
    if (convocatoria.estado not in ESTADOS_CONVOCATORIA_ABIERTA
            or not (convocatoria.fecha_apertura <= hoy <= convocatoria.fecha_cierre)):
        raise HTTPException(status_code=400, detail="La convocatoria no se encuentra abierta para inscripciones.")

    perfil = db.query(PerfilPostulante).filter(PerfilPostulante.usuario_id == current_user.id).first()
    faltan = campos_faltantes(current_user, perfil)
    if faltan:
        raise HTTPException(
            status_code=400,
            detail="Complete su perfil antes de inscribirse. Falta: " + ", ".join(ETIQUETAS_CAMPO.get(c, c) for c in faltan) + "."
        )

    impedimento = _impedimento(db, current_user.id, convocatoria, _inscripciones_vigentes(db, current_user.id))
    if impedimento:
        raise HTTPException(status_code=400, detail=impedimento)

    cursos = _cursos_activos(db, convocatoria.id)
    if not cursos:
        raise HTTPException(status_code=400, detail="La convocatoria aún no tiene cursos preparatorios configurados.")

    ahora = datetime.now()
    inscripcion = Inscripcion(
        postulante_id=current_user.id,
        convocatoria_id=convocatoria.id,
        fecha_inscripcion=ahora,
        estado_proceso=estado_inicial_inscripcion(db, convocatoria.id),
        nivel_riesgo="BAJO",
        motivo_riesgo="Inscripción reciente dentro del plazo reglamentario.",
        fecha_ultimo_avance=ahora,
        creado_en=ahora,
        actualizado_en=ahora
    )
    db.add(inscripcion)
    db.flush()

    # Asignación automática de todos los cursos activos de la convocatoria
    for curso in cursos:
        db.add(AsignacionCurso(
            inscripcion_id=inscripcion.id,
            curso_id=curso.id,
            estado="EN_CURSO",
            estado_aprobacion="PENDIENTE",
            fecha_asignacion=ahora
        ))

    client_ip = request.client.host if request.client else None
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="INSCRIPCION",
        entidad="INSCRIPCION",
        entidad_id=str(inscripcion.id),
        datos_nuevos_json=f'{{"convocatoria_id": {convocatoria.id}, "cursos_asignados": {len(cursos)}}}',
        ip_origen=client_ip
    ))
    db.commit()
    db.refresh(inscripcion)

    lista_cursos = "".join(f"<li>{c.nombre}</li>" for c in cursos)
    send_or_queue_notification(
        db=db,
        destinatario=current_user,
        tipo_evento="INSCRIPCION_CONFIRMADA",
        asunto=f"UIDE: Inscripción confirmada en {convocatoria.nombre}",
        cuerpo_html=(
            f"<p>Estimado(a) <strong>{current_user.nombre_completo}</strong>,</p>"
            f"<p>Su inscripción en <strong>{convocatoria.nombre}</strong> ({convocatoria.programa.nombre}) fue registrada.</p>"
            f"<p>Cursos preparatorios asignados:</p><ul>{lista_cursos}</ul>"
            + (
                "<p>Su documentación consta como <strong>pendiente</strong>: entregue los requisitos obligatorios "
                "a coordinación para que su proceso pueda aprobarse.</p>"
                if inscripcion.estado_proceso == "DOCUMENTACION_PENDIENTE" else ""
            )
            + f"<p>Ingrese a la plataforma para revisar sus actividades y fechas límite.</p>"
        )
    )

    return MyEnrollmentOut(
        id=inscripcion.id,
        convocatoria_id=convocatoria.id,
        convocatoria_nombre=convocatoria.nombre,
        programa_nombre=convocatoria.programa.nombre,
        fecha_inscripcion=inscripcion.fecha_inscripcion,
        estado_proceso=inscripcion.estado_proceso,
        cursos=[c.nombre for c in cursos]
    )
