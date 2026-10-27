import pytest
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.database import SessionLocal
from app.services.risk_engine import evaluate_applicant_risk, evaluate_all_active_applicants
from app.services.notification_service import check_and_send_deadline_reminders
from app.services.report_generator import generate_individual_pdf_report, generate_consolidated_excel_report
from app.models.entities import Inscripcion, Usuario, ActividadCurso, CursoPreparatorio

def test_password_hashing():
    pwd = "TestSecurePassword123!"
    hashed = get_password_hash(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_jwt_token_generation_and_decoding():
    data = {"sub": "42", "rol": "ADMIN", "email": "test@uide.edu.ec"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["rol"] == "ADMIN"
    assert decoded["email"] == "test@uide.edu.ec"

def test_database_connection_and_seeded_admin():
    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.email == "admin@uide.edu.ec").first()
        assert admin is not None
        assert admin.rol.codigo == "ADMIN"
        assert verify_password("Demo2026!", admin.password_hash) is True
    finally:
        db.close()

def test_risk_evaluation_zambrano_high_risk():
    db = SessionLocal()
    try:
        zambrano = db.query(Usuario).filter(Usuario.email == "postulante.zambrano@uide.edu.ec").first()
        assert zambrano is not None
        inscripcion = db.query(Inscripcion).filter(Inscripcion.postulante_id == zambrano.id).first()
        assert inscripcion is not None

        resultado = evaluate_applicant_risk(db, inscripcion.id)
        assert resultado["nivel_riesgo"] == "ALTO"
        assert "Inactividad" in resultado["motivo_riesgo"] or "contactos" in resultado["motivo_riesgo"]
    finally:
        db.close()

def test_risk_evaluation_perez_low_risk():
    db = SessionLocal()
    try:
        perez = db.query(Usuario).filter(Usuario.email == "postulante.perez@uide.edu.ec").first()
        assert perez is not None
        inscripcion = db.query(Inscripcion).filter(Inscripcion.postulante_id == perez.id).first()
        assert inscripcion is not None

        resultado = evaluate_applicant_risk(db, inscripcion.id)
        assert resultado["nivel_riesgo"] == "BAJO"
    finally:
        db.close()

def test_activity_weighting_sum_validation():
    db = SessionLocal()
    try:
        curso = db.query(CursoPreparatorio).filter(CursoPreparatorio.codigo == "CURSO-IA-101").first()
        assert curso is not None
        actividades = db.query(ActividadCurso).filter(ActividadCurso.curso_id == curso.id).all()
        suma_ponderaciones = sum(float(a.ponderacion) for a in actividades)
        # La suma debe ser exactamente 100.0%
        assert suma_ponderaciones == float(curso.ponderacion_total)
    finally:
        db.close()

def test_deadline_reminders_idempotency():
    db = SessionLocal()
    try:
        resultado1 = check_and_send_deadline_reminders(db)
        assert "recordatorios_enviados" in resultado1
        # La segunda ejecución inmediata no debe duplicar recordatorios para la misma fecha
        resultado2 = check_and_send_deadline_reminders(db)
        assert resultado2["recordatorios_enviados"] == 0
    finally:
        db.close()

def test_generate_individual_pdf():
    db = SessionLocal()
    try:
        perez = db.query(Usuario).filter(Usuario.email == "postulante.perez@uide.edu.ec").first()
        inscripcion = db.query(Inscripcion).filter(Inscripcion.postulante_id == perez.id).first()
        pdf_stream = generate_individual_pdf_report(db, inscripcion.id)
        content = pdf_stream.getvalue()
        assert len(content) > 1000
        assert content.startswith(b"%PDF")
    finally:
        db.close()

def test_generate_consolidated_excel():
    db = SessionLocal()
    try:
        excel_stream = generate_consolidated_excel_report(db)
        content = excel_stream.getvalue()
        assert len(content) > 1000
        # Validar firma de archivo ZIP / XLSX
        assert content.startswith(b"PK\x03\x04")
    finally:
        db.close()
