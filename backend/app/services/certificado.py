"""
Certificado de aprobación del curso preparatorio.

Lleva un código de verificación derivado de la inscripción y la clave del sistema: cualquiera
puede comprobarlo en /reportes/certificado/verificar/{codigo} sin iniciar sesión.
"""
import hmac
import hashlib
import io
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Inscripcion
from app.services.progress_service import asignaciones_del_postulante

AZUL = colors.HexColor('#002D72')
VINO = colors.HexColor('#910048')
GRIS = colors.HexColor('#4B5563')
LOGO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "uide-logo.png")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def logo_flowable(alto: float = 40):
    """Logo UIDE para encabezados de PDF (platypus), respetando su proporción."""
    from reportlab.platypus import Image
    if not os.path.exists(LOGO):
        return None
    w, h = ImageReader(LOGO).getSize()
    img = Image(LOGO, width=w * alto / h, height=alto)
    img.hAlign = 'CENTER'
    return img


def codigo_verificacion(inscripcion: Inscripcion) -> str:
    firma = hmac.new(settings.SECRET_KEY.encode(), f"CERT-{inscripcion.id}-{inscripcion.postulante_id}".encode(), hashlib.sha256)
    c = firma.hexdigest()[:12].upper()
    return f"{c[:4]}-{c[4:8]}-{c[8:]}"


def buscar_por_codigo(db: Session, codigo: str):
    codigo = codigo.strip().upper()
    for insc in db.query(Inscripcion).filter(Inscripcion.estado_proceso == "APROBADO").all():
        if hmac.compare_digest(codigo_verificacion(insc), codigo):
            return insc
    return None


def _fecha_larga(d) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def generar_certificado(db: Session, inscripcion: Inscripcion) -> io.BytesIO:
    buf = io.BytesIO()
    ancho, alto = landscape(letter)
    c = canvas.Canvas(buf, pagesize=(ancho, alto))
    c.setTitle(f"Certificado - {inscripcion.postulante.nombre_completo}")

    # Marco
    c.setStrokeColor(AZUL); c.setLineWidth(3); c.rect(28, 28, ancho - 56, alto - 56)
    c.setStrokeColor(VINO); c.setLineWidth(1); c.rect(36, 36, ancho - 72, alto - 72)

    y = alto - 70
    if os.path.exists(LOGO):
        img = ImageReader(LOGO)
        w, h = img.getSize()
        alto_logo = 60
        ancho_logo = w * alto_logo / h
        c.drawImage(img, (ancho - ancho_logo) / 2, y - alto_logo, ancho_logo, alto_logo, mask='auto')
        y -= alto_logo + 22
    c.setFillColor(AZUL); c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(ancho / 2, y, "UNIVERSIDAD INTERNACIONAL DEL ECUADOR")
    c.setFillColor(GRIS); c.setFont("Helvetica", 10.5)
    c.drawCentredString(ancho / 2, y - 16, "Dirección General de Posgrados")

    y -= 58
    c.setFillColor(VINO); c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(ancho / 2, y, "CERTIFICADO DE APROBACIÓN")
    c.setFillColor(GRIS); c.setFont("Helvetica", 12)
    c.drawCentredString(ancho / 2, y - 30, "Se certifica que")
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(ancho / 2, y - 60, inscripcion.postulante.nombre_completo)
    c.setFillColor(GRIS); c.setFont("Helvetica", 11)
    c.drawCentredString(ancho / 2, y - 78, f"con cédula de identidad N.º {inscripcion.postulante.cedula},")

    conv = inscripcion.convocatoria
    c.setFont("Helvetica", 12); c.setFillColor(colors.black)
    c.drawCentredString(ancho / 2, y - 104, "aprobó el curso preparatorio de admisión a la")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(ancho / 2, y - 122, conv.programa.nombre)
    c.setFont("Helvetica", 11); c.setFillColor(GRIS)
    periodo = ""
    if conv.fecha_inicio_preparatorio and conv.fecha_fin_preparatorio:
        periodo = f", del {_fecha_larga(conv.fecha_inicio_preparatorio)} al {_fecha_larga(conv.fecha_fin_preparatorio)}"
    c.drawCentredString(ancho / 2, y - 140, f"Convocatoria {conv.codigo}{periodo}.")

    notas = [f"{a.curso.codigo}: {float(a.nota_final):g}" for a in asignaciones_del_postulante(db, inscripcion) if a.nota_final is not None]
    if notas:
        c.setFont("Helvetica", 10)
        c.drawCentredString(ancho / 2, y - 158, "Calificaciones: " + " · ".join(notas))

    # Firma
    fy = 120
    c.setStrokeColor(colors.black); c.setLineWidth(0.8)
    c.line(ancho / 2 - 120, fy, ancho / 2 + 120, fy)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(ancho / 2, fy - 14, "Coordinación del programa")
    c.setFont("Helvetica", 9.5); c.setFillColor(GRIS)
    c.drawCentredString(ancho / 2, fy - 27, "Dirección General de Posgrados - UIDE")

    # Pie con código de verificación
    c.setFont("Helvetica", 8.5)
    c.drawString(52, 50, f"Emitido el {_fecha_larga(datetime.now())}")
    c.drawRightString(ancho - 52, 50, f"Código de verificación: {codigo_verificacion(inscripcion)}")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf
