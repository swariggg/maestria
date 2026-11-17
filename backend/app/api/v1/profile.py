import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import Usuario, PerfilPostulante, RegistroAuditoria
from app.schemas.pydantic_models import ProfileUpdate

router = APIRouter(prefix="/perfil", tags=["Perfil del Postulante"])

CAMPOS_PERFIL = [
    "direccion", "ciudad", "pais", "titulo_tercer_nivel", "universidad_origen",
    "registrado_senescyt", "contacto_emergencia", "telefono_emergencia",
]


CAMPOS_REQUERIDOS = ["direccion", "ciudad", "titulo_tercer_nivel", "universidad_origen", "contacto_emergencia", "telefono_emergencia"]
ETIQUETAS_CAMPO = {
    "direccion": "dirección", "ciudad": "ciudad", "titulo_tercer_nivel": "título de tercer nivel",
    "universidad_origen": "universidad de origen", "contacto_emergencia": "contacto de emergencia",
    "telefono_emergencia": "teléfono de emergencia", "telefono": "teléfono",
}


def campos_faltantes(usuario: Usuario, perfil: PerfilPostulante) -> list:
    """Datos del perfil que el postulante debe completar antes de inscribirse."""
    datos = {c: getattr(perfil, c) for c in CAMPOS_PERFIL} if perfil else {}
    return [c for c in CAMPOS_REQUERIDOS if not datos.get(c)] + ([] if usuario.telefono else ["telefono"])


def _perfil_dict(usuario: Usuario, perfil: PerfilPostulante) -> dict:
    datos = {c: getattr(perfil, c) for c in CAMPOS_PERFIL} if perfil else {c: None for c in CAMPOS_PERFIL}
    faltantes = campos_faltantes(usuario, perfil)
    return {
        "nombre_completo": usuario.nombre_completo,
        "email": usuario.email,
        "cedula": usuario.cedula,
        "telefono": usuario.telefono,
        **datos,
        "perfil_completo": not faltantes,
        "campos_faltantes": faltantes,
    }


@router.get("")
def get_my_profile(current_user: Usuario = Depends(require_roles("POSTULANTE")), db: Session = Depends(get_db)):
    perfil = db.query(PerfilPostulante).filter(PerfilPostulante.usuario_id == current_user.id).first()
    return _perfil_dict(current_user, perfil)


@router.put("")
def update_my_profile(
    data: ProfileUpdate,
    current_user: Usuario = Depends(require_roles("POSTULANTE")),
    db: Session = Depends(get_db)
):
    perfil = db.query(PerfilPostulante).filter(PerfilPostulante.usuario_id == current_user.id).first()
    if not perfil:
        perfil = PerfilPostulante(usuario_id=current_user.id)
        db.add(perfil)

    anteriores = {c: getattr(perfil, c) for c in CAMPOS_PERFIL}
    for campo in CAMPOS_PERFIL:
        valor = getattr(data, campo)
        setattr(perfil, campo, valor.strip() if isinstance(valor, str) else valor)
    current_user.telefono = data.telefono.strip() if data.telefono else None
    current_user.actualizado_en = datetime.now()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="ACTUALIZAR_PERFIL",
        entidad="PERFIL_POSTULANTE",
        entidad_id=str(current_user.id),
        datos_anteriores_json=json.dumps(anteriores, ensure_ascii=False, default=str),
        datos_nuevos_json=json.dumps({c: getattr(perfil, c) for c in CAMPOS_PERFIL}, ensure_ascii=False, default=str)
    ))
    db.commit()
    db.refresh(perfil)
    return _perfil_dict(current_user, perfil)
