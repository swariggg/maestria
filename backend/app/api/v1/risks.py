import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access, inscripciones_visibles
from pydantic import BaseModel, Field
from app.models.entities import Usuario, AlertaRiesgo, Inscripcion, RegistroAuditoria, CoordinadorPrograma
from app.schemas.pydantic_models import RiskAlertOut
from app.services.risk_engine import evaluate_all_active_applicants, evaluate_applicant_risk
from app.services.process_emails import correo_alerta_derivada


class Derivacion(BaseModel):
    destinatario_id: int
    nota: str = Field(min_length=5, max_length=500)


def _alerta_out(a: AlertaRiesgo) -> RiskAlertOut:
    return RiskAlertOut(
        id=a.id,
        inscripcion_id=a.inscripcion_id,
        postulante_nombre=a.inscripcion.postulante.nombre_completo,
        programa_codigo=a.inscripcion.convocatoria.programa.codigo,
        tipo_alerta=a.tipo_alerta,
        nivel_riesgo=a.nivel_riesgo,
        motivo_detallado=a.motivo_detallado,
        fecha_deteccion=a.fecha_deteccion,
        resuelta=a.resuelta,
        fecha_resolucion=a.fecha_resolucion,
        accion_tomada=a.accion_tomada,
        resuelta_por_nombre=a.usuario_resolutor.nombre_completo if a.usuario_resolutor else None,
        derivada_a_nombre=a.usuario_derivado.nombre_completo if a.usuario_derivado else None,
        nota_derivacion=a.nota_derivacion,
    )


def _alerta_accesible(db: Session, user: Usuario, alerta_id: int) -> AlertaRiesgo:
    alerta = db.query(AlertaRiesgo).filter(AlertaRiesgo.id == alerta_id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")
    if not verify_applicant_access(user, alerta.inscripcion.postulante_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre el postulante de esta alerta.")
    return alerta


def _coordinadores_programa(db: Session, programa_id: int) -> list:
    filas = db.query(CoordinadorPrograma).filter(
        CoordinadorPrograma.programa_id == programa_id, CoordinadorPrograma.activo == True  # noqa: E712
    ).all()
    return [f.coordinador for f in filas if f.coordinador.estado == "ACTIVO"]

router = APIRouter(prefix="/riesgos", tags=["Riesgos y Alertas"])

@router.get("/alertas", response_model=List[RiskAlertOut])
def list_risk_alerts(
    incluir_resueltas: bool = False,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    # Cada rol ve solo las alertas de los postulantes a su cargo
    ids_visibles = [i.id for i in inscripciones_visibles(current_user, db).all()]
    query = db.query(AlertaRiesgo).filter(AlertaRiesgo.inscripcion_id.in_(ids_visibles))
    if not incluir_resueltas:
        query = query.filter(AlertaRiesgo.resuelta == False)  # noqa: E712

    alertas = query.order_by(AlertaRiesgo.resuelta.asc(), AlertaRiesgo.fecha_deteccion.desc()).limit(300).all()
    return [_alerta_out(a) for a in alertas]


@router.get("/mis-alertas", response_model=List[RiskAlertOut])
def my_alerts(current_user: Usuario = Depends(require_roles("POSTULANTE")), db: Session = Depends(get_db)):
    """Alertas abiertas del postulante, para mostrarlas en su página principal."""
    alertas = db.query(AlertaRiesgo).join(Inscripcion).filter(
        Inscripcion.postulante_id == current_user.id,
        AlertaRiesgo.resuelta == False  # noqa: E712
    ).order_by(AlertaRiesgo.fecha_deteccion.desc()).all()
    return [_alerta_out(a) for a in alertas]


@router.get("/alertas/{alerta_id}/destinatarios")
def alert_recipients(
    alerta_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    """A quién se puede derivar la alerta: los coordinadores del programa del postulante."""
    alerta = _alerta_accesible(db, current_user, alerta_id)
    return [{"id": c.id, "nombre_completo": c.nombre_completo, "email": c.email}
            for c in _coordinadores_programa(db, alerta.inscripcion.convocatoria.programa_id) if c.id != current_user.id]


@router.post("/alertas/{alerta_id}/derivar")
def derive_alert(
    alerta_id: int,
    data: Derivacion,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    alerta = _alerta_accesible(db, current_user, alerta_id)
    if alerta.resuelta:
        raise HTTPException(status_code=400, detail="La alerta ya está resuelta.")
    destinatarios = {c.id: c for c in _coordinadores_programa(db, alerta.inscripcion.convocatoria.programa_id)}
    destino = destinatarios.get(data.destinatario_id)
    if not destino:
        raise HTTPException(status_code=400, detail="Solo se puede derivar a un coordinador del programa del postulante.")
    alerta.derivada_a = destino.id
    alerta.nota_derivacion = data.nota.strip()
    alerta.fecha_derivacion = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=current_user.id, accion="DERIVAR_ALERTA", entidad="ALERTA_RIESGO", entidad_id=str(alerta.id),
        datos_nuevos_json=json.dumps({"derivada_a": destino.id, "nota": alerta.nota_derivacion}, ensure_ascii=False)
    ))
    db.commit()
    db.refresh(alerta)
    correo_alerta_derivada(db, alerta, destino, current_user)
    return {"mensaje": f"Alerta derivada a {destino.nombre_completo}."}

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
    alerta = _alerta_accesible(db, current_user, alerta_id)
    if alerta.resuelta:
        raise HTTPException(status_code=400, detail="La alerta ya está resuelta.")
    if not accion_tomada or len(accion_tomada.strip()) < 5:
        raise HTTPException(status_code=400, detail="Describa la acción tomada para resolver la alerta.")

    alerta.resuelta = True
    alerta.fecha_resolucion = datetime.now()
    alerta.resuelta_por = current_user.id
    alerta.accion_tomada = accion_tomada
    alerta.bloquea_reapertura = True  # no vuelve a aparecer mientras el problema siga igual
    db.commit()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="RESOLVER_ALERTA_RIESGO",
        entidad="ALERTA_RIESGO",
        entidad_id=str(alerta.id),
        datos_nuevos_json=json.dumps({"accion_tomada": accion_tomada}, ensure_ascii=False)
    ))
    db.commit()
    evaluate_applicant_risk(db, alerta.inscripcion_id)  # el nivel de riesgo se actualiza al momento
    return {"mensaje": "Alerta marcada como resuelta."}
