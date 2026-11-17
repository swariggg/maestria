import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Usuario, Tutor, TutorPrograma, AsignacionTutor, Inscripcion, RegistroAuditoria
from app.schemas.pydantic_models import AssignTutorRequest
from app.services.progress_service import ESTADOS_INSCRIPCION_CERRADA
from app.services.process_emails import correo_tutor_asignado


def _carga_tutor(db: Session, tutor_usuario_id: int) -> int:
    """Postulantes con inscripción vigente asignados al tutor."""
    return db.query(AsignacionTutor).join(Inscripcion).filter(
        AsignacionTutor.tutor_id == tutor_usuario_id,
        AsignacionTutor.estado == 'ACTIVO',
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).count()

def _programas_tutor(db: Session, tutor_usuario_id: int) -> list:
    return [p[0] for p in db.query(TutorPrograma.programa_id).filter(
        TutorPrograma.tutor_id == tutor_usuario_id, TutorPrograma.activo == True  # noqa: E712
    ).all()]

router = APIRouter(prefix="/tutores", tags=["Tutores y Asignaciones"])

@router.get("")
def list_tutors(
    programa_id: Optional[int] = None,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """Con programa_id, solo los tutores que trabajan en ese programa."""
    tutores_query = db.query(Tutor).join(Usuario).all()
    resultado = []
    for t in tutores_query:
        programas = _programas_tutor(db, t.usuario_id)
        if programa_id and programa_id not in programas:
            continue
        postulantes_activos = _carga_tutor(db, t.usuario_id)
        resultado.append({
            "id": t.id,
            "usuario_id": t.usuario_id,
            "nombre_completo": t.usuario.nombre_completo,
            "email": t.usuario.email,
            "especialidad": t.especialidad,
            "max_postulantes": t.max_postulantes,
            "postulantes_asignados": postulantes_activos,
            "programa_ids": programas,
            "activo": t.activo and t.usuario.estado == "ACTIVO",
            "disponible": t.activo and t.usuario.estado == "ACTIVO" and postulantes_activos < t.max_postulantes
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
    if (not tutor or not tutor.activo or tutor.usuario.rol.codigo != "TUTOR"
            or tutor.usuario.estado != "ACTIVO"):
        raise HTTPException(status_code=404, detail="El tutor seleccionado no existe o no está activo.")
    if inscripcion.estado_proceso in ESTADOS_INSCRIPCION_CERRADA:
        raise HTTPException(status_code=400, detail=f"La inscripción está cerrada ({inscripcion.estado_proceso}).")
    if convocatoria.programa_id not in _programas_tutor(db, data.tutor_id):
        raise HTTPException(
            status_code=400,
            detail=f"{tutor.usuario.nombre_completo} no trabaja en el programa {convocatoria.programa.codigo}. "
                   "El administrador puede agregarle el programa en Usuarios."
        )

    # Desactivar asignación previa si existía
    asignacion_previa = db.query(AsignacionTutor).filter(
        AsignacionTutor.inscripcion_id == inscripcion.id,
        AsignacionTutor.estado == 'ACTIVO'
    ).first()
    if asignacion_previa and asignacion_previa.tutor_id == data.tutor_id:
        raise HTTPException(status_code=400, detail=f"{tutor.usuario.nombre_completo} ya es el tutor de este postulante.")
    motivo = (data.motivo or "").strip()
    if asignacion_previa and len(motivo) < 5:
        raise HTTPException(status_code=400, detail="Para cambiar de tutor indique el motivo (al menos 5 caracteres).")

    carga = _carga_tutor(db, data.tutor_id)
    if carga >= tutor.max_postulantes:
        raise HTTPException(
            status_code=400,
            detail=f"El tutor ya tiene {carga} de {tutor.max_postulantes} postulantes. Elija otro tutor o amplíe su capacidad."
        )

    if asignacion_previa:
        asignacion_previa.estado = "REASIGNADO"
        asignacion_previa.motivo_reasignacion = motivo

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
        datos_nuevos_json=json.dumps({"postulante_id": inscripcion.postulante_id, "tutor_id": data.tutor_id,
                                      "tutor_anterior": asignacion_previa.tutor_id if asignacion_previa else None,
                                      "motivo": motivo or None}, ensure_ascii=False)
    ))
    db.commit()

    correo_tutor_asignado(db, inscripcion, tutor.usuario)

    return {
        "mensaje": "Tutor asignado exitosamente.",
        "asignacion_id": nueva_asig.id,
        "tutor_nombre": tutor.usuario.nombre_completo
    }
