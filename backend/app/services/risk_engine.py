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
    Inscripcion, AlertaRiesgo, SeguimientoPostulante, CompromisoSeguimiento,
    EntregaEvidencia, ActividadCurso
)
from app.services import parametros
from app.services.progress_service import (
    calcular_avance, asignaciones_del_postulante, inscripcion_cerrada, cerrar_alertas_inscripcion
)

# Estados de entrega que siguen siendo responsabilidad del postulante.
# ENTREGADO (subida y esperando calificación) no cuenta: la demora es del tutor.
ESTADOS_ENTREGA_PENDIENTE = ["PENDIENTE", "REQUIERE_CORRECCION", "RECHAZADO"]

ESTADOS_INSCRIPCION_EVALUABLES = ["REGISTRADO", "DOCUMENTACION_PENDIENTE", "EN_CURSO"]

NIVEL_ORDEN = {"BAJO": 0, "MEDIO": 1, "ALTO": 2}

# Tipos que crea y cierra el motor (las demás alertas solo se cierran a mano)
TIPOS_AUTOMATICOS = ("INACTIVIDAD", "CONTACTO_SIN_RESPUESTA", "SIN_EVIDENCIA", "BAJO_AVANCE",
                     "VENCIMIENTO_PROXIMO", "COMPROMISO_VENCIDO")


def _subir_nivel(actual: str, nuevo: str) -> str:
    return nuevo if NIVEL_ORDEN[nuevo] > NIVEL_ORDEN[actual] else actual


def _clave_alerta(tipo: str, motivo: str) -> Tuple[str, str]:
    """Las alertas SIN_EVIDENCIA y COMPROMISO_VENCIDO son una por actividad o compromiso; las demás, una por tipo."""
    if tipo in ("SIN_EVIDENCIA", "COMPROMISO_VENCIDO"):
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
    dias_limite = parametros.get_int(db, "DIAS_INACTIVIDAD_RIESGO")
    fecha_referencia = inscripcion.fecha_ultimo_avance or inscripcion.fecha_inscripcion
    dias_inactivo = (ahora - fecha_referencia).days
    if dias_inactivo >= dias_limite:
        agregar("INACTIVIDAD", "ALTO",
                f"Inactividad prolongada de {dias_inactivo} días (umbral institucional: {dias_limite} días).")

    # 2. Contactos consecutivos sin respuesta
    intentos_limite = parametros.get_int(db, "INTENTOS_SIN_RESPUESTA_ALERTA")
    ultimos = db.query(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id
    ).order_by(SeguimientoPostulante.fecha_contacto.desc()).limit(intentos_limite).all()
    if len(ultimos) >= intentos_limite and all(not s.hubo_respuesta for s in ultimos):
        agregar("CONTACTO_SIN_RESPUESTA", "ALTO",
                f"Acumulación de {intentos_limite} intentos de contacto consecutivos del tutor sin respuesta del postulante.")

    # 3. Actividades vencidas sin evidencia (alerta, riesgo alto) o próximas a vencer (riesgo medio, sin alerta)
    dias_por_vencer = parametros.get_int(db, "DIAS_PROXIMA_A_VENCER")
    por_vencer = []
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
            elif act.fecha_apertura <= ahora and (act.fecha_limite - ahora).days <= dias_por_vencer:
                dias = (act.fecha_limite.date() - ahora.date()).days
                por_vencer.append(act.titulo)
                cuando = "hoy" if dias < 1 else "mañana" if dias == 1 else f"en {dias} días"
                motivos.append(f"Actividad '{act.titulo}' ({asig.curso.codigo}) sin entregar, vence {cuando}.")
    if por_vencer:
        # No abre alerta (avisarían a diario), pero pinta el semáforo en amarillo
        condiciones[("VENCIMIENTO_PROXIMO", "")] = ("VENCIMIENTO_PROXIMO", "MEDIO", None)

    # 4. Bajo avance frente a lo esperado según el calendario del preparatorio
    esperado = avance_esperado(inscripcion, ahora)
    avance = calcular_avance(db, inscripcion)
    real = avance["porcentaje"]
    margen = parametros.get_int(db, "MARGEN_BAJO_AVANCE")
    if avance["total_actividades"] > 0 and esperado - real >= margen:
        agregar("BAJO_AVANCE", "MEDIO",
                f"Bajo avance: {real}% real frente a {esperado}% esperado a la fecha (margen permitido: {margen} puntos).")

    # 5. Compromisos del seguimiento que vencieron sin cumplirse
    vencidos = db.query(CompromisoSeguimiento).join(SeguimientoPostulante).filter(
        SeguimientoPostulante.inscripcion_id == inscripcion.id,
        CompromisoSeguimiento.cumplido == False,  # noqa: E712
        CompromisoSeguimiento.fecha_compromiso < ahora.date()
    ).all()
    for comp in vencidos:
        agregar("COMPROMISO_VENCIDO", "MEDIO",
                f"Compromiso vencido el {comp.fecha_compromiso}: {comp.descripcion}")

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

    # Lo que el tutor resolvió a mano no vuelve a aparecer mientras siga igual;
    # si la condición desaparece, se libera para alertar de nuevo si vuelve a pasar.
    resueltas_a_mano = db.query(AlertaRiesgo).filter(
        AlertaRiesgo.inscripcion_id == inscripcion.id,
        AlertaRiesgo.resuelta == True,  # noqa: E712
        AlertaRiesgo.bloquea_reapertura == True  # noqa: E712
    ).all()
    suprimidas = set()
    for alerta in resueltas_a_mano:
        clave = _clave_alerta(alerta.tipo_alerta, alerta.motivo_detallado)
        if clave in condiciones:
            suprimidas.add(clave)
        else:
            alerta.bloquea_reapertura = False
    for clave in suprimidas:
        motivo_suprimido = condiciones.pop(clave)[2]
        if motivo_suprimido in motivos:
            motivos.remove(motivo_suprimido)

    # Semáforo: ALTO (rojo) inactividad, sin respuesta o vencidas sin entregar;
    # MEDIO (amarillo) entregas por vencer, bajo avance o compromisos vencidos; BAJO (verde) al día
    nivel = "BAJO"
    for _tipo, nivel_cond, _motivo in condiciones.values():
        nivel = _subir_nivel(nivel, nivel_cond)
    # "Por vencer" solo cambia el color; no se guarda como alerta
    condiciones.pop(("VENCIMIENTO_PROXIMO", ""), None)

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
        elif alerta.tipo_alerta in TIPOS_AUTOMATICOS:
            # Solo se cierran solas las alertas que crea el motor
            alerta.resuelta = True
            alerta.fecha_resolucion = ahora
            alerta.accion_tomada = "Resuelta automáticamente: la condición que la originó ya no se cumple."

    nuevas = []
    for clave, (tipo, nivel_cond, motivo) in condiciones.items():
        if clave not in claves_abiertas:
            nuevas.append(motivo)
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

    # El tutor recibe un aviso por cada alerta nueva
    if nuevas:
        from app.services.process_emails import correo_alerta_nueva
        from app.services.tutoria import tutores_de_inscripcion
        for tutor in tutores_de_inscripcion(db, inscripcion):
            correo_alerta_nueva(db, inscripcion, tutor, nuevas)

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
