"""
Servicio central de cursos, avance y cierre del proceso del postulante.

Todo cálculo de "qué cursos tiene un postulante", "cuánto ha avanzado" y
"si ya aprobó" pasa por aquí, para que el dashboard, la lista de postulantes,
los reportes y las evidencias muestren siempre las mismas cifras.
"""
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    Inscripcion, Convocatoria, CursoPreparatorio, ActividadCurso,
    AsignacionCurso, EntregaEvidencia, VersionEvidencia, EvaluacionEvidencia, RegistroAuditoria,
    RequisitoConvocatoria
)

# Estados en los que la inscripción ya terminó y no admite más cambios académicos
ESTADOS_INSCRIPCION_CERRADA = ["APROBADO", "NO_APROBADO", "RETIRADO"]


# Qué permite cada estado de la convocatoria (PLANIFICADA → ABIERTA → EN_CURSO → CERRADA → FINALIZADA)
CONV_PERMITE_INSCRIPCION = ["ABIERTA"]
CONV_PERMITE_CURSOS = ["PLANIFICADA", "ABIERTA", "EN_CURSO"]
CONV_PERMITE_ENTREGAS = ["ABIERTA", "EN_CURSO"]
CONV_PERMITE_CALIFICAR = ["ABIERTA", "EN_CURSO", "CERRADA"]

MENSAJE_ESTADO_CONVOCATORIA = {
    "PLANIFICADA": "La convocatoria aún está planificada.",
    "CERRADA": "La convocatoria está cerrada: ya no se reciben evidencias, solo se terminan de calificar.",
    "FINALIZADA": "La convocatoria está finalizada.",
}


def inscripcion_cerrada(inscripcion: Inscripcion) -> bool:
    return inscripcion.estado_proceso in ESTADOS_INSCRIPCION_CERRADA


def mensaje_convocatoria(convocatoria: Convocatoria) -> str:
    return MENSAJE_ESTADO_CONVOCATORIA.get(convocatoria.estado, f"La convocatoria está en estado {convocatoria.estado}.")


def tiene_requisitos_obligatorios(db: Session, convocatoria_id: int) -> bool:
    return db.query(RequisitoConvocatoria).filter(
        RequisitoConvocatoria.convocatoria_id == convocatoria_id,
        RequisitoConvocatoria.es_obligatorio == True  # noqa: E712
    ).count() > 0


def estado_inicial_inscripcion(db: Session, convocatoria_id: int) -> str:
    """Si la convocatoria pide documentos obligatorios, el postulante empieza con la documentación pendiente."""
    return "DOCUMENTACION_PENDIENTE" if tiene_requisitos_obligatorios(db, convocatoria_id) else "EN_CURSO"


def asignaciones_del_postulante(db: Session, inscripcion: Inscripcion) -> List[AsignacionCurso]:
    """Todos los cursos asignados a la inscripción, en orden de asignación."""
    return db.query(AsignacionCurso).filter(
        AsignacionCurso.inscripcion_id == inscripcion.id
    ).order_by(AsignacionCurso.id.asc()).all()


def asignacion_para_actividad(db: Session, inscripcion: Inscripcion, actividad: ActividadCurso) -> Optional[AsignacionCurso]:
    """La asignación del curso al que pertenece la actividad, o None si el postulante no tiene ese curso."""
    return db.query(AsignacionCurso).filter(
        AsignacionCurso.inscripcion_id == inscripcion.id,
        AsignacionCurso.curso_id == actividad.curso_id
    ).first()


def _actividades_activas(db: Session, curso_id: int) -> List[ActividadCurso]:
    return db.query(ActividadCurso).filter(
        ActividadCurso.curso_id == curso_id,
        ActividadCurso.estado == "ACTIVO"
    ).all()


