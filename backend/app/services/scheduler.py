from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.core.database import SessionLocal
from app.models.entities import RegistroEjecucionJob
from app.services.risk_engine import evaluate_all_active_applicants
from app.services.notification_service import check_and_send_deadline_reminders
from app.services.tareas_diarias import cerrar_inscripciones_vencidas, enviar_resumenes_diarios

scheduler = BackgroundScheduler()


def _ejecutar(nombre: str, funcion):
    """Corre una tarea y deja constancia en registros_ejecucion_job."""
    db = SessionLocal()
    job_reg = RegistroEjecucionJob(nombre_job=nombre, fecha_inicio=datetime.now(), estado="EJECUTANDO")
    db.add(job_reg)
    db.commit()
    try:
        resultado = funcion(db)
        job_reg.estado = "COMPLETADO"
        job_reg.resultado_json = str(resultado)
    except Exception as e:
        db.rollback()
        job_reg.estado = "FALLIDO"
        job_reg.error_detalle = str(e)
    finally:
        job_reg.fecha_fin = datetime.now()
        db.commit()
        db.close()


def job_evaluar_riesgos_e_inactividad():
    _ejecutar("EVALUAR_RIESGOS_E_INACTIVIDAD", evaluate_all_active_applicants)


def job_recordatorios_vencimiento():
    _ejecutar("RECORDATORIOS_VENCIMIENTO_DIARIO", check_and_send_deadline_reminders)


def job_cerrar_inscripciones():
    _ejecutar("CERRAR_INSCRIPCIONES_VENCIDAS", cerrar_inscripciones_vencidas)


def job_resumenes_diarios():
    _ejecutar("RESUMEN_DIARIO_TUTORES_COORDINADORES", enviar_resumenes_diarios)


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(job_evaluar_riesgos_e_inactividad, trigger=IntervalTrigger(minutes=30),
                          id="job_riesgos", name="Evaluación de riesgos", replace_existing=True)
        scheduler.add_job(job_recordatorios_vencimiento, trigger=IntervalTrigger(hours=1),
                          id="job_recordatorios", name="Recordatorios de vencimiento", replace_existing=True)
        scheduler.add_job(job_cerrar_inscripciones, trigger=IntervalTrigger(hours=1),
                          id="job_convocatorias", name="Cierre automático de inscripciones", replace_existing=True)
        scheduler.add_job(job_resumenes_diarios, trigger=CronTrigger(hour=7, minute=0),
                          id="job_resumenes", name="Resumen diario a tutores y coordinadores", replace_existing=True)
        scheduler.start()
        # Al arrancar, ponerse al día con las convocatorias que vencieron mientras el servidor estaba apagado
        job_cerrar_inscripciones()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
