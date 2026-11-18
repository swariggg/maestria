import json
import os
import uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_roles, get_current_user, cursos_visibles
from app.models.entities import Usuario, PerfilPostulante, RegistroAuditoria, Tutor, CursoPreparatorio
from app.schemas.pydantic_models import ProfileUpdate, TutorProfileUpdate
from app.services.validaciones import validar_cedula

router = APIRouter(prefix="/perfil", tags=["Perfil"])

CAMPOS_PERFIL = [
    "direccion", "ciudad", "pais", "titulo_tercer_nivel", "universidad_origen",
    "registrado_senescyt", "contacto_emergencia", "telefono_emergencia",
    "fecha_nacimiento", "enlaces",
]
CAMPOS_TUTOR = ["especialidad", "correo_outlook", "usuario_teams", "horario_atencion", "presentacion"]
FOTO_TIPOS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
FOTO_MAX_MB = 2


CAMPOS_REQUERIDOS = ["fecha_nacimiento", "direccion", "ciudad", "titulo_tercer_nivel", "universidad_origen", "contacto_emergencia", "telefono_emergencia"]
ETIQUETAS_CAMPO = {
    "fecha_nacimiento": "fecha de nacimiento", "direccion": "dirección", "ciudad": "ciudad", "titulo_tercer_nivel": "título de tercer nivel",
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
        "tiene_foto": bool(usuario.foto_ruta),
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

    if data.fecha_nacimiento:
        hoy = date.today()
        edad = hoy.year - data.fecha_nacimiento.year - ((hoy.month, hoy.day) < (data.fecha_nacimiento.month, data.fecha_nacimiento.day))
        if edad < 18 or edad > 100:
            raise HTTPException(status_code=400, detail="Revise la fecha de nacimiento: debe tener al menos 18 años.")
    enlaces = [e.strip() for e in (data.enlaces or "").splitlines() if e.strip()]
    for e in enlaces:
        if not e.lower().startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail=f"El enlace «{e}» debe empezar con http:// o https://.")

    anteriores = {c: getattr(perfil, c) for c in CAMPOS_PERFIL}
    anteriores.update(nombre_completo=current_user.nombre_completo, cedula=current_user.cedula)

    if data.nombre_completo is not None:
        nombre = " ".join(data.nombre_completo.split())
        if len(nombre) < 5 or " " not in nombre:
            raise HTTPException(status_code=400, detail="Escriba sus nombres y apellidos completos.")
        current_user.nombre_completo = nombre
    if data.cedula is not None and data.cedula.strip() != current_user.cedula:
        cedula = validar_cedula(data.cedula)
        if db.query(Usuario).filter(Usuario.cedula == cedula, Usuario.id != current_user.id).first():
            raise HTTPException(status_code=400, detail="Ya existe otra cuenta con esa cédula.")
        current_user.cedula = cedula

    for campo in CAMPOS_PERFIL:
        valor = getattr(data, campo)
        if campo == "enlaces":
            valor = "\n".join(enlaces) or None
        setattr(perfil, campo, valor.strip() if isinstance(valor, str) else valor)
    current_user.telefono = data.telefono.strip() if data.telefono else None
    current_user.actualizado_en = datetime.now()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="ACTUALIZAR_PERFIL",
        entidad="PERFIL_POSTULANTE",
        entidad_id=str(current_user.id),
        datos_anteriores_json=json.dumps(anteriores, ensure_ascii=False, default=str),
        datos_nuevos_json=json.dumps({**{c: getattr(perfil, c) for c in CAMPOS_PERFIL},
                                      "nombre_completo": current_user.nombre_completo, "cedula": current_user.cedula},
                                     ensure_ascii=False, default=str)
    ))
    db.commit()
    db.refresh(perfil)
    return _perfil_dict(current_user, perfil)


# ---------- Foto de perfil (la ve solo su dueño; la del tutor también la ven sus postulantes) ----------

