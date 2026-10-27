from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import Usuario, Inscripcion, RegistroAuditoria
from app.services.report_generator import generate_individual_pdf_report, generate_consolidated_excel_report

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

@router.get("/matriz/excel")
def get_consolidated_excel(
    programa_id: int = Query(None),
    convocatoria_id: int = Query(None),
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    excel_buffer = generate_consolidated_excel_report(db, programa_id=programa_id, convocatoria_id=convocatoria_id)

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
