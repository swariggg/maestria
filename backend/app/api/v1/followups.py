from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Usuario, Inscripcion, SeguimientoPostulante, RegistroAuditoria
)
from app.schemas.pydantic_models import FollowupCreate, FollowupOut
from app.services.risk_engine import evaluate_applicant_risk

router = APIRouter(prefix="/seguimientos", tags=["Seguimiento de Postulantes"])

@router.get("/inscripcion/{inscripcion_id}", response_model=List[FollowupOut])
def get_followups_by_enrollment(
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para ver los seguimientos de este postulante.")

    seguimientos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion_id
    ).order_by(SeguimientoPostulante.fecha_contacto.desc()).all()

    resultados = []
    for s in seguimientos:
        resultados.append(FollowupOut(
            id=s.id,
            inscripcion_id=s.inscripcion_id,
            tutor_id=s.tutor_id,
            tutor_nombre=s.tutor.nombre_completo,
            fecha_contacto=s.fecha_contacto,
            tipo_contacto=s.tipo_contacto,
            motivo=s.motivo,
            accion_realizada=s.accion_realizada,
            resultado=s.resultado,
            respuesta_postulante=s.respuesta_postulante,
            hubo_respuesta=s.hubo_respuesta,
            proxima_accion=s.proxima_accion,
            fecha_proxima_accion=s.fecha_proxima_accion,
            estado_caso=s.estado_caso,
            creado_en=s.creado_en
        ))
    return resultados

@router.post("", response_model=FollowupOut)
def create_followup(
    data: FollowupCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == data.inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para registrar seguimientos para este postulante.")

    seguimiento = SeguimientoPostulante(
        inscripcion_id=data.inscripcion_id,
        tutor_id=current_user.id,
        fecha_contacto=data.fecha_contacto,
        tipo_contacto=data.tipo_contacto,
        motivo=data.motivo,
        accion_realizada=data.accion_realizada,
        resultado=data.resultado,
        respuesta_postulante=data.respuesta_postulante,
        hubo_respuesta=data.hubo_respuesta,
        proxima_accion=data.proxima_accion,
        fecha_proxima_accion=data.fecha_proxima_accion,
        estado_caso=data.estado_caso
    )
    db.add(seguimiento)
    db.commit()
    db.refresh(seguimiento)

    # Si hubo respuesta positiva, actualizar última fecha de avance
    if data.hubo_respuesta:
        inscripcion.fecha_ultimo_avance = datetime.now()
        db.commit()

    # Recalcular automáticamente el riesgo
    evaluate_applicant_risk(db, inscripcion.id)

    # Auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="REGISTRAR_SEGUIMIENTO",
        entidad="SEGUIMIENTO_POSTULANTE",
        entidad_id=str(seguimiento.id),
        datos_nuevos_json=f'{{"tipo": "{data.tipo_contacto}", "hubo_respuesta": {str(data.hubo_respuesta).lower()}}}'
    ))
    db.commit()

    return FollowupOut(
        id=seguimiento.id,
        inscripcion_id=seguimiento.inscripcion_id,
        tutor_id=seguimiento.tutor_id,
        tutor_nombre=current_user.nombre_completo,
        fecha_contacto=seguimiento.fecha_contacto,
        tipo_contacto=seguimiento.tipo_contacto,
        motivo=seguimiento.motivo,
        accion_realizada=seguimiento.accion_realizada,
        resultado=seguimiento.resultado,
        respuesta_postulante=seguimiento.respuesta_postulante,
        hubo_respuesta=seguimiento.hubo_respuesta,
        proxima_accion=seguimiento.proxima_accion,
        fecha_proxima_accion=seguimiento.fecha_proxima_accion,
        estado_caso=seguimiento.estado_caso,
        creado_en=seguimiento.creado_en
    )
