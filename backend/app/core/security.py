from datetime import datetime, timedelta, timezone
from typing import Optional, List
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

security_bearer = HTTPBearer(auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def get_token_from_request(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[str]:
    # 1. Bearer header
    if creds and creds.credentials:
        return creds.credentials
    # 2. HttpOnly Cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token
    return None

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no proporcionadas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    from app.models.entities import Usuario
    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not user or user.estado != 'ACTIVO':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva, bloqueada o inexistente."
        )
    return user

def require_roles(*allowed_roles: str):
    def role_checker(current_user = Depends(get_current_user)):
        user_role = current_user.rol.codigo if current_user.rol else None
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: El rol '{user_role}' no tiene autorización para esta acción."
            )
        return current_user
    return role_checker

def verify_program_access(user, programa_id: int, db: Session) -> bool:
    """Verifica el alcance (ABAC) para Coordinadores. El Admin tiene acceso global."""
    if user.rol.codigo == 'ADMIN':
        return True
    if user.rol.codigo == 'COORDINADOR':
        from app.models.entities import CoordinadorPrograma
        asignado = db.query(CoordinadorPrograma).filter(
            CoordinadorPrograma.programa_id == programa_id,
            CoordinadorPrograma.coordinador_id == user.id,
            CoordinadorPrograma.activo == True
        ).first()
        return bool(asignado)
    return False

def verify_applicant_access(user, postulante_usuario_id: int, db: Session) -> bool:
    """Verifica si el usuario autenticado tiene permiso de ver a este postulante."""
    if user.rol.codigo == 'ADMIN':
        return True
    if user.rol.codigo == 'POSTULANTE':
        return user.id == postulante_usuario_id
    if user.rol.codigo == 'TUTOR':
        from app.models.entities import AsignacionTutor, Inscripcion
        asignacion = db.query(AsignacionTutor).join(Inscripcion).filter(
            Inscripcion.postulante_id == postulante_usuario_id,
            AsignacionTutor.tutor_id == user.id,
            AsignacionTutor.estado == 'ACTIVO'
        ).first()
        return bool(asignacion)
    if user.rol.codigo == 'COORDINADOR':
        from app.models.entities import CoordinadorPrograma, Inscripcion, Convocatoria
        coord_asignado = db.query(CoordinadorPrograma).join(
            Convocatoria, Convocatoria.programa_id == CoordinadorPrograma.programa_id
        ).join(
            Inscripcion, Inscripcion.convocatoria_id == Convocatoria.id
        ).filter(
            Inscripcion.postulante_id == postulante_usuario_id,
            CoordinadorPrograma.coordinador_id == user.id,
            CoordinadorPrograma.activo == True
        ).first()
        return bool(coord_asignado)
    return False
