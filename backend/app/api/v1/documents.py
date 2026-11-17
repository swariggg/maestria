"""
Requisitos documentales de la convocatoria y documentos personales del postulante.

- El coordinador define qué documentos pide cada convocatoria.
- El postulante sube cada documento desde "Mi perfil".
- Coordinación lo revisa. Cuando se aprueba el último obligatorio, la
  inscripción pasa de DOCUMENTACION_PENDIENTE a EN_CURSO.
- Cada documento admite 3 envíos; un rechazo es definitivo y solo coordinación puede
  reabrir un documento ya aprobado. El primer envío debe hacerse hasta la fecha de cierre.
"""
import os
import json
import uuid
import hashlib
from datetime import datetime, date
from typing import List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access, verify_applicant_access
from app.models.entities import (
    Usuario, Convocatoria, RequisitoConvocatoria, Inscripcion, DocumentoPostulante, RegistroAuditoria
)
from app.schemas.pydantic_models import RequisitoCreate, RequisitoUpdate, RequisitoOut, DocumentReview
from app.services.progress_service import inscripcion_cerrada, marcar_documentacion_completa
from app.services.process_emails import correo_documento_cargado, correo_documento_revisado, correo_proceso_aprobado

router = APIRouter(prefix="/documentos", tags=["Requisitos y Documentos"])

ESTADOS_REVISION = ["APROBADO", "REQUIERE_CORRECCION", "RECHAZADO"]
MAX_INTENTOS_DOCUMENTO = 3


class Reapertura(BaseModel):
    motivo: str = Field(min_length=5, max_length=1000)


# ---------- Requisitos de la convocatoria ----------

