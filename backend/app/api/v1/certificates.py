"""
Certificados de curso.

Al aprobar un curso (70/100 o la nota mínima que fije el coordinador) la app emite el certificado
en PDF. Queda en "Certificados" como pendiente hasta que el tutor del curso lo verifica; recién ahí
cuenta para el porcentaje de avance de la maestría.
"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access, inscripciones_visibles
from app.models.entities import Usuario, AsignacionCurso, CursoPreparatorio, Inscripcion, RegistroAuditoria
from app.services.certificado import generar_certificado_curso
from app.services.progress_service import actualizar_estado_inscripcion, calcular_avance, ESTADOS_INSCRIPCION_CERRADA

router = APIRouter(prefix="/certificados", tags=["Certificados de curso"])


class RevisionCertificado(BaseModel):
    aprobar: bool
    observacion: Optional[str] = Field(default=None, max_length=500)


def _out(a: AsignacionCurso) -> dict:
    insc = a.inscripcion
    return {
        "asignacion_id": a.id, "inscripcion_id": insc.id, "curso_id": a.curso_id,
        "curso_codigo": a.curso.codigo, "curso_nombre": a.curso.nombre,
        "postulante_id": insc.postulante_id, "postulante_nombre": insc.postulante.nombre_completo,
        "programa": insc.convocatoria.programa.nombre, "nota_final": float(a.nota_final) if a.nota_final is not None else None,
        "estado_aprobacion": a.estado_aprobacion, "certificado_estado": a.certificado_estado,
        "emitido_en": a.certificado_emitido_en, "revisado_en": a.certificado_revisado_en,
        "observacion": a.certificado_observacion,
        "tutor_nombre": a.curso.tutor.nombre_completo if a.curso.tutor else None,
    }


def _puede_revisar(user: Usuario, a: AsignacionCurso) -> bool:
    """Lo verifica el tutor del curso; el coordinador o el admin solo si el curso no tiene tutor."""
    if a.curso.tutor_id:
        return user.id == a.curso.tutor_id
    return user.rol.codigo in ("ADMIN", "COORDINADOR")


@router.get("/inscripcion/{inscripcion_id}")
def list_by_enrollment(inscripcion_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Todos los cursos del postulante con el estado de su certificado y el % de la maestría."""
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc or not verify_applicant_access(current_user, insc.postulante_id, db):
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    avance = calcular_avance(db, insc)
    asignaciones = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == insc.id).order_by(AsignacionCurso.id).all()
    return {
        "inscripcion_id": insc.id, "programa": insc.convocatoria.programa.nombre,
        "total_cursos": avance["total_cursos"], "certificados_aprobados": avance["certificados_aprobados"],
        "porcentaje_maestria": avance["porcentaje_maestria"],
        "cursos": [_out(a) for a in asignaciones],
    }


@router.get("/pendientes")
def list_pending(current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")), db: Session = Depends(get_db)):
    """Certificados que esperan la verificación de quien consulta."""
    ids = [i.id for i in inscripciones_visibles(current_user, db).filter(
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)).all()]
    if not ids:
        return []
    filas = db.query(AsignacionCurso).filter(
        AsignacionCurso.inscripcion_id.in_(ids), AsignacionCurso.certificado_estado == "PENDIENTE"
    ).order_by(AsignacionCurso.certificado_emitido_en).all()
    return [_out(a) for a in filas if _puede_revisar(current_user, a)]


@router.get("/{asignacion_id}/pdf")
def download(asignacion_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(AsignacionCurso).filter(AsignacionCurso.id == asignacion_id).first()
    if not a or not verify_applicant_access(current_user, a.inscripcion.postulante_id, db):
        raise HTTPException(status_code=404, detail="Certificado no encontrado.")
    if not a.certificado_estado:
        raise HTTPException(status_code=400, detail="El certificado se emite cuando se aprueba el curso.")
    pdf = generar_certificado_curso(db, a)
    nombre = f"certificado_{a.curso.codigo}_{a.inscripcion.postulante.cedula}.pdf"
    return Response(content=pdf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


@router.patch("/{asignacion_id}/revision")
def review(asignacion_id: int, data: RevisionCertificado,
           current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")), db: Session = Depends(get_db)):
    a = db.query(AsignacionCurso).filter(AsignacionCurso.id == asignacion_id).first()
    if not a or not verify_applicant_access(current_user, a.inscripcion.postulante_id, db):
        raise HTTPException(status_code=404, detail="Certificado no encontrado.")
    if not _puede_revisar(current_user, a):
        raise HTTPException(status_code=403, detail="Solo el tutor del curso puede verificar este certificado.")
    if a.inscripcion.estado_proceso in ESTADOS_INSCRIPCION_CERRADA:
        raise HTTPException(status_code=400, detail=f"La inscripción está cerrada ({a.inscripcion.estado_proceso}).")
    if not a.certificado_estado:
        raise HTTPException(status_code=400, detail="El curso todavía no está aprobado.")
    observacion = (data.observacion or "").strip() or None
    if not data.aprobar and (not observacion or len(observacion) < 5):
        raise HTTPException(status_code=400, detail="Para devolver el certificado indique qué hay que revisar.")
    anterior = a.certificado_estado
    a.certificado_estado = "APROBADO" if data.aprobar else "DEVUELTO"
    a.certificado_revisado_por = current_user.id
    a.certificado_revisado_en = datetime.now()
    a.certificado_observacion = observacion
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="VERIFICAR_CERTIFICADO" if data.aprobar else "DEVOLVER_CERTIFICADO",
        entidad="ASIGNACION_CURSO", entidad_id=str(a.id),
        datos_anteriores_json=json.dumps({"certificado_estado": anterior}),
        datos_nuevos_json=json.dumps({"certificado_estado": a.certificado_estado, "observacion": observacion}, ensure_ascii=False)
    ))
    db.flush()
    aprobo = actualizar_estado_inscripcion(db, a.inscripcion, current_user.id)
    db.commit()
    db.refresh(a)
    from app.services.process_emails import correo_certificado_revisado, correo_proceso_aprobado
    correo_certificado_revisado(db, a)
    if aprobo:
        correo_proceso_aprobado(db, a.inscripcion)
    return _out(a)
