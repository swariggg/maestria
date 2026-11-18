import os
import json
import uuid
import hashlib
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Usuario, Inscripcion, SeguimientoPostulante, CompromisoSeguimiento, RegistroAuditoria
)
from app.schemas.pydantic_models import FollowupCreate, FollowupOut, CompromisoOut
from app.services.risk_engine import evaluate_applicant_risk

router = APIRouter(prefix="/seguimientos", tags=["Seguimiento de Postulantes"])

TIPOS_CONTACTO = ["TELEFONO", "CORREO", "WHATSAPP", "TEAMS", "VIDEOCONFERENCIA", "PRESENCIAL"]
ESTADOS_CASO = ["ABIERTO", "EN_PROCESO", "RESUELTO", "ESCALADO"]
EXTENSIONES_EVIDENCIA = ["pdf", "jpg", "jpeg", "png", "docx", "txt"]
MAX_EVIDENCIA_MB = 10


def numero_de(db: Session, seg: SeguimientoPostulante) -> int:
    """Número correlativo del seguimiento dentro del postulante (1, 2, 3...)."""
    if seg.numero_seguimiento:
        return seg.numero_seguimiento
    anteriores = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == seg.inscripcion_id,
        (SeguimientoPostulante.fecha_contacto < seg.fecha_contacto) |
        ((SeguimientoPostulante.fecha_contacto == seg.fecha_contacto) & (SeguimientoPostulante.id < seg.id))
    ).count()
    return anteriores + 1


def followup_out(db: Session, s: SeguimientoPostulante) -> FollowupOut:
    return FollowupOut(
        id=s.id,
        inscripcion_id=s.inscripcion_id,
        tutor_id=s.tutor_id,
        tutor_nombre=s.tutor.nombre_completo,
        fecha_contacto=s.fecha_contacto,
        tipo_contacto=s.tipo_contacto,
        motivo=s.motivo,
        accion_realizada=s.accion_realizada,
        resultado=s.resultado,
        respuesta_postulante=s.respuesta_postulante,
        hubo_respuesta=s.hubo_respuesta,
        proxima_accion=s.proxima_accion,
        fecha_proxima_accion=s.fecha_proxima_accion,
        estado_caso=s.estado_caso,
        creado_en=s.creado_en,
        numero_seguimiento=numero_de(db, s),
        observaciones=s.observaciones,
        recomendaciones=s.recomendaciones,
        evidencia_nombre=s.evidencia_nombre_original,
        dato_contacto=s.dato_contacto,
        compromisos=[CompromisoOut.model_validate(c) for c in s.compromisos],
    )


def _seguimiento_accesible(db: Session, user: Usuario, seguimiento_id: int) -> SeguimientoPostulante:
    seg = db.query(SeguimientoPostulante).filter(SeguimientoPostulante.id == seguimiento_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado.")
    if not verify_applicant_access(user, seg.inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este postulante.")
    return seg


@router.get("/inscripcion/{inscripcion_id}", response_model=List[FollowupOut])
def get_followups_by_enrollment(
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para ver los seguimientos de este postulante.")

    seguimientos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion_id
    ).order_by(SeguimientoPostulante.fecha_contacto.desc()).all()
    salida = [followup_out(db, s) for s in seguimientos]
    if current_user.rol.codigo == "POSTULANTE":
        for f in salida:
            f.observaciones = None  # notas internas del tutor
    return salida


@router.post("", response_model=FollowupOut)
def create_followup(
    data: FollowupCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == data.inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para registrar seguimientos para este postulante.")
    if data.tipo_contacto not in TIPOS_CONTACTO:
        raise HTTPException(status_code=400, detail=f"Tipo de contacto inválido. Use: {', '.join(TIPOS_CONTACTO)}.")
    if data.estado_caso not in ESTADOS_CASO:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {', '.join(ESTADOS_CASO)}.")

    numero = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id
    ).count() + 1

    seguimiento = SeguimientoPostulante(
        inscripcion_id=data.inscripcion_id,
        tutor_id=current_user.id,
        fecha_contacto=data.fecha_contacto,
        tipo_contacto=data.tipo_contacto,
        dato_contacto=(data.dato_contacto or "").strip() or None,
        motivo=data.motivo,
        accion_realizada=data.accion_realizada,
        resultado=data.resultado,
        respuesta_postulante=data.respuesta_postulante,
        hubo_respuesta=data.hubo_respuesta,
        proxima_accion=data.proxima_accion,
        fecha_proxima_accion=data.fecha_proxima_accion,
        estado_caso=data.estado_caso,
        numero_seguimiento=numero,
        observaciones=data.observaciones,
        recomendaciones=data.recomendaciones,
    )
    db.add(seguimiento)
    db.flush()
    for comp in data.compromisos:
        db.add(CompromisoSeguimiento(
            seguimiento_id=seguimiento.id,
            descripcion=comp.descripcion.strip(),
            fecha_compromiso=comp.fecha_compromiso,
            cumplido=False
        ))

    # Si hubo respuesta, cuenta como actividad del postulante
    if data.hubo_respuesta:
        inscripcion.fecha_ultimo_avance = datetime.now()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="REGISTRAR_SEGUIMIENTO",
        entidad="SEGUIMIENTO_POSTULANTE",
        entidad_id=str(seguimiento.id),
        datos_nuevos_json=json.dumps({
            "numero": numero, "tipo": data.tipo_contacto, "hubo_respuesta": data.hubo_respuesta,
            "compromisos": len(data.compromisos)
        })
    ))
    db.commit()

    # Recalcular automáticamente el riesgo
    evaluate_applicant_risk(db, inscripcion.id)
    db.refresh(seguimiento)
    return followup_out(db, seguimiento)


