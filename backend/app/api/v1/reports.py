import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    get_current_user, require_roles, verify_applicant_access, verify_program_access,
    programas_del_coordinador, inscripciones_visibles
)
from app.models.entities import Usuario, Inscripcion, Convocatoria, Programa, RegistroAuditoria
from app.services.report_generator import (
    generate_individual_pdf_report, generate_consolidated_excel_report, inscripciones_matriz
)
from app.services.certificado import generar_certificado, buscar_por_codigo
from app.services.report_extra import (
    generate_consolidated_pdf, generate_traceability_pdf, generate_traceability_excel
)

router = APIRouter(prefix="/reportes", tags=["Reportes y Exportaciones"])

@router.get("/individual/{inscripcion_id}/pdf")
def get_individual_pdf_report(
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")

    # Validar permisos
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para generar este reporte individual.")

    pdf_buffer = generate_individual_pdf_report(db, inscripcion_id)

    # Auditoría
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="GENERAR_REPORTE_PDF",
        entidad="INSCRIPCION",
        entidad_id=str(inscripcion_id)
    ))
    db.commit()

    nombre_archivo = f"reporte_individual_{inscripcion.postulante.cedula}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )

def _alcance_matriz(user, db: Session, programa_id: int = None, convocatoria_id: int = None):
    """
    El coordinador solo exporta sus programas. Si pide uno ajeno, 403.
    Devuelve la lista de programas permitidos (None = todos, para el administrador y el tutor,
    a quien se filtra por sus postulantes con _inscripciones_tutor).
    """
    if user.rol.codigo in ("ADMIN", "TUTOR"):
        return None
    if convocatoria_id:
        conv = db.query(Convocatoria).filter(Convocatoria.id == convocatoria_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")
        programa_id = programa_id or conv.programa_id
        if conv.programa_id != programa_id:
            raise HTTPException(status_code=400, detail="La convocatoria no pertenece al programa indicado.")
    if programa_id and not verify_program_access(user, programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este programa.")
    return programas_del_coordinador(user, db)


def _inscripciones_tutor(user, db: Session):
    """El tutor solo ve en la matriz a sus postulantes asignados."""
    if user.rol.codigo != "TUTOR":
        return None
    return [i.id for i in inscripciones_visibles(user, db).all()]


@router.get("/matriz/excel")
def get_consolidated_excel(
    programa_id: int = Query(None),
    convocatoria_id: int = Query(None),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    programa_ids = _alcance_matriz(current_user, db, programa_id, convocatoria_id)
    excel_buffer = generate_consolidated_excel_report(
        db, programa_id=programa_id, convocatoria_id=convocatoria_id, programa_ids=programa_ids,
        inscripcion_ids=_inscripciones_tutor(current_user, db)
    )

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="GENERAR_MATRIZ_EXCEL",
        entidad="REPORTE_CONSOLIDADO"
    ))
    db.commit()

    nombre_archivo = f"matriz_seguimiento_uide_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )


PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _descripcion_filtro(db: Session, programa_id: int = None, convocatoria_id: int = None, inscripcion: Inscripcion = None) -> str:
    if inscripcion:
        return f"Postulante: {inscripcion.postulante.nombre_completo} (CI {inscripcion.postulante.cedula}) · {inscripcion.convocatoria.nombre}"
    if convocatoria_id:
        conv = db.query(Convocatoria).filter(Convocatoria.id == convocatoria_id).first()
        return f"Convocatoria: {conv.codigo} · {conv.nombre}" if conv else None
    if programa_id:
        prog = db.query(Programa).filter(Programa.id == programa_id).first()
        return f"Programa: {prog.codigo} · {prog.nombre}" if prog else None
    return "Todos los programas a su cargo"


def _archivo(contenido: io.BytesIO, media: str, nombre: str) -> Response:
    return Response(content=contenido.getvalue(), media_type=media,
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


@router.get("/matriz/pdf")
def get_consolidated_pdf(
    programa_id: int = Query(None),
    convocatoria_id: int = Query(None),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    programa_ids = _alcance_matriz(current_user, db, programa_id, convocatoria_id)
    inscripciones = inscripciones_matriz(db, programa_id, convocatoria_id, programa_ids, _inscripciones_tutor(current_user, db))
    filtro = _descripcion_filtro(db, programa_id, convocatoria_id)
    if current_user.rol.codigo == "TUTOR":
        filtro = f"Postulantes de {current_user.nombre_completo}" + (f" · {filtro}" if programa_id or convocatoria_id else "")
    pdf = generate_consolidated_pdf(db, inscripciones, filtro)
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="GENERAR_MATRIZ_PDF", entidad="REPORTE_CONSOLIDADO"))
    db.commit()
    return _archivo(pdf, PDF, f"matriz_seguimiento_uide_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")


@router.get("/trazabilidad/{formato}")
def get_traceability_report(
    formato: str,
    inscripcion_id: int = Query(None),
    programa_id: int = Query(None),
    convocatoria_id: int = Query(None),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    """Informe de trazabilidad por postulante, por convocatoria o por programa, en PDF o Excel."""
    if formato not in ("pdf", "excel"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use pdf o excel.")

    inscripcion = None
    if inscripcion_id:
        inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
        if not inscripcion:
            raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
        if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
            raise HTTPException(status_code=403, detail="No tiene autorización sobre este postulante.")
        inscripciones = [inscripcion]
    else:
        if current_user.rol.codigo == "COORDINADOR":
            _alcance_matriz(current_user, db, programa_id, convocatoria_id)
        # Cada rol ve solo a sus postulantes (el tutor, a los asignados)
        query = inscripciones_visibles(current_user, db)
        if convocatoria_id:
            query = query.filter(Inscripcion.convocatoria_id == convocatoria_id)
        elif programa_id:
            query = query.filter(Inscripcion.convocatoria_id.in_(
                db.query(Convocatoria.id).filter(Convocatoria.programa_id == programa_id)
            ))
        inscripciones = query.order_by(Inscripcion.id).all()

    filtro = _descripcion_filtro(db, programa_id, convocatoria_id, inscripcion)
    sello = datetime.now().strftime('%Y%m%d_%H%M')
    sufijo = f"_{inscripcion.postulante.cedula}" if inscripcion else ""
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion=f"GENERAR_TRAZABILIDAD_{formato.upper()}", entidad="REPORTE_TRAZABILIDAD",
        entidad_id=str(inscripcion_id) if inscripcion_id else None
    ))
    db.commit()
    if formato == "pdf":
        return _archivo(generate_traceability_pdf(db, inscripciones, filtro), PDF, f"trazabilidad{sufijo}_{sello}.pdf")
    return _archivo(generate_traceability_excel(db, inscripciones, filtro), XLSX, f"trazabilidad{sufijo}_{sello}.xlsx")


@router.get("/certificado/verificar/{codigo}")
def verify_certificate(codigo: str, db: Session = Depends(get_db)):
    """Público: confirma que un certificado es auténtico. Solo devuelve lo que ya figura en él."""
    insc = buscar_por_codigo(db, codigo)
    if not insc:
        raise HTTPException(status_code=404, detail="No existe un certificado con ese código.")
    return {
        "valido": True,
        "postulante": insc.postulante.nombre_completo,
        "programa": insc.convocatoria.programa.nombre,
        "convocatoria": insc.convocatoria.codigo,
    }


@router.get("/certificado/{inscripcion_id}")
def get_certificate(
    inscripcion_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
    if not verify_applicant_access(current_user, inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este postulante.")
    if inscripcion.estado_proceso != "APROBADO":
        raise HTTPException(status_code=400, detail="El certificado solo se emite cuando el proceso está aprobado.")
    pdf = generar_certificado(db, inscripcion)
    db.add(RegistroAuditoria(usuario_id=current_user.id, accion="GENERAR_CERTIFICADO", entidad="INSCRIPCION",
                             entidad_id=str(inscripcion.id)))
    db.commit()
    return _archivo(pdf, PDF, f"certificado_{inscripcion.postulante.cedula}.pdf")
