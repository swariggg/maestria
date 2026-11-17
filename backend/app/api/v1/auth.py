from datetime import timedelta, datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user
)
from app.core.config import settings
from app.models.entities import Usuario, Rol, PerfilPostulante, RegistroAuditoria
from app.services.notification_service import send_or_queue_notification
from app.schemas.pydantic_models import LoginRequest, TokenResponse, RegisterRequest, UserOut, UserDetailOut
from app.services.validaciones import validar_password, validar_cedula

router = APIRouter(prefix="/auth", tags=["Autenticación"])

MAX_INTENTOS_LOGIN = 5
MINUTOS_BLOQUEO = 15


class CambioPassword(BaseModel):
    password_actual: str
    password_nueva: str

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == credentials.email.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos.")

    if user.estado != "ACTIVO":
        raise HTTPException(status_code=403, detail=f"La cuenta se encuentra en estado '{user.estado}'. Contacte al administrador.")

    ahora = datetime.now()
    if user.fecha_bloqueo and ahora < user.fecha_bloqueo + timedelta(minutes=MINUTOS_BLOQUEO):
        faltan = int((user.fecha_bloqueo + timedelta(minutes=MINUTOS_BLOQUEO) - ahora).total_seconds() // 60) + 1
        raise HTTPException(
            status_code=423,
            detail=f"Cuenta bloqueada por {MAX_INTENTOS_LOGIN} intentos fallidos. Intente de nuevo en {faltan} minuto(s)."
        )

    if not verify_password(credentials.password, user.password_hash):
        user.intentos_fallidos = (user.intentos_fallidos or 0) + 1
        if user.intentos_fallidos >= MAX_INTENTOS_LOGIN:
            user.intentos_fallidos = 0
            user.fecha_bloqueo = ahora
            db.add(RegistroAuditoria(usuario_id=user.id, accion="BLOQUEO_CUENTA", entidad="USUARIO", entidad_id=str(user.id),
                                     ip_origen=request.client.host if request.client else None))
            db.commit()
            raise HTTPException(
                status_code=423,
                detail=f"Contraseña incorrecta. La cuenta quedó bloqueada por {MINUTOS_BLOQUEO} minutos."
            )
        quedan = MAX_INTENTOS_LOGIN - user.intentos_fallidos
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=f"Correo electrónico o contraseña incorrectos. Le quedan {quedan} intento(s) antes del bloqueo."
        )

    user.intentos_fallidos = 0
    user.fecha_bloqueo = None
    db.commit()

    # Generar JWT Token
    access_token = create_access_token(data={"sub": str(user.id), "rol": user.rol.codigo, "email": user.email})

    # Establecer Cookie HttpOnly segura
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False # Cambiar a True en HTTPS producción
    )

    # Auditoría
    client_ip = request.client.host if request.client else "127.0.0.1"
    db.add(RegistroAuditoria(
        usuario_id=user.id,
        accion="LOGIN",
        entidad="USUARIO",
        entidad_id=str(user.id),
        ip_origen=client_ip
    ))
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=UserOut)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if not data.acepta_datos:
        raise HTTPException(status_code=400, detail="Debe aceptar la política de tratamiento de datos personales para registrarse.")
    validar_password(data.password)
    data.cedula = validar_cedula(data.cedula)
    # Validar duplicados
    if db.query(Usuario).filter(Usuario.email == data.email.lower()).first():
        raise HTTPException(status_code=400, detail="El correo electrónico ya se encuentra registrado.")
    if db.query(Usuario).filter(Usuario.cedula == data.cedula).first():
        raise HTTPException(status_code=400, detail="La cédula de identidad ya se encuentra registrada.")

    rol_postulante = db.query(Rol).filter(Rol.codigo == "POSTULANTE").first()
    if not rol_postulante:
        raise HTTPException(status_code=500, detail="Rol POSTULANTE no configurado en la base de datos.")

    nuevo_usuario = Usuario(
        email=data.email.lower(),
        password_hash=get_password_hash(data.password),
        nombre_completo=data.nombre_completo,
        cedula=data.cedula,
        telefono=data.telefono,
        rol_id=rol_postulante.id,
        estado="ACTIVO",
        acepto_datos_en=datetime.now()
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    # Crear perfil del postulante
    perfil = PerfilPostulante(
        usuario_id=nuevo_usuario.id,
        direccion=data.direccion,
        ciudad=data.ciudad,
        titulo_tercer_nivel=data.titulo_tercer_nivel,
        universidad_origen=data.universidad_origen
    )
    db.add(perfil)
    db.add(RegistroAuditoria(
        usuario_id=nuevo_usuario.id,
        accion="REGISTRO",
        entidad="USUARIO",
        entidad_id=str(nuevo_usuario.id)
    ))
    db.commit()

    send_or_queue_notification(
        db=db,
        destinatario=nuevo_usuario,
        tipo_evento="REGISTRO_EXITOSO",
        asunto="UIDE: Registro exitoso en APP - Maestría",
        cuerpo_html=(
            f"<p>Estimado(a) <strong>{nuevo_usuario.nombre_completo}</strong>,</p>"
            "<p>Su cuenta de postulante fue creada correctamente. "
            "Ingrese a la plataforma para inscribirse en una convocatoria de maestría.</p>"
        )
    )

    return nuevo_usuario

@router.post("/logout")
def logout(response: Response, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie("access_token")
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="LOGOUT",
        entidad="USUARIO",
        entidad_id=str(current_user.id)
    ))
    db.commit()
    return {"message": "Sesión cerrada correctamente."}

@router.post("/cambiar-password")
def change_password(data: CambioPassword, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Solo se usa para la clave inicial: quien recibió su contraseña del administrador la cambia al
    entrar por primera vez. Después, un cambio se pide al administrador.
    """
    if not current_user.debe_cambiar_password:
        raise HTTPException(status_code=403, detail="Para cambiar su contraseña, solicítelo al administrador.")
    if not verify_password(data.password_actual, current_user.password_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    validar_password(data.password_nueva)
    if data.password_nueva == data.password_actual:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual.")
    current_user.password_hash = get_password_hash(data.password_nueva)
    current_user.debe_cambiar_password = False
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="CAMBIO_PASSWORD_INICIAL", entidad="USUARIO", entidad_id=str(current_user.id)))
    db.commit()
    return {"mensaje": "Contraseña actualizada."}


@router.get("/me", response_model=UserDetailOut)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user