def calcular_avance(db: Session, inscripcion: Inscripcion) -> dict:
    """
    Avance del postulante sumando TODOS sus cursos.
    Porcentaje = actividades aprobadas / actividades activas de todos sus cursos.
    """
    cursos = []
    total_global = 0
    aprobadas_global = 0

    for asig in asignaciones_del_postulante(db, inscripcion):
        actividades = _actividades_activas(db, asig.curso_id)
        ids_actividades = [a.id for a in actividades]
        aprobadas = 0
        if ids_actividades:
            aprobadas = db.query(EntregaEvidencia).filter(
                EntregaEvidencia.asignacion_curso_id == asig.id,
                EntregaEvidencia.actividad_id.in_(ids_actividades),
                EntregaEvidencia.estado_entrega == "APROBADO"
            ).count()

        total_global += len(actividades)
        aprobadas_global += aprobadas
        cursos.append({
            "asignacion_id": asig.id,
            "curso_id": asig.curso_id,
            "codigo": asig.curso.codigo,
            "nombre": asig.curso.nombre,
            "nota_minima": float(asig.curso.nota_minima),
            "nota_final": float(asig.nota_final) if asig.nota_final is not None else None,
            "estado_aprobacion": asig.estado_aprobacion,
            "total_actividades": len(actividades),
            "actividades_aprobadas": aprobadas,
            "porcentaje": round(aprobadas / len(actividades) * 100.0, 1) if actividades else 0.0,
        })

    return {
        "inscripcion_id": inscripcion.id,
        "estado_proceso": inscripcion.estado_proceso,
        "total_actividades": total_global,
        "actividades_aprobadas": aprobadas_global,
        "actividades_pendientes": max(0, total_global - aprobadas_global),
        "porcentaje": round(aprobadas_global / total_global * 100.0, 1) if total_global else 0.0,
        "convocatoria_estado": inscripcion.convocatoria.estado,
        "permite_entregas": inscripcion.convocatoria.estado in CONV_PERMITE_ENTREGAS and not inscripcion_cerrada(inscripcion),
        "permite_calificar": inscripcion.convocatoria.estado in CONV_PERMITE_CALIFICAR and not inscripcion_cerrada(inscripcion),
        "documentacion_pendiente": inscripcion.estado_proceso == "DOCUMENTACION_PENDIENTE",
        "aviso_convocatoria": None if inscripcion.convocatoria.estado in CONV_PERMITE_ENTREGAS else mensaje_convocatoria(inscripcion.convocatoria),
        "cursos": cursos,
    }


def asignar_curso_a_inscritos(db: Session, curso: CursoPreparatorio) -> int:
    """Asigna un curso nuevo a todos los inscritos vigentes de su convocatoria que aún no lo tienen."""
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.convocatoria_id == curso.convocatoria_id,
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()

    asignados = 0
    ahora = datetime.now()
    for insc in inscripciones:
        ya_asignado = db.query(AsignacionCurso).filter(
            AsignacionCurso.inscripcion_id == insc.id,
            AsignacionCurso.curso_id == curso.id
        ).first()
        if not ya_asignado:
            db.add(AsignacionCurso(
                inscripcion_id=insc.id,
                curso_id=curso.id,
                estado="EN_CURSO",
                estado_aprobacion="PENDIENTE",
                fecha_asignacion=ahora
            ))
            asignados += 1
    return asignados


def recalcular_curso(db: Session, asig: AsignacionCurso) -> None:
    """
    Nota del curso = suma de la última calificación registrada de cada actividad.
    El curso se aprueba cuando la nota alcanza la mínima y todas las actividades
    obligatorias tienen su evidencia aprobada.
    """
    nota = 0.0
    entregas = db.query(EntregaEvidencia).filter(EntregaEvidencia.asignacion_curso_id == asig.id).all()
    for ent in entregas:
        ultima_evaluacion = db.query(EvaluacionEvidencia).join(VersionEvidencia).filter(
            VersionEvidencia.entrega_id == ent.id
        ).order_by(VersionEvidencia.numero_version.desc()).first()
        if ultima_evaluacion:
            nota += float(ultima_evaluacion.puntaje_obtenido)

    obligatorias = [a.id for a in _actividades_activas(db, asig.curso_id) if a.es_obligatorio]
    aprobadas = {e.actividad_id for e in entregas if e.estado_entrega == "APROBADO"}
    obligatorias_completas = all(a in aprobadas for a in obligatorias)

    asig.nota_final = nota
    if nota >= float(asig.curso.nota_minima) and obligatorias_completas:
        asig.estado_aprobacion = "APROBADO"
        asig.estado = "COMPLETADO"
    else:
        asig.estado_aprobacion = "PENDIENTE"
        asig.estado = "EN_CURSO"


