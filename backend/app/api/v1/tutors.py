import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Usuario, Tutor, TutorPrograma, Inscripcion, CursoPreparatorio
from app.services.progress_service import ESTADOS_INSCRIPCION_CERRADA
from app.services.tutoria import inscripciones_del_tutor


def _carga_tutor(db: Session, tutor_usuario_id: int) -> int:
    """Postulantes con inscripción vigente en los cursos del tutor."""
    return inscripciones_del_tutor(db, tutor_usuario_id).filter(
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
            "cursos": db.query(CursoPreparatorio).filter(CursoPreparatorio.tutor_id == t.usuario_id).count(),
            "programa_ids": programas,
            "activo": t.activo and t.usuario.estado == "ACTIVO",
            "disponible": t.activo and t.usuario.estado == "ACTIVO" and postulantes_activos < t.max_postulantes
        })
    return resultado
