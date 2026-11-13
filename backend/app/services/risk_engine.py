"""
Motor de riesgo académico.

En cada evaluación arma la lista de condiciones que hoy se cumplen para el postulante,
abre una alerta por cada condición nueva y cierra sola la alerta cuya condición ya no
se cumple. Así la lista de alertas siempre refleja la situación actual.
"""
from datetime import datetime
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from app.models.entities import (
    Inscripcion, AlertaRiesgo, SeguimientoPostulante,
    EntregaEvidencia, ActividadCurso
)
from app.core.config import settings
from app.services.progress_service import (
    calcular_avance, asignaciones_del_postulante, inscripcion_cerrada, cerrar_alertas_inscripcion
)

# Estados de entrega que siguen siendo responsabilidad del postulante.
# ENTREGADO (subida y esperando calificación) no cuenta: la demora es del tutor.
ESTADOS_ENTREGA_PENDIENTE = ["PENDIENTE", "REQUIERE_CORRECCION", "RECHAZADO"]

ESTADOS_INSCRIPCION_EVALUABLES = ["REGISTRADO", "DOCUMENTACION_PENDIENTE", "EN_CURSO"]

NIVEL_ORDEN = {"BAJO": 0, "MEDIO": 1, "ALTO": 2}


def _subir_nivel(actual: str, nuevo: str) -> str:
    return nuevo if NIVEL_ORDEN[nuevo] > NIVEL_ORDEN[actual] else actual


def _clave_alerta(tipo: str, motivo: str) -> Tuple[str, str]:
    """Las alertas SIN_EVIDENCIA son una por actividad; las demás, una por tipo."""
    if tipo == "SIN_EVIDENCIA":
        return tipo, motivo
    return tipo, ""


def avance_esperado(inscripcion: Inscripcion, ahora: datetime) -> float:
    """Porcentaje del preparatorio que ya transcurrió (0 antes de empezar, 100 al terminar)."""
    conv = inscripcion.convocatoria
    inicio, fin = conv.fecha_inicio_preparatorio, conv.fecha_fin_preparatorio
    if not inicio or not fin or fin <= inicio:
        return 0.0
    hoy = ahora.date()
    if hoy <= inicio:
        return 0.0
    if hoy >= fin:
        return 100.0
    return round((hoy - inicio).days / (fin - inicio).days * 100.0, 1)


def _condiciones_activas(db: Session, inscripcion: Inscripcion, ahora: datetime) -> Tuple[Dict, list]:
    """
    Devuelve (condiciones, motivos).
    condiciones: {clave: (tipo, nivel, motivo)} para las que generan alerta.
    motivos: textos para el resumen del riesgo (incluye avisos que no abren alerta).
    """
    condiciones = {}
    motivos = []

    def agregar(tipo, nivel, motivo):
        condiciones[_clave_alerta(tipo, motivo)] = (tipo, nivel, motivo)
        motivos.append(motivo)

    # 1. Inactividad académica
    dias_limite = settings.DIAS_INACTIVIDAD_RIESGO
    fecha_referencia = inscripcion.fecha_ultimo_avance or inscripcion.fecha_inscripcion
    dias_inactivo = (ahora - fecha_referencia).days
    if dias_inactivo >= dias_limite:
        agregar("INACTIVIDAD", "ALTO",
                f"Inactividad prolongada de {dias_inactivo} días (umbral institucional: {dias_limite} días).")

    # 2. Contactos consecutivos sin respuesta
    intentos_limite = settings.INTENTOS_SIN_RESPUESTA_ALERTA
    ultimos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id
    ).order_by(SeguimientoPostulante.fecha_contacto.desc()).limit(intentos_limite).all()
    if len(ultimos) >= intentos_limite and all(not s.hubo_respuesta for s in ultimos):
        agregar("CONTACTO_SIN_RESPUESTA", "ALTO",
                f"Acumulación de {intentos_limite} intentos de contacto consecutivos del tutor sin respuesta del postulante.")

    # 3. Actividades vencidas sin evidencia (alerta) o próximas a vencer (solo aviso)
    for asig in asignaciones_del_postulante(db, inscripcion):
        actividades = db.query(ActividadCurso).filter(
            ActividadCurso.curso_id == asig.curso_id,
            ActividadCurso.estado == "ACTIVO"
        ).all()
        for act in actividades:
            entrega = db.query(EntregaEvidencia).filter(
                EntregaEvidencia.asignacion_curso_id == asig.id,
                EntregaEvidencia.actividad_id == act.id
            ).first()
            if entrega and entrega.estado_entrega not in ESTADOS_ENTREGA_PENDIENTE:
                continue
            if ahora > act.fecha_limite:
                agregar("SIN_EVIDENCIA", "ALTO",
                        f"Actividad '{act.titulo}' ({asig.curso.codigo}) vencida sin evidencia aprobada.")
            elif (act.fecha_limite - ahora).days <= 5:
                motivos.append(f"Actividad '{act.titulo}' próxima a vencer en {(act.fecha_limite - ahora).days} días.")

    # 4. Bajo avance frente a lo esperado según el calendario del preparatorio
    esperado = avance_esperado(inscripcion, ahora)
    avance = calcular_avance(db, inscripcion)
    real = avance["porcentaje"]
    margen = settings.MARGEN_BAJO_AVANCE
    if avance["total_actividades"] > 0 and esperado - real >= margen:
        agregar("BAJO_AVANCE", "MEDIO",
                f"Bajo avance: {real}% real frente a {esperado}% esperado a la fecha (margen permitido: {margen} puntos).")

    return condiciones, motivos