@router.post("/foto")
async def upload_photo(file: UploadFile = File(...), current_user: Usuario = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    ext = FOTO_TIPOS.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(status_code=400, detail="La foto debe ser JPG, PNG o WEBP.")
    contenido = await file.read()
    if len(contenido) > FOTO_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"La foto supera {FOTO_MAX_MB} MB.")
    carpeta = os.path.join(settings.STORAGE_DIR, "fotos")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"foto_{current_user.id}_{uuid.uuid4().hex[:10]}.{ext}")
    with open(ruta, "wb") as f:
        f.write(contenido)
    anterior = current_user.foto_ruta
    current_user.foto_ruta, current_user.foto_mime = ruta, file.content_type.lower()
    db.commit()
    if anterior and anterior != ruta and os.path.exists(anterior):
        os.remove(anterior)
    return {"mensaje": "Foto actualizada.", "tiene_foto": True}


@router.delete("/foto")
def delete_photo(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.foto_ruta and os.path.exists(current_user.foto_ruta):
        os.remove(current_user.foto_ruta)
    current_user.foto_ruta = current_user.foto_mime = None
    db.commit()
    return {"mensaje": "Foto eliminada.", "tiene_foto": False}


@router.get("/foto/{usuario_id}")
def get_photo(usuario_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario or not usuario.foto_ruta or not os.path.exists(usuario.foto_ruta):
        raise HTTPException(status_code=404, detail="Sin foto.")
    if usuario.id != current_user.id and usuario.rol.codigo != "TUTOR":
        raise HTTPException(status_code=403, detail="La foto de perfil solo la ve su dueño.")
    return FileResponse(path=usuario.foto_ruta, media_type=usuario.foto_mime or "image/jpeg")


# ---------- Perfil del tutor: datos de contacto para sus postulantes ----------

def _tutor_dict(usuario: Usuario, tutor: Tutor) -> dict:
    return {
        "usuario_id": usuario.id,
        "nombre_completo": usuario.nombre_completo,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "tiene_foto": bool(usuario.foto_ruta),
        **{c: getattr(tutor, c) if tutor else None for c in CAMPOS_TUTOR},
    }


@router.get("/tutor")
def get_tutor_profile(current_user: Usuario = Depends(require_roles("TUTOR")), db: Session = Depends(get_db)):
    tutor = db.query(Tutor).filter(Tutor.usuario_id == current_user.id).first()
    return _tutor_dict(current_user, tutor)


@router.put("/tutor")
def update_tutor_profile(data: TutorProfileUpdate, current_user: Usuario = Depends(require_roles("TUTOR")),
                         db: Session = Depends(get_db)):
    tutor = db.query(Tutor).filter(Tutor.usuario_id == current_user.id).first()
    if not tutor:
        tutor = Tutor(usuario_id=current_user.id, especialidad=data.especialidad.strip())
        db.add(tutor)
    anteriores = {c: getattr(tutor, c) for c in CAMPOS_TUTOR}
    for campo in CAMPOS_TUTOR:
        valor = getattr(data, campo)
        setattr(tutor, campo, (valor.strip() or None) if isinstance(valor, str) else valor)
    if tutor.correo_outlook and "@" not in tutor.correo_outlook:
        raise HTTPException(status_code=400, detail="Revise el correo de Outlook.")
    current_user.telefono = data.telefono.strip() if data.telefono else None
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="ACTUALIZAR_PERFIL", entidad="TUTOR",
                             entidad_id=str(current_user.id),
                             datos_anteriores_json=json.dumps(anteriores, ensure_ascii=False),
                             datos_nuevos_json=json.dumps({c: getattr(tutor, c) for c in CAMPOS_TUTOR}, ensure_ascii=False)))
    db.commit()
    return _tutor_dict(current_user, tutor)


@router.get("/tutor-del-curso/{curso_id}")
def get_course_tutor_card(curso_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tarjeta de contacto del tutor que aparece en la portada del curso."""
    curso = cursos_visibles(current_user, db).filter(CursoPreparatorio.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    if not curso.tutor:
        return None
    tutor = db.query(Tutor).filter(Tutor.usuario_id == curso.tutor_id).first()
    return _tutor_dict(curso.tutor, tutor)
