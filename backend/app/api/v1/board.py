"""
Tablero del postulante: sus cursos y actividades en columnas (tipo kanban) y la agenda por fecha.
Cada actividad trae su estado, la fecha en que entregó y si vence pronto.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import Usuario, Inscripcion, EntregaEvidencia, ActividadCurso
from app.services.progress_service import asignaciones_del_postulante, calcular_avance, ESTADOS_INSCRIPCION_CERRADA
from app.services.parametros import get_int

router = APIRouter(prefix="/tablero", tags=["Tablero del postulante"])

# Estado de la entrega -> columna del tablero
ESTADO_ENTREGA = {
    "APROBADO": "APROBADA",
    "REQUIERE_CORRECCION": "POR_CORREGIR",
    "RECHAZADO": "RECHAZADA",
    "ENTREGADO": "EN_REVISION",
    "REVISADO": "EN_REVISION",
}
ESTADOS_ABIERTOS = ("PENDIENTE", "POR_CORREGIR")


def _estado_actividad(act: ActividadCurso, entrega: EntregaEvidencia, ahora: datetime) -> str:
    if entrega and entrega.estado_entrega in ESTADO_ENTREGA:
        return ESTADO_ENTREGA[entrega.estado_entrega]
    if ahora < act.fecha_apertura:
        return "PROXIMA"
    if ahora > act.fecha_limite:
        return "VENCIDA"
    return "PENDIENTE"


@router.get("")
def my_board(current_user: Usuario = Depends(require_roles("POSTULANTE")), db: Session = Depends(get_db)):
    ahora = datetime.now()
    dias_alerta = get_int(db, "DIAS_PROXIMA_A_VENCER")
    inscripciones = db.query(Inscripcion).filter(Inscripcion.postulante_id == current_user.id).order_by(Inscripcion.id.desc()).all()
    # Primero las vigentes; las cerradas solo si no hay otra
    vigentes = [i for i in inscripciones if i.estado_proceso not in ESTADOS_INSCRIPCION_CERRADA] or inscripciones[:1]

    cursos, actividades = [], []
    for insc in vigentes:
        avance = {c["asignacion_id"]: c for c in calcular_avance(db, insc)["cursos"]}
        for asig in asignaciones_del_postulante(db, insc):
            info = avance.get(asig.id, {})
            curso = asig.curso
            cursos.append({
                "curso_id": curso.id,
                "codigo": curso.codigo,
                "nombre": curso.nombre,
                "programa": insc.convocatoria.programa.nombre,
                "inscripcion_id": insc.id,
                "tutor_nombre": curso.tutor.nombre_completo if curso.tutor else None,
                "porcentaje": info.get("porcentaje", 0.0),
                "nota_final": info.get("nota_final"),
                "nota_minima": float(curso.nota_minima),
                "estado_aprobacion": asig.estado_aprobacion,
                "certificado_estado": asig.certificado_estado,
            })
            entregas = {e.actividad_id: e for e in db.query(EntregaEvidencia).filter(
                EntregaEvidencia.asignacion_curso_id == asig.id).all()}
            for act in sorted(curso.actividades, key=lambda a: a.fecha_limite):
                if act.estado != "ACTIVO":
                    continue
                entrega = entregas.get(act.id)
                ultima = entrega.versiones[-1] if entrega and entrega.versiones else None
                estado = _estado_actividad(act, entrega, ahora)
                dias = (act.fecha_limite - ahora).total_seconds() / 86400
                actividades.append({
                    "id": act.id,
                    "curso_id": curso.id,
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

    hechas = sum(1 for a in actividades if a["estado"] == "APROBADA")
    return {
        "hoy": ahora,
        "dias_alerta": dias_alerta,
        "cursos": cursos,
        "actividades": actividades,
        "resumen": {
            "total": len(actividades),
            "aprobadas": hechas,
            "pendientes": sum(1 for a in actividades if a["estado"] in ESTADOS_ABIERTOS),
            "vencen_pronto": sum(1 for a in actividades if a["vence_pronto"]),
            "porcentaje": round(hechas / len(actividades) * 100, 1) if actividades else 0.0,
        },
    }
