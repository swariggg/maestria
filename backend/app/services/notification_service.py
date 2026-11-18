import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.entities import (
    NotificacionCola, RegistroIntentoEnvio, ActividadCurso, 
    AsignacionCurso, Inscripcion, Usuario, PlantillaNotificacion,
    CursoPreparatorio, Convocatoria, EntregaEvidencia
)
from app.services.progress_service import CONV_PERMITE_ENTREGAS, ESTADOS_INSCRIPCION_CERRADA
from app.services.parametros import get_lista
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
    # Sin conexión con el correo institucional: el aviso queda solo en la campana de la app
    if not settings.ENVIAR_CORREOS:
        notif.estado = "EN_APP"
        db.commit()
        return True

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
    """Envía recordatorios los días configurados antes del vencimiento (por defecto 15, 10, 5, 3 y 1), sin duplicados."""
    intervalos_dias = get_lista(db, "DIAS_RECORDATORIO")
    ahora = datetime.now()
    enviados = 0

    # Actividades activas que aún no vencen, de convocatorias que reciben entregas
    actividades = db.query(ActividadCurso).join(CursoPreparatorio).join(Convocatoria).filter(
        ActividadCurso.fecha_limite > ahora,
        ActividadCurso.estado == "ACTIVO",
        Convocatoria.estado.in_(CONV_PERMITE_ENTREGAS)
    ).all()

    for act in actividades:
        dias_restantes = (act.fecha_limite - ahora).days
        if dias_restantes in intervalos_dias:
            # Solo inscripciones vigentes del curso
            asignaciones = db.query(AsignacionCurso).join(Inscripcion).filter(
                AsignacionCurso.curso_id == act.curso_id,
                Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
            ).all()

            for asig in asignaciones:
                # No se recuerda a quien ya entregó (salvo que deba corregir o fue rechazado)
                entrega = db.query(EntregaEvidencia).filter(
                    EntregaEvidencia.asignacion_curso_id == asig.id,
                    EntregaEvidencia.actividad_id == act.id
                ).first()
                if entrega and entrega.estado_entrega not in ("PENDIENTE", "REQUIERE_CORRECCION", "RECHAZADO"):
                    continue

                postulante = asig.inscripcion.postulante

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
                            <h2 style="color: #910048;">Recordatorio Académico UIDE</h2>
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
