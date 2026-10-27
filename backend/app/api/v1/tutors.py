from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Usuario, Tutor, AsignacionTutor, Inscripcion, RegistroAuditoria
from app.schemas.pydantic_models import AssignTutorRequest

router = APIRouter(prefix="/tutores", tags=["Tutores y Asignaciones"])

@router.get("")
def list_tutors(current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")), db: Session = Depends(get_db)):
    tutores_query = db.query(Tutor).join(Usuario).all()
    resultado = []
    for t in tutores_query:
        postulantes_activos = db.query(AsignacionTutor).filter(
            AsignacionTutor.tutor_id == t.usuario_id,
            AsignacionTutor.estado == 'ACTIVO'
        ).count()
        resultado.append({
            "id": t.id,
            "usuario_id": t.usuario_id,
            "nombre_completo": t.usuario.nombre_completo,
            "email": t.usuario.email,
            "especialidad": t.especialidad,
            "max_postulantes": t.max_postulantes,
            "postulantes_asignados": postulantes_activos,
            "activo": t.activo
        })
    return resultado

@router.post("/asignar")
def assign_tutor(
    data: AssignTutorRequest,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == data.inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    # Validar que el coordinador gestione este programa
    convocatoria = inscripcion.convocatoria
    if not verify_program_access(current_user, convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este programa para asignar tutores.")

    tutor = db.query(Tutor).filter(Tutor.usuario_id == data.tutor_id).first()
    if not tutor or not tutor.activo:
        raise HTTPException(status_code=404, detail="El tutor seleccionado no existe o no está activo.")

    # Desactivar asignación previa si existía
    asignacion_previa = db.query(AsignacionTutor).filter(
        AsignacionTutor.inscripcion_id == inscripcion.id,
        AsignacionTutor.estado == 'ACTIVO'
    ).first()
    if asignacion_previa:
        asignacion_previa.estado = "REASIGNADO"
        asignacion_previa.motivo_reasignacion = data.motivo or "Reasignación administrativa por coordinación"

    # Crear nueva asignación
    nueva_asig = AsignacionTutor(
        inscripcion_id=inscripcion.id,
        tutor_id=data.tutor_id,
        coordinador_id=current_user.id,
        estado="ACTIVO",
        motivo_reasignacion=None
    )
    db.add(nueva_asig)
    db.commit()

    # Auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="ASIGNAR_TUTOR",
        entidad="ASIGNACION_TUTOR",
        entidad_id=str(nueva_asig.id),
        datos_nuevos_json=f'{{"postulante_id": {inscripcion.postulante_id}, "tutor_id": {data.tutor_id}}}'
    ))
    db.commit()

    return {
        "mensaje": "Tutor asignado exitosamente.",
        "asignacion_id": nueva_asig.id,
        "tutor_nombre": tutor.usuario.nombre_completo
    }
