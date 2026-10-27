from datetime import timedelta
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

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == credentials.email.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos.")

    if user.estado != "ACTIVO":
        raise HTTPException(status_code=403, detail=f"La cuenta se encuentra en estado '{user.estado}'. Contacte al administrador.")

    if not verify_password(credentials.password, user.password_hash):
        user.intentos_fallidos += 1
        db.commit()
        raise HTTPException(status_code=401, detail="Correo electrónico o contraseña incorrectos.")

    user.intentos_fallidos = 0
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
        estado="ACTIVO"
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

@router.get("/me", response_model=UserDetailOut)
def get_me(current_user: Usuario = Depends(get_current_user)):
    return current_user
