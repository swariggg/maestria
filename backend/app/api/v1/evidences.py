import os
import uuid
import hashlib
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, verify_applicant_access
from app.core.config import settings
from app.models.entities import (
    Usuario, ActividadCurso, AsignacionCurso, EntregaEvidencia, 
    VersionEvidencia, Inscripcion, RegistroAuditoria
)
from app.schemas.pydantic_models import EvidenceOut

router = APIRouter(prefix="/evidencias", tags=["Evidencias y Archivos"])

@router.get("/actividad/{actividad_id}/entrega")
def get_applicant_evidence(
    actividad_id: int, 
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para consultar esta evidencia.")

    asig_curso = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == inscripcion.id).first()
    if not asig_curso:
        raise HTTPException(status_code=404, detail="Postulante no tiene curso asignado.")

    entrega = db.query(EntregaEvidencia).filter(
        EntregaEvidencia.asignacion_curso_id == asig_curso.id,
        EntregaEvidencia.actividad_id == actividad_id
    ).first()

    if not entrega:
        return {"estado_entrega": "PENDIENTE", "numero_versiones": 0, "versiones": []}

    versiones = []
    for v in entrega.versiones:
        eval_data = None
        if v.evaluacion:
            eval_data = {
                "id": v.evaluacion.id,
                "puntaje_obtenido": float(v.evaluacion.puntaje_obtenido),
                "resultado": v.evaluacion.resultado,
                "observaciones": v.evaluacion.observaciones,
                "recomendaciones": v.evaluacion.recomendaciones,
                "evaluador_nombre": v.evaluacion.evaluador.nombre_completo,
                "fecha_evaluacion": v.evaluacion.fecha_evaluacion
            }
        versiones.append({
            "id": v.id,
            "numero_version": v.numero_version,
            "nombre_archivo_original": v.nombre_archivo_original,
            "tamano_bytes": v.tamano_bytes,
            "es_tardia": v.es_tardia,
            "fecha_entrega": v.fecha_entrega,
            "evaluacion": eval_data
        })

    return {
        "id": entrega.id,
        "actividad_id": actividad_id,
        "actividad_titulo": entrega.actividad.titulo,
        "estado_entrega": entrega.estado_entrega,
        "numero_versiones": entrega.numero_versiones,
        "versiones": versiones
    }

@router.post("/upload")
async def upload_evidence(
    actividad_id: int = Form(...),
    inscripcion_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    # Solo el postulante propietario o el admin pueden subir la evidencia
    if current_user.rol.codigo != "ADMIN" and current_user.id != inscripcion.postulante_id:
        raise HTTPException(status_code=403, detail="Solo el postulante autorizado puede cargar sus evidencias.")

    actividad = db.query(ActividadCurso).filter(ActividadCurso.id == actividad_id).first()
    if not actividad:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")

    # Validar extensión
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    permitidas = [e.strip().lower() for e in actividad.extensiones_permitidas.split(",")]
    if ext not in permitidas:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no permitido (. {ext}). Se admiten: {actividad.extensiones_permitidas}"
        )

    # Leer contenido
    content = await file.read()
    tamano_bytes = len(content)
    max_bytes = actividad.tamano_max_mb * 1024 * 1024
    if tamano_bytes > max_bytes:
        raise HTTPException(
            status_code=400, 
            detail=f"El archivo supera el tamaño máximo permitido de {actividad.tamano_max_mb} MB."
        )

    # Calcular Hash SHA-256
    sha256_hash = hashlib.sha256(content).hexdigest()

    # Guardar en almacenamiento privado seguro
    secure_filename = f"ev_{uuid.uuid4().hex[:12]}_{sha256_hash[:8]}.{ext}"
    private_path = os.path.join(settings.STORAGE_DIR, "evidencias", secure_filename)
    with open(private_path, "wb") as f:
        f.write(content)

    # Buscar o crear EntregaEvidencia
    asig_curso = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == inscripcion.id).first()
    if not asig_curso:
        raise HTTPException(status_code=400, detail="El postulante no tiene asignado el curso de esta actividad.")

    entrega = db.query(EntregaEvidencia).filter(
        EntregaEvidencia.asignacion_curso_id == asig_curso.id,
        EntregaEvidencia.actividad_id == actividad.id
    ).first()

    ahora = datetime.now()
    es_tardia = ahora > actividad.fecha_limite

    if not entrega:
        entrega = EntregaEvidencia(
            asignacion_curso_id=asig_curso.id,
            actividad_id=actividad.id,
            estado_entrega="ENTREGADO",
            numero_versiones=1
        )
        db.add(entrega)
        db.commit()
        db.refresh(entrega)
        nueva_version_num = 1
    else:
        if entrega.numero_versiones >= actividad.max_reenvios:
            raise HTTPException(
                status_code=400, 
                detail=f"Se ha alcanzado el límite de {actividad.max_reenvios} reenvíos para esta actividad."
            )
        entrega.numero_versiones += 1
        entrega.estado_entrega = "ENTREGADO"
        entrega.actualizada_en = ahora
        nueva_version_num = entrega.numero_versiones
        db.commit()

    # Registrar versión
    version = VersionEvidencia(
        entrega_id=entrega.id,
        numero_version=nueva_version_num,
        nombre_archivo_original=file.filename,
        nombre_archivo_seguro=secure_filename,
        ruta_privada=private_path,
        tamano_bytes=tamano_bytes,
        mime_type=file.content_type or "application/octet-stream",
        hash_sha256=sha256_hash,
        es_tardia=es_tardia,
        fecha_entrega=ahora
    )
    db.add(version)

    # Actualizar última fecha de avance de la inscripción
    inscripcion.fecha_ultimo_avance = ahora
    db.commit()

    # Registrar auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="UPLOAD_EVIDENCIA",
        entidad="VERSION_EVIDENCIA",
        entidad_id=str(version.id),
        datos_nuevos_json=f'{{"version": {nueva_version_num}, "archivo": "{file.filename}", "es_tardia": {str(es_tardia).lower()}}}'
    ))
    db.commit()

    return {
        "mensaje": "Evidencia cargada con éxito.",
        "version_id": version.id,
        "numero_version": nueva_version_num,
        "es_tardia": es_tardia
    }

@router.get("/version/{version_id}/download")
def download_evidence(
    version_id: int, 
    current_user: Usuario = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    version = db.query(VersionEvidencia).filter(VersionEvidencia.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Archivo de versión no encontrado.")

    entrega = version.entrega
    asig_curso = entrega.asignacion_curso
    inscripcion = asig_curso.inscripcion

    # Verificación de alcance de seguridad (ABAC)
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para descargar este documento privado.")

    if not os.path.exists(version.ruta_privada):
        raise HTTPException(status_code=404, detail="El archivo físico no se encuentra en el almacenamiento privado.")

    # Registrar auditoría de descarga
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="DESCARGA_ARCHIVO",
        entidad="VERSION_EVIDENCIA",
        entidad_id=str(version.id)
    ))
    db.commit()

    return FileResponse(
        path=version.ruta_privada,
        filename=version.nombre_archivo_original,
        media_type=version.mime_type
    )