@router.post("/{seguimiento_id}/evidencia", response_model=FollowupOut)
async def upload_followup_evidence(
    seguimiento_id: int,
    file: UploadFile = File(...),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    """Evidencia del contacto: captura de un chat, acta de reunión, correo exportado..."""
    seg = _seguimiento_accesible(db, current_user, seguimiento_id)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in EXTENSIONES_EVIDENCIA:
        raise HTTPException(status_code=400, detail=f"Formato no permitido. Se admiten: {', '.join(EXTENSIONES_EVIDENCIA)}.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > MAX_EVIDENCIA_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"El archivo supera {MAX_EVIDENCIA_MB} MB.")

    sha256 = hashlib.sha256(content).hexdigest()
    carpeta = os.path.join(settings.STORAGE_DIR, "seguimientos")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"seg_{uuid.uuid4().hex[:12]}_{sha256[:8]}.{ext}")
    with open(ruta, "wb") as f:
        f.write(content)

    reemplaza = seg.evidencia_nombre_original
    seg.evidencia_nombre_original = file.filename
    seg.evidencia_ruta_privada = ruta
    seg.evidencia_mime_type = file.content_type or "application/octet-stream"
    seg.evidencia_hash_sha256 = sha256
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="EVIDENCIA_SEGUIMIENTO", entidad="SEGUIMIENTO_POSTULANTE",
        entidad_id=str(seg.id),
        datos_nuevos_json=json.dumps({"archivo": file.filename, "reemplaza": reemplaza}, ensure_ascii=False)
    ))
    db.commit()
    db.refresh(seg)
    return followup_out(db, seg)


@router.get("/{seguimiento_id}/evidencia")
def download_followup_evidence(seguimiento_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    seg = _seguimiento_accesible(db, current_user, seguimiento_id)
    if not seg.evidencia_ruta_privada or not os.path.exists(seg.evidencia_ruta_privada):
        raise HTTPException(status_code=404, detail="Este seguimiento no tiene evidencia adjunta.")
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="DESCARGA_ARCHIVO", entidad="SEGUIMIENTO_POSTULANTE", entidad_id=str(seg.id)
    ))
    db.commit()
    return FileResponse(path=seg.evidencia_ruta_privada, filename=seg.evidencia_nombre_original, media_type=seg.evidencia_mime_type)


@router.patch("/compromisos/{compromiso_id}/cumplido", response_model=CompromisoOut)
def mark_commitment_done(
    compromiso_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    comp = db.query(CompromisoSeguimiento).filter(CompromisoSeguimiento.id == compromiso_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compromiso no encontrado.")
    _seguimiento_accesible(db, current_user, comp.seguimiento_id)
    if comp.cumplido:
        raise HTTPException(status_code=400, detail="El compromiso ya está marcado como cumplido.")
    comp.cumplido = True
    comp.fecha_cumplimiento = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="COMPROMISO_CUMPLIDO", entidad="COMPROMISO_SEGUIMIENTO", entidad_id=str(comp.id)
    ))
    db.commit()
    db.refresh(comp)
    return comp
