import io
from datetime import datetime, date
from html import escape
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from app.services.certificado import logo_flowable
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from sqlalchemy.orm import Session
from app.models.entities import (
    Inscripcion, Usuario, Programa, Convocatoria, CursoPreparatorio,
    ActividadCurso, AsignacionCurso, EntregaEvidencia, EvaluacionEvidencia,
    SeguimientoPostulante
)
from app.services.tutoria import nombres_tutores
from app.services.progress_service import calcular_avance, asignaciones_del_postulante

def generate_individual_pdf_report(db: Session, inscripcion_id: int) -> io.BytesIO:
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise ValueError("Inscripción no encontrada.")

    postulante = inscripcion.postulante
    convocatoria = inscripcion.convocatoria
    programa = convocatoria.programa

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#002D72'),
        alignment=1 # Centered
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#4B5563'),
        alignment=1
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#252533'),
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#252533')
    )

    story = []

    # Encabezado Institucional
    logo = logo_flowable()
    if logo:
        story.append(logo)
        story.append(Spacer(1, 6))
    story.append(Paragraph("UNIVERSIDAD INTERNACIONAL DEL ECUADOR (UIDE)", title_style))
    story.append(Paragraph("Dirección General de Posgrados - APP Maestría", subtitle_style))
    story.append(Paragraph("INFORME INDIVIDUAL DE SEGUIMIENTO ACADÉMICO PREPARATORIO", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#EAAA00'), spaceAfter=15))

    # Datos del Postulante y Programa
    tutor_nombre = nombres_tutores(db, inscripcion, "No asignado")
    avance = calcular_avance(db, inscripcion)
    perfil = postulante.perfil
    celda = ParagraphStyle('Celda', parent=body_style, fontSize=7.8, leading=9.6)
    cab = ParagraphStyle('Cab', parent=celda, fontName='Helvetica-Bold')
    P = lambda t, e=celda: Paragraph(escape(str(t)) if t not in (None, "") else "-", e)

    def tabla(filas, anchos, fondo):
        t = Table(filas, colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(fondo)),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return t

    def dato(etq, valor):
        return [Paragraph(f"<b>{etq}</b>", body_style), Paragraph(escape(str(valor)) if valor not in (None, "") else "N/A", body_style)]

    story.append(Paragraph("Datos personales y del programa", section_title))
    info_data = [
        dato("Postulante:", postulante.nombre_completo) + dato("Cédula:", postulante.cedula),
        dato("Correo:", postulante.email) + dato("Teléfono:", postulante.telefono),
        dato("Fecha de nacimiento:", perfil.fecha_nacimiento.strftime("%Y-%m-%d") if perfil and perfil.fecha_nacimiento else None)
        + dato("Ciudad:", perfil.ciudad if perfil else None),
        dato("Título:", perfil.titulo_tercer_nivel if perfil else None) + dato("Universidad:", perfil.universidad_origen if perfil else None),
        dato("Programa:", f"{programa.codigo} - {programa.nombre}") + dato("Convocatoria:", convocatoria.nombre),
        dato("Tutor(es):", tutor_nombre) + dato("Fecha de inscripción:", inscripcion.fecha_inscripcion.strftime("%Y-%m-%d")),
    ]
    info_table = Table(info_data, colWidths=[100, 165, 110, 155])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)

    # Estado y cumplimiento
    story.append(Paragraph("Estado y cumplimiento", section_title))
    resumen = Table([
        dato("Estado del proceso:", inscripcion.estado_proceso) + dato("Nivel de riesgo:", {"ALTO": "Alto (rojo)", "MEDIO": "Medio (amarillo)", "BAJO": "Al día (verde)"}.get(inscripcion.nivel_riesgo, inscripcion.nivel_riesgo)),
        dato("Cumplimiento:", f"{avance['porcentaje']}% ({avance['actividades_aprobadas']} de {avance['total_actividades']} actividades aprobadas)")
        + dato("Avance de la maestría:", f"{avance['porcentaje_maestria']}% ({avance['certificados_aprobados']} de {avance['total_cursos']} certificados verificados)"),
    ], colWidths=[100, 165, 110, 155])
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FDF5DC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#EAAA00')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(resumen)

    # 1. Cursos
    story.append(Paragraph("1. Cursos preparatorios", section_title))
    filas = [[P("Curso", cab), P("Tutor", cab), P("% completado", cab), P("Nota /100", cab), P("Resultado", cab), P("Certificado", cab)]]
    for c in avance["cursos"]:
        filas.append([P(f"{c['codigo']} - {c['nombre']}"), P(c["tutor_nombre"] or "Sin tutor"), P(f"{c['porcentaje']}%"),
                      P(f"{c['nota_final']:g} (mín. {c['nota_minima']:g})" if c["nota_final"] is not None else f"- (mín. {c['nota_minima']:g})"),
                      P(c["estado_aprobacion"] or "EN CURSO"), P(c["certificado_estado"] or "-")])
    story.append(tabla(filas, [150, 100, 60, 75, 70, 75], '#E6ECF5'))

    # 2. Actividades y evidencias
    story.append(Paragraph("2. Actividades, evidencias y calificaciones", section_title))
    filas = [[P("Actividad", cab), P("Pts", cab), P("Estado", cab), P("Evidencia entregada", cab), P("Nota", cab), P("Observación del tutor", cab)]]
    observaciones = []
    for asig_curso in asignaciones_del_postulante(db, inscripcion):
        actividades = db.query(ActividadCurso).filter(
            ActividadCurso.curso_id == asig_curso.curso_id,
            ActividadCurso.estado == 'ACTIVO'
        ).order_by(ActividadCurso.fecha_limite).all()
        for act in actividades:
            entrega = db.query(EntregaEvidencia).filter(
                EntregaEvidencia.asignacion_curso_id == asig_curso.id,
                EntregaEvidencia.actividad_id == act.id
            ).first()
            ultima = entrega.versiones[-1] if entrega and entrega.versiones else None
            ev = ultima.evaluacion if ultima else None
            evidencia = (f"{ultima.nombre_archivo_original} (v{ultima.numero_version}, {ultima.fecha_entrega.strftime('%Y-%m-%d %H:%M')}"
                         + (", tardía" if ultima.es_tardia else "") + ")") if ultima else "Sin entrega"
            if ev and ev.observaciones:
                observaciones.append(f"{act.titulo}: {ev.observaciones}")
            filas.append([
                P(f"{asig_curso.curso.codigo}: {act.titulo}"),
                P(f"{float(act.ponderacion):g}"),
                P(entrega.estado_entrega if entrega else "PENDIENTE"),
                P(evidencia),
                P(f"{float(ev.puntaje_obtenido):g}" if ev else "S/N"),
                P((ev.observaciones or ev.resultado) if ev else "-"),
            ])
    story.append(tabla(filas, [130, 30, 70, 140, 40, 120], '#E6ECF5'))

    # 3. Seguimientos
    story.append(Paragraph("3. Seguimientos del tutor", section_title))
    seguimientos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id
    ).order_by(SeguimientoPostulante.fecha_contacto.asc(), SeguimientoPostulante.id.asc()).all()
    if seguimientos:
        from app.services.history_service import TIPO_CONTACTO
        filas = [[P("N.º", cab), P("Fecha y hora", cab), P("Responsable", cab), P("Medio", cab), P("Resultado", cab),
                  P("Respuesta del postulante", cab), P("Compromisos / próxima acción", cab), P("Estado", cab)]]
        for n, s_ in enumerate(seguimientos, 1):
            compromisos = "; ".join(f"{c.descripcion} ({c.fecha_compromiso:%Y-%m-%d}{', cumplido' if c.cumplido else ''})" for c in s_.compromisos)
            proxima = (s_.proxima_accion or "") + (f" ({s_.fecha_proxima_accion:%Y-%m-%d})" if s_.fecha_proxima_accion else "")
            filas.append([
                P(s_.numero_seguimiento or n), P(s_.fecha_contacto.strftime("%Y-%m-%d %H:%M")), P(s_.tutor.nombre_completo),
                P(TIPO_CONTACTO.get(s_.tipo_contacto, s_.tipo_contacto) + (f" ({s_.dato_contacto})" if s_.dato_contacto else "")),
                P(s_.resultado), P(s_.respuesta_postulante or ("Respondió" if s_.hubo_respuesta else "SIN RESPUESTA")),
                P(" · ".join(x for x in [compromisos, proxima] if x) or "-"), P(s_.estado_caso),
            ])
            if s_.observaciones:
                observaciones.append(f"Seguimiento #{s_.numero_seguimiento or n}: {s_.observaciones}")
            if s_.recomendaciones:
                observaciones.append(f"Recomendación (seguimiento #{s_.numero_seguimiento or n}): {s_.recomendaciones}")
        story.append(tabla(filas, [25, 60, 70, 65, 85, 80, 85, 60], '#F7E6EE'))
    else:
        story.append(Paragraph("<i>No se registran contactos de seguimiento a la fecha.</i>", body_style))

    # 4. Observaciones
    story.append(Paragraph("4. Observaciones y recomendaciones", section_title))
    if inscripcion.nivel_riesgo != "BAJO" and inscripcion.motivo_riesgo:
        observaciones.insert(0, f"Riesgo: {inscripcion.motivo_riesgo}")
    if observaciones:
        for o in observaciones:
            story.append(Paragraph(f"• {escape(o)}", body_style))
    else:
        story.append(Paragraph("<i>Sin observaciones registradas.</i>", body_style))

    story.append(Spacer(1, 25))
    story.append(Paragraph(f"Informe generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sistema APP Maestría UIDE.", ParagraphStyle('Footer', parent=styles['Italic'], fontSize=8, textColor=colors.HexColor('#9CA3AF'), alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer

COLUMNAS_MATRIZ = [
    "Postulante", "Cédula", "Programa", "Convocatoria", "Fecha Inscripción",
    "% Avance", "Actividades Pendientes", "Días Pendientes", "Tutor Asignado",
    "# Seguimientos", "Estado", "Nivel de Riesgo"
]


def inscripciones_matriz(db: Session, programa_id: int = None, convocatoria_id: int = None, programa_ids: list = None,
                         inscripcion_ids: list = None):
    """
    Inscripciones de la matriz según los filtros y el alcance: programa_ids para el coordinador,
    inscripcion_ids para el tutor (solo sus postulantes).
    """
    query = db.query(Inscripcion)
    if inscripcion_ids is not None:
        query = query.filter(Inscripcion.id.in_(inscripcion_ids))
    if convocatoria_id:
        query = query.filter(Inscripcion.convocatoria_id == convocatoria_id)
    elif programa_id:
        query = query.filter(Inscripcion.convocatoria_id.in_(
            db.query(Convocatoria.id).filter(Convocatoria.programa_id == programa_id)
        ))
    if programa_ids is not None:
        query = query.filter(Inscripcion.convocatoria_id.in_(
            db.query(Convocatoria.id).filter(Convocatoria.programa_id.in_(programa_ids))
        ))
    return query.order_by(Inscripcion.convocatoria_id, Inscripcion.id).all()


def dias_pendientes(inscripcion: Inscripcion) -> int:
    """Días que faltan para el fin del preparatorio (0 si ya terminó)."""
    fin = inscripcion.convocatoria.fecha_fin_preparatorio
    return max(0, (fin - date.today()).days) if fin else 0


def filas_matriz(db: Session, inscripciones) -> list:
    """Mismas columnas para la matriz en Excel y en PDF."""
    filas = []
    for insc in inscripciones:
        post = insc.postulante
        conv = insc.convocatoria
        avance = calcular_avance(db, insc)
        filas.append([
            post.nombre_completo,
            post.cedula,
            conv.programa.codigo,
            conv.codigo,
            insc.fecha_inscripcion.strftime("%Y-%m-%d"),
            f"{avance['porcentaje']}%",
            avance["actividades_pendientes"],
            dias_pendientes(insc),
            nombres_tutores(db, insc, "Sin tutor"),
            db.query(SeguimientoPostulante).filter(SeguimientoPostulante.inscripcion_id == insc.id).count(),
            insc.estado_proceso,
            insc.nivel_riesgo,
        ])
    return filas


def generate_consolidated_excel_report(db: Session, programa_id: int = None, convocatoria_id: int = None, programa_ids: list = None,
                                       inscripcion_ids: list = None) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Matriz de Seguimiento"

    # Estilos UIDE
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="002D72", end_color="002D72", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="002D72")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="4B5563")
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = COLUMNAS_MATRIZ
    ultima = openpyxl.utils.get_column_letter(len(headers))

    # Título
    ws.merge_cells(f"A1:{ultima}1")
    ws["A1"] = "UNIVERSIDAD INTERNACIONAL DEL ECUADOR - DIRECCIÓN DE POSGRADOS"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(f"A2:{ultima}2")
    ws["A2"] = f"Matriz Consolidada de Seguimiento Académico - Cursos Preparatorios (Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')})"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    inscripciones = inscripciones_matriz(db, programa_id, convocatoria_id, programa_ids, inscripcion_ids)
    col_riesgo = headers.index("Nivel de Riesgo") + 1

    row_num = 5
    for fila in filas_matriz(db, inscripciones):
        for col_idx, val in enumerate(fila, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.border = border_thin
            if col_idx > 1:
                cell.alignment = Alignment(horizontal="center")
            # Pintar riesgo
            if col_idx == col_riesgo:
                if val == "ALTO":
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                    cell.font = Font(color="991B1B", bold=True)
                elif val == "MEDIO":
                    cell.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
                    cell.font = Font(color="92400E", bold=True)
                else:
                    cell.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
                    cell.font = Font(color="065F46", bold=True)
        row_num += 1

    # Autoajuste de columnas
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
