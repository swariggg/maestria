import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.entities import (
    NotificacionCola, RegistroIntentoEnvio, ActividadCurso, 
    AsignacionCurso, Inscripcion, Usuario, PlantillaNotificacion
)
from app.core.config import settings

def send_or_queue_notification(
    db: Session,
    destinatario: Usuario,
    tipo_evento: str,
    asunto: str,
    cuerpo_html: str
) -> NotificacionCola:
    notif = NotificacionCola(
        destinatario_id=destinatario.id,
        email_destinatario=destinatario.email,
        tipo_evento=tipo_evento,
        asunto=asunto,
        cuerpo_html=cuerpo_html,
        estado="PENDIENTE",
        intentos=0
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Procesar envío inmediato (en segundo plano o sincronizado en desarrollo)
    process_single_notification(db, notif)
    return notif

def process_single_notification(db: Session, notif: NotificacionCola) -> bool:
    notif.intentos += 1
    notif.fecha_ultimo_intento = datetime.now()

    # Si está en modo de prueba, simular éxito y registrar
    if settings.SMTP_TEST_MODE:
        notif.estado = "ENVIADO"
        intento = RegistroIntentoEnvio(
            notificacion_id=notif.id,
            exito=True,
            respuesta_smtp="[MODO PRUEBA SMTP SIMULADO - Mensaje aceptado localmente]",
            error_detalle=None
        )
        db.add(intento)
        db.commit()
        return True

    # Intento SMTP Real
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = notif.asunto
        msg["From"] = settings.SMTP_FROM
        msg["To"] = notif.email_destinatario

        part = MIMEText(notif.cuerpo_html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [notif.email_destinatario], msg.as_string())

        notif.estado = "ENVIADO"
        intento = RegistroIntentoEnvio(
            notificacion_id=notif.id,
            exito=True,
            respuesta_smtp="250 OK Mensaje enviado a servidor SMTP institucional",
            error_detalle=None
        )
        db.add(intento)
        db.commit()
        return True
    except Exception as e:
        notif.estado = "FALLIDO" if notif.intentos >= 3 else "PENDIENTE"
        intento = RegistroIntentoEnvio(
            notificacion_id=notif.id,
            exito=False,
            respuesta_smtp="ERROR_CONEXION",
            error_detalle=str(e)
        )
        db.add(intento)
        db.commit()
        return False

def check_and_send_deadline_reminders(db: Session) -> dict:
    """Revisa recordatorios a los 15, 10, 5, 3 y 1 día antes del vencimiento sin duplicados."""
    intervalos_dias = [15, 10, 5, 3, 1]
    ahora = datetime.now()
    enviados = 0

    # Actividades futuras
    actividades = db.query(ActividadCurso).filter(ActividadCurso.fecha_limite > ahora).all()

    for act in actividades:
        dias_restantes = (act.fecha_limite - ahora).days
        if dias_restantes in intervalos_dias:
            # Obtener todos los postulantes del curso
            asignaciones = db.query(AsignacionCurso).filter(
                AsignacionCurso.curso_id == act.curso_id
            ).all()

            for asig in asignaciones:
                postulante = db.query(Usuario).join(Inscripcion).filter(
                    Inscripcion.id == asig.inscripcion_id
                ).first()

                if postulante:
                    # Verificar si ya se envió el recordatorio para esta actividad, postulante y días restantes
                    evento_clave = f"RECORDATORIO_VENCIMIENTO_{act.id}_{dias_restantes}D"
                    ya_enviado = db.query(NotificacionCola).filter(
                        NotificacionCola.destinatario_id == postulante.id,
                        NotificacionCola.tipo_evento == evento_clave
                    ).first()

                    if not ya_enviado:
                        asunto = f"UIDE: La actividad '{act.titulo}' vence en {dias_restantes} días"
                        html = f"""
                        <div style="font-family: sans-serif; color: #252533; max-width: 600px; border: 1px solid #E6E9F2; border-radius: 16px; padding: 24px; background: #FFFFFF;">
                            <h2 style="color: #1E3A8A;">Recordatorio Académico UIDE</h2>
                            <p>Estimado(a) <strong>{postulante.nombre_completo}</strong>,</p>
                            <p>Le recordamos que la actividad <strong>{act.titulo}</strong> vence en <strong>{dias_restantes} días</strong>.</p>
                            <p><strong>Fecha límite:</strong> {act.fecha_limite.strftime('%Y-%m-%d %H:%M')}</p>
                            <p>Por favor ingrese a la plataforma para cargar su evidencia antes del cierre.</p>
                            <hr style="border: none; border-top: 1px solid #E6E9F2;">
                            <small style="color: #747789;">Sistema de Gestión de Cursos Preparatorios - UIDE</small>
                        </div>
                        """
                        send_or_queue_notification(
                            db=db,
                            destinatario=postulante,
                            tipo_evento=evento_clave,
                            asunto=asunto,
                            cuerpo_html=html
                        )
                        enviados += 1

    return {"recordatorios_enviados": enviados}
