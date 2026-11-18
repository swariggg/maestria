"""
Materiales del curso: archivos de lectura, enlaces y sesiones sincrónicas (con fecha y enlace de Teams o Zoom).

Los sube el coordinador del programa o un tutor que acompaña en ese programa. Los postulantes
asignados al curso los ven y descargan. Las sesiones aparecen además en el calendario del postulante.
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import case
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access, cursos_visibles
from app.models.entities import Usuario, CursoPreparatorio, MaterialCurso, RegistroAuditoria

router = APIRouter(prefix="/materiales", tags=["Materiales del curso"])

TIPOS = ["ARCHIVO", "ENLACE", "SESION"]
EXTENSIONES = {"pdf", "docx", "pptx", "xlsx", "zip", "png", "jpg", "jpeg", "txt", "mp4"}
MAX_MB = 50


def _puede_gestionar(db: Session, user: Usuario, curso: CursoPreparatorio) -> bool:
    if user.rol.codigo == "TUTOR":
        return curso.tutor_id == user.id
    return verify_program_access(user, curso.convocatoria.programa_id, db)


def _out(m: MaterialCurso) -> dict:
    return {
        "id": m.id, "curso_id": m.curso_id, "tipo": m.tipo, "titulo": m.titulo, "descripcion": m.descripcion,
        "url": m.url, "fecha_sesion": m.fecha_sesion, "nombre_original": m.nombre_original,
        "tiene_archivo": bool(m.ruta_privada), "subido_por": m.autor.nombre_completo if m.autor else None,
        "creado_en": m.creado_en,
    }


def _curso_visible(db: Session, user: Usuario, curso_id: int) -> CursoPreparatorio:
    curso = cursos_visibles(user, db).filter(CursoPreparatorio.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    return curso


@router.get("/curso/{curso_id}")
def list_materials(curso_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    curso = _curso_visible(db, current_user, curso_id)
    filas = db.query(MaterialCurso).filter(MaterialCurso.curso_id == curso.id).order_by(
        # SQL Server no acepta "IS NULL" en ORDER BY: las sesiones con fecha van primero
        case((MaterialCurso.fecha_sesion.is_(None), 1), else_=0), MaterialCurso.fecha_sesion, MaterialCurso.creado_en.desc()
    ).all()
    return {"puede_gestionar": current_user.rol.codigo != "POSTULANTE" and _puede_gestionar(db, current_user, curso),
            "materiales": [_out(m) for m in filas]}


@router.post("")
async def create_material(
    curso_id: int = Form(...),
    tipo: str = Form(...),
    titulo: str = Form(...),
    descripcion: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    fecha_sesion: Optional[datetime] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    curso = db.query(CursoPreparatorio).filter(CursoPreparatorio.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    if not _puede_gestionar(db, current_user, curso):
        raise HTTPException(status_code=403, detail="No tiene permiso para subir material a este curso.")
    tipo = tipo.upper()
    if tipo not in TIPOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(TIPOS)}.")
    titulo = titulo.strip()
    if len(titulo) < 3:
        raise HTTPException(status_code=400, detail="Escriba un título.")
    url = (url or "").strip() or None
    if url and not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="El enlace debe empezar con http:// o https://.")
    if tipo == "ENLACE" and not url:
        raise HTTPException(status_code=400, detail="Indique el enlace.")
    if tipo == "SESION" and (not url or not fecha_sesion):
        raise HTTPException(status_code=400, detail="Una sesión necesita fecha y hora y el enlace de la reunión (Teams o Zoom).")

    m = MaterialCurso(curso_id=curso.id, tipo=tipo, titulo=titulo, descripcion=(descripcion or "").strip() or None,
                      url=url, fecha_sesion=fecha_sesion if tipo == "SESION" else None, subido_por=current_user.id)
    if tipo == "ARCHIVO":
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="Adjunte el archivo.")
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in EXTENSIONES:
            raise HTTPException(status_code=400, detail=f"Formato no permitido. Se admiten: {', '.join(sorted(EXTENSIONES))}.")
        contenido = await file.read()
        if len(contenido) > MAX_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"El archivo supera {MAX_MB} MB.")
        carpeta = os.path.join(settings.STORAGE_DIR, "materiales")
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, f"mat_{uuid.uuid4().hex[:16]}.{ext}")
        with open(ruta, "wb") as f:
            f.write(contenido)
        m.nombre_original, m.ruta_privada = file.filename, ruta
        m.mime_type = file.content_type or "application/octet-stream"
    db.add(m)
    db.flush()
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="CREAR_MATERIAL", entidad="MATERIAL_CURSO",
                             entidad_id=str(m.id), datos_nuevos_json=f'{{"curso_id": {curso.id}, "tipo": "{tipo}"}}'))
    db.commit()
    db.refresh(m)
    return _out(m)


@router.delete("/{material_id}")
def delete_material(material_id: int, current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
                    db: Session = Depends(get_db)):
    m = db.query(MaterialCurso).filter(MaterialCurso.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Material no encontrado.")
    # El tutor solo borra lo que subió; el coordinador, cualquier material de su programa
    es_autor = m.subido_por == current_user.id
    if not (es_autor or (current_user.rol.codigo != "TUTOR" and _puede_gestionar(db, current_user, m.curso))):
        raise HTTPException(status_code=403, detail="Solo quien lo subió o el coordinador del programa pueden eliminarlo.")
    if m.ruta_privada and os.path.exists(m.ruta_privada):
        os.remove(m.ruta_privada)
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="ELIMINAR_MATERIAL", entidad="MATERIAL_CURSO",
                             entidad_id=str(m.id)))
    db.delete(m)
    db.commit()
    return {"mensaje": "Material eliminado."}


@router.get("/{material_id}/download")
def download_material(material_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(MaterialCurso).filter(MaterialCurso.id == material_id).first()
    if not m or not m.ruta_privada:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    _curso_visible(db, current_user, m.curso_id)
    if not os.path.exists(m.ruta_privada):
        raise HTTPException(status_code=404, detail="El archivo ya no está en el almacenamiento.")
    return FileResponse(path=m.ruta_privada, filename=m.nombre_original, media_type=m.mime_type)
