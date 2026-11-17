"""
Gestión de usuarios internos (solo administrador).

Crea coordinadores y tutores, activa o desactiva cuentas, restablece contraseñas
y asigna coordinadores a programas. Cada acción queda en la auditoría.
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles, get_password_hash
from app.models.entities import Usuario, Rol, Tutor, Programa, CoordinadorPrograma, TutorPrograma, RegistroAuditoria
from app.services.validaciones import validar_password, validar_cedula

router = APIRouter(prefix="/usuarios", tags=["Gestión de Usuarios"])

ROLES_CREABLES = ["COORDINADOR", "TUTOR"]
ESTADOS = ["ACTIVO", "INACTIVO", "BLOQUEADO"]


class UserCreate(BaseModel):
    email: EmailStr
    nombre_completo: str = Field(min_length=3, max_length=200)
    cedula: str = Field(min_length=10, max_length=20)
    telefono: Optional[str] = Field(default=None, max_length=30)
    rol: str
    password: str = Field(min_length=8, max_length=100)
    especialidad: Optional[str] = Field(default=None, max_length=150)
    max_postulantes: Optional[int] = Field(default=None, ge=1, le=500)
    programa_ids: List[int] = []


class UserUpdate(BaseModel):
    nombre_completo: Optional[str] = Field(default=None, min_length=3, max_length=200)
    telefono: Optional[str] = Field(default=None, max_length=30)
    especialidad: Optional[str] = Field(default=None, max_length=150)
    max_postulantes: Optional[int] = Field(default=None, ge=1, le=500)


class EstadoUpdate(BaseModel):
    estado: str


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=100)


class ProgramasUpdate(BaseModel):
    programa_ids: List[int]


def _out(u: Usuario) -> dict:
    tutor = u.tutor_perfil
    return {
        "id": u.id,
        "email": u.email,
        "nombre_completo": u.nombre_completo,
        "cedula": u.cedula,
        "telefono": u.telefono,
        "rol": u.rol.codigo,
        "estado": u.estado,
        "creado_en": u.creado_en,
        "especialidad": tutor.especialidad if tutor else None,
        "max_postulantes": tutor.max_postulantes if tutor else None,
        "programas": [
            {"id": c.programa.id, "codigo": c.programa.codigo, "nombre": c.programa.nombre}
            for c in (u.coordinaciones if u.rol.codigo == "COORDINADOR" else u.programas_tutor) if c.activo
        ],
    }


def _usuario(db: Session, user_id: int) -> Usuario:
    u = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return u


def _auditar(db: Session, admin: Usuario, accion: str, u: Usuario, antes=None, despues=None):
    db.add(RegistroAuditoria(
        usuario_id=admin.id, accion=accion, entidad="USUARIO", entidad_id=str(u.id),
        datos_anteriores_json=json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
        datos_nuevos_json=json.dumps(despues, ensure_ascii=False, default=str) if despues is not None else None,
    ))


def _asignar_programas(db: Session, admin: Usuario, coord: Usuario, programa_ids: List[int]) -> list:
    """Programas de un coordinador (los gestiona) o de un tutor (puede acompañar a sus postulantes)."""
    ids = sorted(set(programa_ids))
    if ids:
        existentes = {p.id for p in db.query(Programa).filter(Programa.id.in_(ids)).all()}
        faltan = [i for i in ids if i not in existentes]
        if faltan:
            raise HTTPException(status_code=400, detail=f"Programas inexistentes: {faltan}.")
    if coord.rol.codigo == "TUTOR":
        actuales = {c.programa_id: c for c in db.query(TutorPrograma).filter(TutorPrograma.tutor_id == coord.id).all()}
        nuevo = lambda pid: TutorPrograma(programa_id=pid, tutor_id=coord.id, activo=True, asignado_por=admin.id)
    else:
        actuales = {c.programa_id: c for c in db.query(CoordinadorPrograma).filter(CoordinadorPrograma.coordinador_id == coord.id).all()}
        nuevo = lambda pid: CoordinadorPrograma(programa_id=pid, coordinador_id=coord.id, activo=True, asignado_por=admin.id)
    for pid, c in actuales.items():
        c.activo = pid in ids
    for pid in ids:
        if pid not in actuales:
            db.add(nuevo(pid))
    return ids


@router.get("")
def list_users(
    rol: Optional[str] = None,
    current_user: Usuario = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db)
):
    q = db.query(Usuario).join(Rol)
    if rol:
        q = q.filter(Rol.codigo == rol.upper())
    return [_out(u) for u in q.order_by(Rol.codigo, Usuario.nombre_completo).all()]


@router.post("")
def create_user(data: UserCreate, current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    rol_codigo = data.rol.upper()
    if rol_codigo not in ROLES_CREABLES:
        raise HTTPException(status_code=400, detail="Solo se pueden crear coordinadores o tutores. Los postulantes se registran solos.")
    email = data.email.lower()
    cedula = validar_cedula(data.cedula)
    validar_password(data.password)
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo.")
    if db.query(Usuario).filter(Usuario.cedula == cedula).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con esa cédula.")
    if rol_codigo == "TUTOR" and not (data.especialidad or "").strip():
        raise HTTPException(status_code=400, detail="El tutor necesita una especialidad.")
    rol = db.query(Rol).filter(Rol.codigo == rol_codigo).first()
    if not rol:
        raise HTTPException(status_code=500, detail=f"El rol {rol_codigo} no existe en la base de datos.")

    u = Usuario(
        email=email, password_hash=get_password_hash(data.password), nombre_completo=data.nombre_completo.strip(),
        cedula=cedula, telefono=(data.telefono or "").strip() or None, rol_id=rol.id, estado="ACTIVO",
        debe_cambiar_password=True,
    )
    db.add(u)
    db.flush()
    if rol_codigo == "TUTOR":
        db.add(Tutor(usuario_id=u.id, especialidad=data.especialidad.strip(), max_postulantes=data.max_postulantes or 30, activo=True))
    db.flush()
    db.refresh(u)
    programas = _asignar_programas(db, current_user, u, data.programa_ids)
    _auditar(db, current_user, "CREAR_USUARIO", u, despues={
        "email": email, "rol": rol_codigo, "programas": programas,
        "especialidad": data.especialidad, "max_postulantes": data.max_postulantes,
    })
    db.commit()
    db.refresh(u)
    return _out(u)


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    u = _usuario(db, user_id)
    antes, despues = {}, {}
    if data.nombre_completo is not None and data.nombre_completo.strip() != u.nombre_completo:
        antes["nombre_completo"], despues["nombre_completo"] = u.nombre_completo, data.nombre_completo.strip()
        u.nombre_completo = data.nombre_completo.strip()
    if data.telefono is not None and (data.telefono.strip() or None) != u.telefono:
        antes["telefono"], despues["telefono"] = u.telefono, data.telefono.strip() or None
        u.telefono = data.telefono.strip() or None
    tutor = u.tutor_perfil
    if (data.especialidad is not None or data.max_postulantes is not None) and not tutor:
        raise HTTPException(status_code=400, detail="La especialidad y el cupo solo aplican a tutores.")
    if tutor and data.especialidad is not None:
        if not data.especialidad.strip():
            raise HTTPException(status_code=400, detail="La especialidad no puede quedar vacía.")
        if data.especialidad.strip() != tutor.especialidad:
            antes["especialidad"], despues["especialidad"] = tutor.especialidad, data.especialidad.strip()
            tutor.especialidad = data.especialidad.strip()
    if tutor and data.max_postulantes is not None and data.max_postulantes != tutor.max_postulantes:
        antes["max_postulantes"], despues["max_postulantes"] = tutor.max_postulantes, data.max_postulantes
        tutor.max_postulantes = data.max_postulantes
    if despues:
        _auditar(db, current_user, "ACTUALIZAR_USUARIO", u, antes, despues)
    db.commit()
    db.refresh(u)
    return _out(u)


@router.patch("/{user_id}/estado")
def change_status(user_id: int, data: EstadoUpdate, current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    u = _usuario(db, user_id)
    estado = data.estado.upper()
    if estado not in ESTADOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {', '.join(ESTADOS)}.")
    if u.id == current_user.id and estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="No puede desactivar su propia cuenta.")
    if u.estado == estado:
        raise HTTPException(status_code=400, detail=f"La cuenta ya está en estado {estado}.")
    anterior = u.estado
    u.estado = estado
    if estado == "ACTIVO":
        u.intentos_fallidos = 0
        u.fecha_bloqueo = None
    if u.tutor_perfil:
        u.tutor_perfil.activo = estado == "ACTIVO"
    _auditar(db, current_user, "CAMBIAR_ESTADO_USUARIO", u, {"estado": anterior}, {"estado": estado})
    db.commit()
    db.refresh(u)
    return _out(u)


@router.post("/{user_id}/password")
def reset_password(user_id: int, data: PasswordReset, current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    u = _usuario(db, user_id)
    validar_password(data.password)
    u.password_hash = get_password_hash(data.password)
    u.intentos_fallidos = 0
    u.fecha_bloqueo = None
    u.debe_cambiar_password = True  # la cambiará al entrar
    _auditar(db, current_user, "RESTABLECER_CONTRASENA", u)  # nunca se guarda la contraseña
    db.commit()
    return {"mensaje": f"Contraseña de {u.nombre_completo} restablecida."}


@router.put("/{user_id}/programas")
def set_programs(user_id: int, data: ProgramasUpdate, current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    u = _usuario(db, user_id)
    if u.rol.codigo not in ("COORDINADOR", "TUTOR"):
        raise HTTPException(status_code=400, detail="Solo coordinadores y tutores tienen programas asignados.")
    filas = u.coordinaciones if u.rol.codigo == "COORDINADOR" else u.programas_tutor
    antes = sorted(c.programa_id for c in filas if c.activo)
    ids = _asignar_programas(db, current_user, u, data.programa_ids)
    if antes != ids:
        _auditar(db, current_user, "ASIGNAR_PROGRAMAS", u, {"programas": antes}, {"programas": ids})
    db.commit()
    db.refresh(u)
    return _out(u)