def evaluate_applicant_risk(db: Session, inscripcion_id: int, ahora: datetime = None) -> dict:
    inscripcion = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        return {"error": "Inscripcion no encontrada"}

    ahora = ahora or datetime.now()

    # Un proceso terminado ya no tiene riesgo que vigilar
    if inscripcion_cerrada(inscripcion):
        cerrar_alertas_inscripcion(db, inscripcion, f"Cerrada automáticamente: proceso {inscripcion.estado_proceso}.", ahora)
        db.commit()
        return {
            "inscripcion_id": inscripcion.id,
            "nivel_riesgo": inscripcion.nivel_riesgo,
            "motivo_riesgo": inscripcion.motivo_riesgo,
            "alertas_activas_count": 0
        }

    condiciones, motivos = _condiciones_activas(db, inscripcion, ahora)

    nivel = "BAJO"
    for _tipo, nivel_cond, _motivo in condiciones.values():
        nivel = _subir_nivel(nivel, nivel_cond)
    if nivel == "BAJO" and len(motivos) > len(condiciones):
        nivel = "MEDIO"  # Tiene actividades por vencer en 5 días o menos

    # Abrir alertas nuevas y cerrar las que ya no aplican
    abiertas = db.query(AlertaRiesgo).filter(
        AlertaRiesgo.inscripcion_id == inscripcion.id,
        AlertaRiesgo.resuelta == False  # noqa: E712
    ).all()
    claves_abiertas = set()
    for alerta in abiertas:
        clave = _clave_alerta(alerta.tipo_alerta, alerta.motivo_detallado)
        if clave in condiciones and clave not in claves_abiertas:
            claves_abiertas.add(clave)
        elif alerta.tipo_alerta in ("INACTIVIDAD", "CONTACTO_SIN_RESPUESTA", "SIN_EVIDENCIA", "BAJO_AVANCE"):
            # Solo se cierran solas las alertas que crea el motor
            alerta.resuelta = True
            alerta.fecha_resolucion = ahora
            alerta.accion_tomada = "Resuelta automáticamente: la condición que la originó ya no se cumple."

    for clave, (tipo, nivel_cond, motivo) in condiciones.items():
        if clave not in claves_abiertas:
            db.add(AlertaRiesgo(
                inscripcion_id=inscripcion.id,
                tipo_alerta=tipo,
                nivel_riesgo=nivel_cond,
                motivo_detallado=motivo,
                fecha_deteccion=ahora
            ))

    inscripcion.nivel_riesgo = nivel
    inscripcion.motivo_riesgo = " | ".join(motivos) if motivos else "Cumplimiento satisfactorio del cronograma académico."
    inscripcion.actualizado_en = ahora

    db.commit()
    db.refresh(inscripcion)

    return {
        "inscripcion_id": inscripcion.id,
        "nivel_riesgo": inscripcion.nivel_riesgo,
        "motivo_riesgo": inscripcion.motivo_riesgo,
        "alertas_activas_count": len(condiciones)
    }


def evaluate_all_active_applicants(db: Session) -> dict:
    # Primero se cierran las alertas que quedaron abiertas en procesos ya terminados
    cerradas = db.query(Inscripcion).join(AlertaRiesgo).filter(
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_EVALUABLES),
        AlertaRiesgo.resuelta == False  # noqa: E712
    ).distinct().all()
    for insc in cerradas:
        cerrar_alertas_inscripcion(db, insc, f"Cerrada automáticamente: proceso {insc.estado_proceso}.")
    db.commit()

    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.estado_proceso.in_(ESTADOS_INSCRIPCION_EVALUABLES)
    ).all()

    resumen = {"evaluados": len(inscripciones), "alto": 0, "medio": 0, "bajo": 0}
    for insc in inscripciones:
        nivel = evaluate_applicant_risk(db, insc.id).get("nivel_riesgo", "BAJO")
        if nivel == "ALTO":
            resumen["alto"] += 1
        elif nivel == "MEDIO":
            resumen["medio"] += 1
        else:
            resumen["bajo"] += 1

    return resumen
