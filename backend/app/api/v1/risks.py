from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.entities import Usuario, AlertaRiesgo, Inscripcion, RegistroAuditoria
from app.schemas.pydantic_models import RiskAlertOut
from app.services.risk_engine import evaluate_all_active_applicants

router = APIRouter(prefix="/riesgos", tags=["Riesgos y Alertas"])

@router.get("/alertas", response_model=List[RiskAlertOut])
def list_risk_alerts(current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")), db: Session = Depends(get_db)):
    query = db.query(AlertaRiesgo).join(Inscripcion).filter(AlertaRiesgo.resuelta == False)
    
    # Restricción por rol
    if current_user.rol.codigo == "TUTOR":
        from app.models.entities import AsignacionTutor
        query = query.join(AsignacionTutor, AsignacionTutor.inscripcion_id == Inscripcion.id).filter(
            AsignacionTutor.tutor_id == current_user.id,
            AsignacionTutor.estado == 'ACTIVO'
        )

    alertas = query.order_by(AlertaRiesgo.fecha_deteccion.desc()).all()
    resultado = []
    for a in alertas:
        resultado.append(RiskAlertOut(
            id=a.id,
            inscripcion_id=a.inscripcion_id,
            postulante_nombre=a.inscripcion.postulante.nombre_completo,
            tipo_alerta=a.tipo_alerta,
            nivel_riesgo=a.nivel_riesgo,
            motivo_detallado=a.motivo_detallado,
            fecha_deteccion=a.fecha_deteccion,
            resuelta=a.resuelta,
            fecha_resolucion=a.fecha_resolucion
        ))
    return resultado

@router.post("/evaluar")
def trigger_risk_evaluation(
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    resultado = evaluate_all_active_applicants(db)
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="EVALUAR_RIESGOS_MANUAL",
        entidad="REGLAS_RIESGO",
        datos_nuevos_json=str(resultado)
    ))
    db.commit()
    return {"mensaje": "Evaluación de riesgos ejecutada exitosamente.", "resumen": resultado}

@router.post("/alertas/{alerta_id}/resolver")
def resolve_risk_alert(
    alerta_id: int,
    accion_tomada: str = "Resuelto mediante acción de tutoría documentada",
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    alerta = db.query(AlertaRiesgo).filter(AlertaRiesgo.id == alerta_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    alerta.resuelta = True
    alerta.fecha_resolucion = datetime.now()
    alerta.resuelta_por = current_user.id
    alerta.accion_tomada = accion_tomada
    db.commit()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="RESOLVER_ALERTA_RIESGO",
        entidad="ALERTA_RIESGO",
        entidad_id=str(alerta.id)
    ))
    db.commit()
    return {"mensaje": "Alerta marcada como resuelta."}
