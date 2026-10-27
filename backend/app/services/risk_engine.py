from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.entities import (
    Inscripcion, AlertaRiesgo, SeguimientoPostulante, 
    AsignacionCurso, EntregaEvidencia, ActividadCurso, RegistroAuditoria
)
from app.core.config import settings

def evaluate_applicant_risk(db: Session, inscripcion_id: int, ahora: datetime = None) -> dict:
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        return {"error": "Inscripcion no encontrada"}
    
    ahora = ahora or datetime.now()
    dias_inactividad_limite = settings.DIAS_INACTIVIDAD_RIESGO
    intentos_sin_respuesta_limite = settings.INTENTOS_SIN_RESPUESTA_ALERTA
    
    motivos = []
    nuevo_nivel = "BAJO"

    # 1. Evaluar inactividad académica
    fecha_referencia = inscripcion.fecha_ultimo_avance or inscripcion.fecha_inscripcion
    dias_inactivo = (ahora - fecha_referencia).days
    if dias_inactivo >= dias_inactividad_limite:
        motivo_inact = f"Inactividad prolongada de {dias_inactivo} días (umbral institucional: {dias_inactividad_limite} días)."
        motivos.append(motivo_inact)
        nuevo_nivel = "ALTO"
        
        # Registrar alerta si no existe activa
        alerta_existente = db.query(AlertaRiesgo).filter(
            AlertaRiesgo.inscripcion_id == inscripcion.id,
            AlertaRiesgo.tipo_alerta == "INACTIVIDAD",
            AlertaRiesgo.resuelta == False
        ).first()
        if not alerta_existente:
            db.add(AlertaRiesgo(
                inscripcion_id=inscripcion.id,
                tipo_alerta="INACTIVIDAD",
                nivel_riesgo="ALTO",
                motivo_detallado=motivo_inact
            ))

    # 2. Evaluar contactos consecutivos sin respuesta
    ultimos_seguimientos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id
    ).order_by(SeguimientoPostulante.fecha_contacto.desc()).limit(intentos_sin_respuesta_limite).all()

    if len(ultimos_seguimientos) >= intentos_sin_respuesta_limite:
        sin_respuesta = all(not s.hubo_respuesta for s in ultimos_seguimientos)
        if sin_respuesta:
            motivo_resp = f"Acumulación de {intentos_sin_respuesta_limite} intentos de contacto consecutivos del tutor sin respuesta del postulante."
            motivos.append(motivo_resp)
            nuevo_nivel = "ALTO"

            alerta_resp = db.query(AlertaRiesgo).filter(
                AlertaRiesgo.inscripcion_id == inscripcion.id,
                AlertaRiesgo.tipo_alerta == "CONTACTO_SIN_RESPUESTA",
                AlertaRiesgo.resuelta == False
            ).first()
            if not alerta_resp:
                db.add(AlertaRiesgo(
                    inscripcion_id=inscripcion.id,
                    tipo_alerta="CONTACTO_SIN_RESPUESTA",
                    nivel_riesgo="ALTO",
                    motivo_detallado=motivo_resp
                ))

    # 3. Evaluar entregas vencidas o próximas a vencer
    asignaciones = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == inscripcion.id).all()
    for asig in asignaciones:
        actividades = db.query(ActividadCurso).filter(ActividadCurso.curso_id == asig.curso_id).all()
        for act in actividades:
            entrega = db.query(EntregaEvidencia).filter(
                EntregaEvidencia.asignacion_curso_id == asig.id,
                EntregaEvidencia.actividad_id == act.id
            ).first()

            if not entrega or entrega.estado_entrega in ["PENDIENTE", "REQUIERE_CORRECCION"]:
                if ahora > act.fecha_limite:
                    motivos.append(f"Actividad '{act.titulo}' se encuentra vencida sin evidencia aprobada.")
                    if nuevo_nivel != "ALTO":
                        nuevo_nivel = "MEDIO"
                elif (act.fecha_limite - ahora).days <= 5:
                    motivos.append(f"Actividad '{act.titulo}' próxima a vencer en {(act.fecha_limite - ahora).days} días.")
                    if nuevo_nivel == "BAJO":
                        nuevo_nivel = "MEDIO"

    # Actualizar estado de la inscripción
    inscripcion.nivel_riesgo = nuevo_nivel
    inscripcion.motivo_riesgo = " | ".join(motivos) if motivos else "Cumplimiento satisfactorio del cronograma académico."
    inscripcion.actualizado_en = ahora
    
    db.commit()
    db.refresh(inscripcion)

    return {
        "inscripcion_id": inscripcion.id,
        "nivel_riesgo": inscripcion.nivel_riesgo,
        "motivo_riesgo": inscripcion.motivo_riesgo,
        "alertas_activas_count": len(motivos)
    }

def evaluate_all_active_applicants(db: Session) -> dict:
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.estado_proceso.in_(["EN_CURSO", "DOCUMENTACION_PENDIENTE", "REGISTRADO"])
    ).all()
    
    resumen = {"evaluados": len(inscripciones), "alto": 0, "medio": 0, "bajo": 0}
    for insc in inscripciones:
        resultado = evaluate_applicant_risk(db, insc.id)
        nivel = resultado.get("nivel_riesgo", "BAJO")
        if nivel == "ALTO":
            resumen["alto"] += 1
        elif nivel == "MEDIO":
            resumen["medio"] += 1
        else:
            resumen["bajo"] += 1
            
    return resumen
