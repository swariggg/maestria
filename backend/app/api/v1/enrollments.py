from datetime import datetime, date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.entities import (
    Usuario, Convocatoria, CursoPreparatorio, Inscripcion, AsignacionCurso, RegistroAuditoria
)
from app.schemas.pydantic_models import EnrollmentCreate, OpenCallOut, MyEnrollmentOut
from app.services.notification_service import send_or_queue_notification

router = APIRouter(prefix="/inscripciones", tags=["Postulantes e Inscripciones"])

ESTADOS_CONVOCATORIA_ABIERTA = ["ABIERTA", "EN_CURSO"]


def _cursos_activos(db: Session, convocatoria_id: int) -> List[CursoPreparatorio]:
    return db.query(CursoPreparatorio).filter(
        CursoPreparatorio.convocatoria_id == convocatoria_id,
        CursoPreparatorio.estado == "ACTIVO"
    ).all()


def _inscripcion_vigente(db: Session, postulante_id: int):
    return db.query(Inscripcion).filter(
        Inscripcion.postulante_id == postulante_id,
        Inscripcion.estado_proceso != "RETIRADO"
    ).first()


@router.get("/convocatorias-abiertas", response_model=List[OpenCallOut])
def list_open_calls(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    hoy = date.today()
    convocatorias = db.query(Convocatoria).filter(
        Convocatoria.estado.in_(ESTADOS_CONVOCATORIA_ABIERTA),
        Convocatoria.fecha_apertura <= hoy,
        Convocatoria.fecha_cierre >= hoy
    ).order_by(Convocatoria.fecha_cierre.asc()).all()

    vigente = _inscripcion_vigente(db, current_user.id)

    resultado = []
    for conv in convocatorias:
        cursos = _cursos_activos(db, conv.id)
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
            inscrito=bool(vigente and vigente.convocatoria_id == conv.id)
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
            cursos=[ac.curso.nombre for ac in insc.asignaciones_cursos]
        )
        for insc in inscripciones
    ]


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

    vigente = _inscripcion_vigente(db, current_user.id)
    if vigente:
        if vigente.convocatoria_id == convocatoria.id:
            raise HTTPException(status_code=400, detail="Ya se encuentra inscrito en esta convocatoria.")
        raise HTTPException(
            status_code=400,
            detail=f"Ya tiene una inscripción vigente en '{vigente.convocatoria.nombre}'. Solo se permite una inscripción activa."
        )

    cursos = _cursos_activos(db, convocatoria.id)
    if not cursos:
        raise HTTPException(status_code=400, detail="La convocatoria aún no tiene cursos preparatorios configurados.")

    ahora = datetime.now()
    inscripcion = Inscripcion(
        postulante_id=current_user.id,
        convocatoria_id=convocatoria.id,
        fecha_inscripcion=ahora,
        estado_proceso="EN_CURSO",
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
            f"<p>Ingrese a la plataforma para revisar sus actividades y fechas límite.</p>"
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