def actualizar_estado_inscripcion(db: Session, inscripcion: Inscripcion, usuario_id: Optional[int] = None) -> bool:
    """
    La inscripción pasa a APROBADO cuando todos sus cursos están aprobados y su
    documentación está completa. Si una recalificación hace que un curso deje de estar aprobado, vuelve a EN_CURSO.
    Devuelve True si el postulante acaba de aprobar.
    """
    if inscripcion.estado_proceso in ["NO_APROBADO", "RETIRADO"]:
        return False

    asignaciones = asignaciones_del_postulante(db, inscripcion)
    for asig in asignaciones:
        recalcular_curso(db, asig)
    todos_aprobados = bool(asignaciones) and all(a.estado_aprobacion == "APROBADO" for a in asignaciones)
    anterior = inscripcion.estado_proceso

    if anterior == "DOCUMENTACION_PENDIENTE":
        # Puede avanzar en los cursos, pero no aprobar sin la documentación completa
        return False
    if todos_aprobados and anterior != "APROBADO":
        inscripcion.estado_proceso = "APROBADO"
    elif not todos_aprobados and anterior == "APROBADO":
        inscripcion.estado_proceso = "EN_CURSO"
    else:
        return False

    inscripcion.actualizado_en = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=usuario_id,
        accion="CAMBIO_ESTADO_INSCRIPCION",
        entidad="INSCRIPCION",
        entidad_id=str(inscripcion.id),
        datos_anteriores_json=json.dumps({"estado_proceso": anterior}),
        datos_nuevos_json=json.dumps({"estado_proceso": inscripcion.estado_proceso})
    ))
    return inscripcion.estado_proceso == "APROBADO"


def marcar_documentacion_completa(db: Session, inscripcion: Inscripcion, usuario_id: int) -> bool:
    """
    El coordinador confirma que el postulante entregó sus documentos.
    La inscripción pasa a EN_CURSO y, si ya tenía todo aprobado, aprueba en ese momento.
    Devuelve True si el postulante quedó APROBADO.
    """
    inscripcion.estado_proceso = "EN_CURSO"
    inscripcion.actualizado_en = datetime.now()
    db.add(RegistroAuditoria(
        usuario_id=usuario_id,
        accion="DOCUMENTACION_COMPLETA",
        entidad="INSCRIPCION",
        entidad_id=str(inscripcion.id),
        datos_anteriores_json=json.dumps({"estado_proceso": "DOCUMENTACION_PENDIENTE"}),
        datos_nuevos_json=json.dumps({"estado_proceso": "EN_CURSO"})
    ))
    return actualizar_estado_inscripcion(db, inscripcion, usuario_id)


def cerrar_convocatoria(db: Session, convocatoria: Convocatoria, usuario_id: int) -> dict:
    """Al finalizar la convocatoria, quien no aprobó todos sus cursos queda NO_APROBADO."""
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.convocatoria_id == convocatoria.id,
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()

    no_aprobados = 0
    for insc in inscripciones:
        # Último recálculo por si algún curso quedó aprobado sin una calificación reciente
        if actualizar_estado_inscripcion(db, insc, usuario_id):
            continue
        for asig in asignaciones_del_postulante(db, insc):
            if asig.estado_aprobacion != "APROBADO":
                asig.estado_aprobacion = "REPROBADO"
                asig.estado = "FINALIZADO"
        anterior = insc.estado_proceso
        insc.estado_proceso = "NO_APROBADO"
        insc.actualizado_en = datetime.now()
        db.add(RegistroAuditoria(
            usuario_id=usuario_id,
            accion="CAMBIO_ESTADO_INSCRIPCION",
            entidad="INSCRIPCION",
            entidad_id=str(insc.id),
            datos_anteriores_json=json.dumps({"estado_proceso": anterior}),
            datos_nuevos_json=json.dumps({"estado_proceso": "NO_APROBADO", "motivo": "Convocatoria finalizada"})
        ))
        no_aprobados += 1

    return {"no_aprobados": no_aprobados}
