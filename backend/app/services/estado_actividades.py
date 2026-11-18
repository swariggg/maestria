"""
Estado de cada actividad de un postulante: por entregar, por corregir, en revisión, aprobada, vencida...
Lo usan el tablero del postulante y la lista y la ficha del postulante que ve el tutor.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.entities import Inscripcion, EntregaEvidencia, ActividadCurso
from app.services.progress_service import asignaciones_del_postulante

# Estado de la entrega -> estado que se muestra
ESTADO_ENTREGA = {
    "APROBADO": "APROBADA",
    "REQUIERE_CORRECCION": "POR_CORREGIR",
    "RECHAZADO": "RECHAZADA",
    "ENTREGADO": "EN_REVISION",
    "REVISADO": "EN_REVISION",
}
ESTADOS_ABIERTOS = ("PENDIENTE", "POR_CORREGIR")


def estado_actividad(act: ActividadCurso, entrega: Optional[EntregaEvidencia], ahora: datetime) -> str:
    if entrega and entrega.estado_entrega in ESTADO_ENTREGA:
        return ESTADO_ENTREGA[entrega.estado_entrega]
    if ahora < act.fecha_apertura:
        return "PROXIMA"
    if ahora > act.fecha_limite:
        return "VENCIDA"
    return "PENDIENTE"


def actividades_de_inscripcion(db: Session, insc: Inscripcion, ahora: datetime, dias_alerta: int,
                               solo_tutor_id: Optional[int] = None) -> list:
    """
    Actividades activas de todos los cursos de la inscripción, por fecha límite.
    Con solo_tutor_id, solo las de los cursos que dicta ese tutor.
    """
    resultado = []
    for asig in asignaciones_del_postulante(db, insc):
        curso = asig.curso
        if solo_tutor_id is not None and curso.tutor_id != solo_tutor_id:
            continue
        entregas = {e.actividad_id: e for e in db.query(EntregaEvidencia).filter(
            EntregaEvidencia.asignacion_curso_id == asig.id).all()}
        for act in sorted(curso.actividades, key=lambda a: a.fecha_limite):
            if act.estado != "ACTIVO":
                continue
            entrega = entregas.get(act.id)
            ultima = entrega.versiones[-1] if entrega and entrega.versiones else None
            estado = estado_actividad(act, entrega, ahora)
            dias = (act.fecha_limite - ahora).total_seconds() / 86400
            resultado.append({
                "id": act.id,
                "curso_id": curso.id,
                "curso_codigo": curso.codigo,
                "curso_nombre": curso.nombre,
                "inscripcion_id": insc.id,
                "titulo": act.titulo,
                "tipo": act.tipo,
                "ponderacion": float(act.ponderacion or 0),
                "es_obligatorio": act.es_obligatorio,
                "fecha_apertura": act.fecha_apertura,
                "fecha_limite": act.fecha_limite,
                "estado": estado,
                "intentos_usados": entrega.numero_versiones if entrega else 0,
                "max_reenvios": act.max_reenvios,
                "fecha_entrega": ultima.fecha_entrega if ultima else None,
                "entrega_tardia": bool(ultima and ultima.es_tardia),
                "nota": float(ultima.evaluacion.puntaje_obtenido) if ultima and ultima.evaluacion else None,
                "dias_restantes": round(dias, 1),
                "vence_pronto": estado in ESTADOS_ABIERTOS and 0 <= dias <= dias_alerta,
            })
    return resultado
