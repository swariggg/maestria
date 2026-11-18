"""
Tablero del postulante: sus cursos y actividades en columnas (tipo kanban) y la agenda por fecha.
Cada actividad trae su estado, la fecha en que entregó y si vence pronto.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import Usuario, Inscripcion
from app.services.progress_service import asignaciones_del_postulante, calcular_avance, ESTADOS_INSCRIPCION_CERRADA
from app.services.parametros import get_int
from app.services.estado_actividades import actividades_de_inscripcion, ESTADOS_ABIERTOS

router = APIRouter(prefix="/tablero", tags=["Tablero del postulante"])

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
        actividades.extend(actividades_de_inscripcion(db, insc, ahora, dias_alerta))

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
