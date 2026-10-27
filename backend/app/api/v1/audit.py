from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.entities import Usuario, RegistroAuditoria
from app.schemas.pydantic_models import AuditLogOut

router = APIRouter(prefix="/auditoria", tags=["Auditoría y Trazabilidad"])

@router.get("", response_model=List[AuditLogOut])
def list_audit_logs(
    limit: int = Query(50, le=200),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    query = db.query(RegistroAuditoria).order_by(RegistroAuditoria.fecha_creacion.desc()).limit(limit).all()
    resultado = []
    for r in query:
        resultado.append(AuditLogOut(
            id=r.id,
            usuario_nombre=r.usuario.nombre_completo if r.usuario else "Sistema / Anónimo",
            accion=r.accion,
            entidad=r.entidad,
            entidad_id=r.entidad_id,
            ip_origen=r.ip_origen,
            fecha_creacion=r.fecha_creacion
        ))
    return resultado
