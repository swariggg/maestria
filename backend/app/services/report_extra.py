"""
Matriz consolidada en PDF e informe de trazabilidad (PDF y Excel).

La matriz usa las mismas filas que el Excel (filas_matriz), así las cifras coinciden.
La trazabilidad lista cada seguimiento del tutor con su número, responsable, acción,
resultado, respuesta del postulante, compromisos, próxima acción y estado final.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.services.certificado import logo_flowable
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy.orm import Session
from app.models.entities import SeguimientoPostulante
from app.services.report_generator import COLUMNAS_MATRIZ, filas_matriz

AZUL = colors.HexColor('#002D72')
VINO = colors.HexColor('#910048')
GRIS = colors.HexColor('#4B5563')
BORDE = colors.HexColor('#CBD5E1')

COLUMNAS_TRAZABILIDAD = [
    "Postulante", "Cédula", "N.º", "Fecha", "Responsable", "Tipo de contacto", "Motivo",
    "Acción realizada", "Resultado", "Respuesta del postulante", "Compromisos",
    "Próxima acción", "Estado final", "Evidencia asociada"
]


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle('T', parent=base['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=AZUL, alignment=1),
        "sub": ParagraphStyle('S', parent=base['Normal'], fontName='Helvetica', fontSize=9.5, leading=12, textColor=GRIS, alignment=1),
        "celda": ParagraphStyle('C', parent=base['Normal'], fontName='Helvetica', fontSize=7.2, leading=9),
        "cab": ParagraphStyle('H', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=7.4, leading=9, textColor=colors.white),
        "pie": ParagraphStyle('P', parent=base['Italic'], fontSize=7.5, textColor=colors.HexColor('#9CA3AF'), alignment=1),
    }


def _encabezado(story, est, titulo, filtro):
    logo = logo_flowable()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 6))
    story.append(Paragraph("UNIVERSIDAD INTERNACIONAL DEL ECUADOR (UIDE)", est["titulo"]))
    story.append(Paragraph("Dirección General de Posgrados - APP Maestría", est["sub"]))
    story.append(Paragraph(titulo, est["sub"]))
    if filtro:
        story.append(Paragraph(filtro, est["sub"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.2, color=VINO, spaceAfter=10))


def _tabla(filas, cabeceras, anchos, est, resaltar_col=None):
    datos = [[Paragraph(h, est["cab"]) for h in cabeceras]]
    datos += [[Paragraph(str(v) if v is not None else "", est["celda"]) for v in f] for f in filas]
    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    estilo = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F7FA')]),
    ]
    if resaltar_col is not None:
        for i, f in enumerate(filas, 1):
            color = {"ALTO": '#FEE2E2', "MEDIO": '#FEF3C7'}.get(f[resaltar_col], '#D1FAE5')
            estilo.append(('BACKGROUND', (resaltar_col, i), (resaltar_col, i), colors.HexColor(color)))
    tabla.setStyle(TableStyle(estilo))
    return tabla


def _pdf(story_builder) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
    doc.build(story_builder())
    buffer.seek(0)
    return buffer


# ---------- Matriz consolidada en PDF ----------

def generate_consolidated_pdf(db: Session, inscripciones, filtro: str = None) -> io.BytesIO:
    est = _estilos()
    filas = filas_matriz(db, inscripciones)

    def construir():
        story = []
        _encabezado(story, est, "MATRIZ CONSOLIDADA DE SEGUIMIENTO ACADÉMICO - CURSOS PREPARATORIOS", filtro)
        if not filas:
            story.append(Paragraph("<i>No hay postulantes para los filtros seleccionados.</i>", est["celda"]))
        else:
            anchos = [104, 58, 48, 62, 56, 42, 60, 52, 80, 64, 66, 52]  # 744 pt = ancho útil horizontal
            story.append(_tabla(filas, COLUMNAS_MATRIZ, anchos, est, resaltar_col=COLUMNAS_MATRIZ.index("Nivel de Riesgo")))
            altos = sum(1 for f in filas if f[-1] == "ALTO")
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"Total: {len(filas)} postulantes · Riesgo alto: {altos}", est["celda"]))
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} - Sistema APP Maestría UIDE.", est["pie"]))
        return story

    return _pdf(construir)


# ---------- Informe de trazabilidad ----------

def filas_trazabilidad(db: Session, inscripciones) -> list:
    filas = []
    for insc in inscripciones:
        seguimientos = db.query(SeguimientoPostulante).filter(
            SeguimientoPostulante.inscripcion_id == insc.id
        ).order_by(SeguimientoPostulante.fecha_contacto.asc(), SeguimientoPostulante.id.asc()).all()
        for n, s in enumerate(seguimientos, 1):
            compromisos = "; ".join(
                f"{c.descripcion} ({c.fecha_compromiso.strftime('%Y-%m-%d')}{', cumplido' if c.cumplido else ''})"
                for c in s.compromisos
            )
            proxima = s.proxima_accion or ""
            if s.fecha_proxima_accion:
                proxima += f" ({s.fecha_proxima_accion.strftime('%Y-%m-%d')})"
            filas.append([
                insc.postulante.nombre_completo,
                insc.postulante.cedula,
                s.numero_seguimiento or n,
                s.fecha_contacto.strftime("%Y-%m-%d %H:%M"),
                s.tutor.nombre_completo,
                s.tipo_contacto,
                s.motivo,
                s.accion_realizada,
                s.resultado,
                s.respuesta_postulante or ("Respondió" if s.hubo_respuesta else "SIN RESPUESTA"),
                compromisos or "-",
                proxima or "-",
                s.estado_caso,
                s.evidencia_nombre_original or "-",
            ])
    return filas


def generate_traceability_pdf(db: Session, inscripciones, filtro: str = None) -> io.BytesIO:
    est = _estilos()
    filas = filas_trazabilidad(db, inscripciones)

    def construir():
        story = []
        _encabezado(story, est, "INFORME DE TRAZABILIDAD DEL SEGUIMIENTO ACADÉMICO", filtro)
        if not filas:
            story.append(Paragraph("<i>No se registran seguimientos para los filtros seleccionados.</i>", est["celda"]))
        else:
            anchos = [64, 54, 24, 60, 60, 58, 48, 62, 60, 56, 58, 48, 44, 48]  # 744 pt = ancho útil horizontal
            story.append(_tabla(filas, COLUMNAS_TRAZABILIDAD, anchos, est))
            story.append(Spacer(1, 8))
            sin_resp = sum(1 for f in filas if f[9] == "SIN RESPUESTA")
            story.append(Paragraph(f"Total: {len(filas)} seguimientos · Sin respuesta: {sin_resp}", est["celda"]))
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} - Sistema APP Maestría UIDE.", est["pie"]))
        return story

    return _pdf(construir)


def generate_traceability_excel(db: Session, inscripciones, filtro: str = None) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Trazabilidad"
    ultima = openpyxl.utils.get_column_letter(len(COLUMNAS_TRAZABILIDAD))
    borde = Border(*(Side(style='thin', color='CBD5E1'),) * 4)

    ws.merge_cells(f"A1:{ultima}1")
    ws["A1"] = "UNIVERSIDAD INTERNACIONAL DEL ECUADOR - INFORME DE TRAZABILIDAD DEL SEGUIMIENTO"
    ws["A1"].font = Font(size=14, bold=True, color="002D72")
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells(f"A2:{ultima}2")
    ws["A2"] = f"{filtro + ' · ' if filtro else ''}Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws["A2"].font = Font(size=10, italic=True, color="4B5563")
    ws["A2"].alignment = Alignment(horizontal="center")

    for col, h in enumerate(COLUMNAS_TRAZABILIDAD, 1):
        c = ws.cell(row=4, column=col, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill(start_color="002D72", end_color="002D72", fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = borde

    for r, fila in enumerate(filas_trazabilidad(db, inscripciones), 5):
        for col, val in enumerate(fila, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.border = borde
            c.alignment = Alignment(vertical="top", wrap_text=True)

    anchos = [28, 13, 6, 16, 22, 16, 26, 34, 30, 28, 30, 24, 13, 22]
    for i, w in enumerate(anchos, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A5"

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