def _convocatoria_gestionable(db: Session, user: Usuario, convocatoria_id: int) -> Convocatoria:
    conv = db.query(Convocatoria).filter(Convocatoria.id == convocatoria_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")
    if not verify_program_access(user, conv.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene permiso sobre el programa de esta convocatoria.")
    if conv.estado != "PLANIFICADA":
        raise HTTPException(
            status_code=400,
            detail="Los requisitos solo se cambian mientras la convocatoria está PLANIFICADA, antes de abrir las inscripciones."
        )
    return conv


def _normalizar_formatos(formatos: str) -> str:
    lista = [f.strip().lower().lstrip(".") for f in formatos.split(",") if f.strip()]
    if not lista:
        raise HTTPException(status_code=400, detail="Indique al menos un formato permitido (por ejemplo: pdf).")
    return ",".join(dict.fromkeys(lista))


@router.get("/requisitos", response_model=List[RequisitoOut])
def list_requirements(convocatoria_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(RequisitoConvocatoria).filter(
        RequisitoConvocatoria.convocatoria_id == convocatoria_id
    ).order_by(RequisitoConvocatoria.id.asc()).all()


@router.post("/requisitos", response_model=RequisitoOut)
def create_requirement(
    data: RequisitoCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    _convocatoria_gestionable(db, current_user, data.convocatoria_id)
    req = RequisitoConvocatoria(
        convocatoria_id=data.convocatoria_id,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion,
        es_obligatorio=data.es_obligatorio,
        formato_permitido=_normalizar_formatos(data.formato_permitido),
        tamano_max_mb=data.tamano_max_mb,
    )
    db.add(req)
    db.flush()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="CREAR_REQUISITO", entidad="REQUISITO_CONVOCATORIA",
        entidad_id=str(req.id),
        datos_nuevos_json=json.dumps(data.model_dump(), ensure_ascii=False)
    ))
    db.commit()
    db.refresh(req)
    return req


@router.put("/requisitos/{requisito_id}", response_model=RequisitoOut)
def update_requirement(
    requisito_id: int,
    data: RequisitoUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    req = db.query(RequisitoConvocatoria).filter(RequisitoConvocatoria.id == requisito_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisito no encontrado.")
    _convocatoria_gestionable(db, current_user, req.convocatoria_id)
    anterior = RequisitoOut.model_validate(req).model_dump()
    req.nombre = data.nombre.strip()
    req.descripcion = data.descripcion
    req.es_obligatorio = data.es_obligatorio
    req.formato_permitido = _normalizar_formatos(data.formato_permitido)
    req.tamano_max_mb = data.tamano_max_mb
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="EDITAR_REQUISITO", entidad="REQUISITO_CONVOCATORIA",
        entidad_id=str(req.id),
        datos_anteriores_json=json.dumps(anterior, ensure_ascii=False),
        datos_nuevos_json=json.dumps(data.model_dump(), ensure_ascii=False)
    ))
    db.commit()
    db.refresh(req)
    return req


@router.delete("/requisitos/{requisito_id}")
def delete_requirement(
    requisito_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    req = db.query(RequisitoConvocatoria).filter(RequisitoConvocatoria.id == requisito_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requisito no encontrado.")
    _convocatoria_gestionable(db, current_user, req.convocatoria_id)
    if db.query(DocumentoPostulante).filter(DocumentoPostulante.requisito_id == req.id).count():
        raise HTTPException(
            status_code=400,
            detail="Ya hay postulantes que subieron este documento. Márquelo como opcional en lugar de eliminarlo."
        )
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="ELIMINAR_REQUISITO", entidad="REQUISITO_CONVOCATORIA",
        entidad_id=str(req.id),
        datos_anteriores_json=json.dumps(RequisitoOut.model_validate(req).model_dump(), ensure_ascii=False)
    ))
    db.delete(req)
    db.commit()
    return {"mensaje": "Requisito eliminado."}


# ---------- Documentos del postulante ----------

def _ultimo_documento(db: Session, inscripcion_id: int, requisito_id: int):
    return db.query(DocumentoPostulante).filter(
        DocumentoPostulante.inscripcion_id == inscripcion_id,
        DocumentoPostulante.requisito_id == requisito_id
    ).order_by(DocumentoPostulante.id.desc()).first()


def documentacion_obligatoria_aprobada(db: Session, inscripcion: Inscripcion) -> bool:
    obligatorios = db.query(RequisitoConvocatoria).filter(
        RequisitoConvocatoria.convocatoria_id == inscripcion.convocatoria_id,
        RequisitoConvocatoria.es_obligatorio == True  # noqa: E712
    ).all()
    for req in obligatorios:
        doc = _ultimo_documento(db, inscripcion.id, req.id)
        if not doc or doc.estado_revision != "APROBADO":
            return False
    return True


def estado_subida(db: Session, insc: Inscripcion, req: RequisitoConvocatoria, hoy: date = None) -> dict:
    """Si el postulante puede subir este documento ahora, cuántos intentos lleva y, si no, por qué."""
    hoy = hoy or date.today()
    docs = db.query(DocumentoPostulante).filter(
        DocumentoPostulante.inscripcion_id == insc.id,
        DocumentoPostulante.requisito_id == req.id
    ).order_by(DocumentoPostulante.id.asc()).all()
    # Una reapertura de coordinación vuelve a dar los 3 intentos
    desde = max((i for i, d in enumerate(docs) if d.reabierto), default=-1)
    usados = len(docs) - (desde + 1)
    ultimo = docs[-1] if docs else None
    motivo = None
    if inscripcion_cerrada(insc) or insc.convocatoria.estado == "FINALIZADA":
        motivo = "La inscripción está cerrada."
    elif ultimo and ultimo.estado_revision == "APROBADO":
        motivo = "El documento ya fue aprobado."
    elif ultimo and ultimo.estado_revision == "RECHAZADO":
        motivo = "El documento fue rechazado de forma definitiva."
    elif ultimo and ultimo.estado_revision == "PENDIENTE":
        motivo = "Espere a que coordinación revise el documento que ya subió."
    elif usados >= MAX_INTENTOS_DOCUMENTO:
        motivo = f"Ya usó los {MAX_INTENTOS_DOCUMENTO} intentos de este documento."
    elif not docs and hoy > insc.convocatoria.fecha_cierre:
        motivo = f"El plazo para entregar documentos terminó el {insc.convocatoria.fecha_cierre}."
    return {
        "puede_subir": motivo is None,
        "motivo_bloqueo": motivo,
        "intentos_usados": usados,
        "intentos_restantes": max(0, MAX_INTENTOS_DOCUMENTO - usados),
    }


def _inscripcion_accesible(db: Session, user: Usuario, inscripcion_id: int) -> Inscripcion:
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_applicant_access(user, insc.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este postulante.")
    return insc


def _doc_dict(doc: DocumentoPostulante) -> dict:
    if not doc:
        return None
    return {
        "id": doc.id,
        "nombre_original": doc.nombre_original,
        "tamano_bytes": doc.tamano_bytes,
        "estado_revision": doc.estado_revision,
        "observaciones": doc.observaciones,
        "revisado_por": doc.revisor.nombre_completo if doc.revisor else None,
        "fecha_revision": doc.fecha_revision,
        "fecha_carga": doc.fecha_carga,
    }


@router.get("/inscripcion/{inscripcion_id}")
def list_enrollment_documents(inscripcion_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cada requisito de la convocatoria con el último documento subido y su estado."""
    insc = _inscripcion_accesible(db, current_user, inscripcion_id)
    requisitos = db.query(RequisitoConvocatoria).filter(
        RequisitoConvocatoria.convocatoria_id == insc.convocatoria_id
    ).order_by(RequisitoConvocatoria.id.asc()).all()
    items = []
    for req in requisitos:
        doc = _ultimo_documento(db, insc.id, req.id)
        items.append({
            **RequisitoOut.model_validate(req).model_dump(),
            "documento": _doc_dict(doc),
            "estado": doc.estado_revision if doc else "SIN_CARGAR",
            **estado_subida(db, insc, req),
        })
    return {
        "inscripcion_id": insc.id,
        "estado_proceso": insc.estado_proceso,
        "convocatoria_nombre": insc.convocatoria.nombre,
        "documentacion_completa": documentacion_obligatoria_aprobada(db, insc),
        "puede_subir": not inscripcion_cerrada(insc) and insc.convocatoria.estado != "FINALIZADA",
        "max_intentos": MAX_INTENTOS_DOCUMENTO,
        "fecha_limite": insc.convocatoria.fecha_cierre,
        "requisitos": items,
    }


@router.post("/upload")
async def upload_document(
    inscripcion_id: int = Form(...),
    requisito_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: Usuario = Depends(require_roles("POSTULANTE")),
    db: Session = Depends(get_db)
):
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc or insc.postulante_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo puede subir documentos de su propia inscripción.")
    if inscripcion_cerrada(insc) or insc.convocatoria.estado == "FINALIZADA":
        raise HTTPException(status_code=400, detail="La inscripción está cerrada; ya no admite documentos.")

    req = db.query(RequisitoConvocatoria).filter(
        RequisitoConvocatoria.id == requisito_id,
        RequisitoConvocatoria.convocatoria_id == insc.convocatoria_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="El requisito no pertenece a su convocatoria.")

    anterior = _ultimo_documento(db, insc.id, req.id)
    estado = estado_subida(db, insc, req)
    if not estado["puede_subir"]:
        raise HTTPException(status_code=400, detail=estado["motivo_bloqueo"])

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    permitidos = [f.strip().lower() for f in req.formato_permitido.split(",")]
    if ext not in permitidos:
        raise HTTPException(status_code=400, detail=f"Formato no permitido (.{ext}). Se admiten: {req.formato_permitido}")

    content = await file.read()
    if len(content) > req.tamano_max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El archivo supera el tamaño máximo de {req.tamano_max_mb} MB.")
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    sha256 = hashlib.sha256(content).hexdigest()
    nombre_seguro = f"doc_{uuid.uuid4().hex[:12]}_{sha256[:8]}.{ext}"
    ruta = os.path.join(settings.STORAGE_DIR, "documentos", nombre_seguro)
    with open(ruta, "wb") as f:
        f.write(content)

    ahora = datetime.now()
    doc = DocumentoPostulante(
        inscripcion_id=insc.id,
        requisito_id=req.id,
        nombre_original=file.filename,
        nombre_seguro=nombre_seguro,
        ruta_privada=ruta,
        mime_type=file.content_type or "application/octet-stream",
        tamano_bytes=len(content),
        hash_sha256=sha256,
        estado_revision="PENDIENTE",
        fecha_carga=ahora,
    )
    db.add(doc)
    db.flush()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="UPLOAD_DOCUMENTO", entidad="DOCUMENTO_POSTULANTE",
        entidad_id=str(doc.id),
        datos_nuevos_json=json.dumps({"requisito": req.nombre, "archivo": file.filename, "reemplaza": anterior.id if anterior else None}, ensure_ascii=False)
    ))
    db.commit()
    correo_documento_cargado(db, insc, req.nombre, file.filename)
    quedan = estado["intentos_restantes"] - 1
    return {"mensaje": f"Documento cargado. Coordinación lo revisará. Le quedan {quedan} intento(s) para este documento.",
            "documento_id": doc.id, "intentos_restantes": quedan}


@router.patch("/{documento_id}/revision")
def review_document(
    documento_id: int,
    data: DocumentReview,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    if data.estado_revision not in ESTADOS_REVISION:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {', '.join(ESTADOS_REVISION)}.")
    if data.estado_revision != "APROBADO" and not (data.observaciones or "").strip():
        raise HTTPException(status_code=400, detail="Indique en observaciones qué debe corregir el postulante.")

    doc = db.query(DocumentoPostulante).filter(DocumentoPostulante.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    insc = _inscripcion_accesible(db, current_user, doc.inscripcion_id)
    if inscripcion_cerrada(insc):
        raise HTTPException(status_code=400, detail="La inscripción está cerrada.")
    ultimo = _ultimo_documento(db, insc.id, doc.requisito_id)
    if ultimo.id != doc.id:
        raise HTTPException(status_code=400, detail="El postulante ya subió una versión más reciente de este documento.")

    anterior = doc.estado_revision
    doc.estado_revision = data.estado_revision
    doc.observaciones = data.observaciones
    doc.revisado_por = current_user.id
    doc.fecha_revision = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="REVISAR_DOCUMENTO", entidad="DOCUMENTO_POSTULANTE",
        entidad_id=str(doc.id),
        datos_anteriores_json=json.dumps({"estado_revision": anterior}),
        datos_nuevos_json=json.dumps({"estado_revision": data.estado_revision, "observaciones": data.observaciones}, ensure_ascii=False)
    ))
    db.flush()

    # Con el último documento obligatorio aprobado, el proceso sigue su curso
    aprobado = False
    documentacion_completa = False
    if insc.estado_proceso == "DOCUMENTACION_PENDIENTE" and documentacion_obligatoria_aprobada(db, insc):
        aprobado = marcar_documentacion_completa(db, insc, current_user.id)
        documentacion_completa = True
    db.commit()

    correo_documento_revisado(db, insc, doc.requisito.nombre, data.estado_revision, data.observaciones)
    if aprobado:
        correo_proceso_aprobado(db, insc)
    db.refresh(insc)
    return {
        "mensaje": "Revisión registrada.",
        "estado_revision": data.estado_revision,
        "documentacion_completa": documentacion_completa,
        "estado_proceso": insc.estado_proceso,
    }


@router.patch("/{documento_id}/reabrir")
def reopen_document(
    documento_id: int,
    data: Reapertura,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """
    Coordinación vuelve a pedir un documento ya aprobado, o da otra oportunidad a uno rechazado
    (el rechazo es definitivo para el postulante, no para coordinación). Siempre con motivo.
    """
    doc = db.query(DocumentoPostulante).filter(DocumentoPostulante.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    insc = _inscripcion_accesible(db, current_user, doc.inscripcion_id)
    if inscripcion_cerrada(insc):
        raise HTTPException(status_code=400, detail="La inscripción está cerrada.")
    if _ultimo_documento(db, insc.id, doc.requisito_id).id != doc.id or doc.estado_revision not in ("APROBADO", "RECHAZADO"):
        raise HTTPException(status_code=400, detail="Solo se puede reabrir la última versión, si está aprobada o rechazada.")
    doc.estado_revision = "REQUIERE_CORRECCION"
    doc.observaciones = data.motivo.strip()
    doc.revisado_por = current_user.id
    doc.fecha_revision = datetime.now()
    doc.reabierto = True
    estado_anterior = insc.estado_proceso
    if doc.requisito.es_obligatorio and insc.estado_proceso != "DOCUMENTACION_PENDIENTE":
        insc.estado_proceso = "DOCUMENTACION_PENDIENTE"
        insc.actualizado_en = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="REABRIR_DOCUMENTO", entidad="DOCUMENTO_POSTULANTE", entidad_id=str(doc.id),
        datos_anteriores_json=json.dumps({"estado_revision": "APROBADO", "estado_proceso": estado_anterior}),
        datos_nuevos_json=json.dumps({"estado_revision": "REQUIERE_CORRECCION", "estado_proceso": insc.estado_proceso,
                                      "motivo": doc.observaciones}, ensure_ascii=False)
    ))
    db.commit()
    correo_documento_revisado(db, insc, doc.requisito.nombre, "REQUIERE_CORRECCION", doc.observaciones)
    return {"mensaje": "Documento reabierto. El postulante debe subirlo de nuevo.", "estado_proceso": insc.estado_proceso}


@router.get("/{documento_id}/download")
def download_document(documento_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(DocumentoPostulante).filter(DocumentoPostulante.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    _inscripcion_accesible(db, current_user, doc.inscripcion_id)
    if not os.path.exists(doc.ruta_privada):
        raise HTTPException(status_code=404, detail="El archivo físico no se encuentra en el almacenamiento privado.")
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="DESCARGA_ARCHIVO", entidad="DOCUMENTO_POSTULANTE", entidad_id=str(doc.id)
    ))
    db.commit()
    return FileResponse(path=doc.ruta_privada, filename=doc.nombre_original, media_type=doc.mime_type)
