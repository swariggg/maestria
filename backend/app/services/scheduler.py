from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import SessionLocal
from app.models.entities import RegistroEjecucionJob
from app.services.risk_engine import evaluate_all_active_applicants
from app.services.notification_service import check_and_send_deadline_reminders

scheduler = BackgroundScheduler()

def job_evaluar_riesgos_e_inactividad():
    db = SessionLocal()
    inicio = datetime.now()
    job_reg = RegistroEjecucionJob(
        nombre_job="EVALUAR_RIESGOS_E_INACTIVIDAD",
        fecha_inicio=inicio,
        estado="EJECUTANDO"
    )
    db.add(job_reg)
    db.commit()

    try:
        resultado = evaluate_all_active_applicants(db)
        job_reg.estado = "COMPLETADO"
        job_reg.fecha_fin = datetime.now()
        job_reg.resultado_json = str(resultado)
        db.commit()
    except Exception as e:
        job_reg.estado = "FALLIDO"
        job_reg.fecha_fin = datetime.now()
        job_reg.error_detalle = str(e)
        db.commit()
    finally:
        db.close()

def job_recordatorios_vencimiento():
    db = SessionLocal()
    inicio = datetime.now()
    job_reg = RegistroEjecucionJob(
        nombre_job="RECORDATORIOS_VENCIMIENTO_DIARIO",
        fecha_inicio=inicio,
        estado="EJECUTANDO"
    )
    db.add(job_reg)
    db.commit()

    try:
        resultado = check_and_send_deadline_reminders(db)
        job_reg.estado = "COMPLETADO"
        job_reg.fecha_fin = datetime.now()
        job_reg.resultado_json = str(resultado)
        db.commit()
    except Exception as e:
        job_reg.estado = "FALLIDO"
        job_reg.fecha_fin = datetime.now()
        job_reg.error_detalle = str(e)
        db.commit()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Evaluar riesgos cada 30 minutos
        scheduler.add_job(
            job_evaluar_riesgos_e_inactividad,
            trigger=IntervalTrigger(minutes=30),
            id="job_riesgos",
            name="Evaluación de Riesgos e Inactividad (7d)",
            replace_existing=True
        )
        # Recordatorios cada hora
        scheduler.add_job(
            job_recordatorios_vencimiento,
            trigger=IntervalTrigger(hours=1),
            id="job_recordatorios",
            name="Recordatorios de Vencimiento (15, 10, 5, 3, 1d)",
            replace_existing=True
        )
        scheduler.start()

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
