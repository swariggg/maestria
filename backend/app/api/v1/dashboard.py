from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import (
    Usuario, Inscripcion, CursoPreparatorio, ActividadCurso, 
    AsignacionCurso, EntregaEvidencia, AsignacionTutor, 
    SeguimientoPostulante, CoordinadorPrograma, Convocatoria, MaterialCurso
)
from app.schemas.pydantic_models import DashboardStats
from app.services.progress_service import calcular_avance, asignaciones_del_postulante, inscripcion_cerrada


def _cumplimiento_promedio(db: Session, inscripciones) -> float:
    avances = [calcular_avance(db, i)["porcentaje"] for i in inscripciones if i.estado_proceso != "RETIRADO"]
    return round(sum(avances) / len(avances), 1) if avances else 0.0

def _actividades_pendientes(db: Session, inscripciones) -> int:
    """Suma de lo que le falta aprobar a cada postulante vigente (mismo cálculo que ve el postulante)."""
    return sum(
        calcular_avance(db, i)["actividades_pendientes"]
        for i in inscripciones if not inscripcion_cerrada(i)
    )

router = APIRouter(prefix="/dashboard", tags=["Dashboard e Indicadores"])

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    rol = current_user.rol.codigo
    stats = DashboardStats(rol=rol)
    ahora = datetime.now()

    if rol == "ADMIN":
        stats.total_postulantes = db.query(Inscripcion).count()
        stats.cursos_activos = db.query(CursoPreparatorio).filter(CursoPreparatorio.estado == 'ACTIVO').count()
        stats.postulantes_aprobados = db.query(Inscripcion).filter(Inscripcion.estado_proceso == 'APROBADO').count()
        stats.postulantes_riesgo_alto = db.query(Inscripcion).filter(Inscripcion.nivel_riesgo == 'ALTO').count()
        stats.postulantes_riesgo_medio = db.query(Inscripcion).filter(Inscripcion.nivel_riesgo == 'MEDIO').count()
        stats.postulantes_riesgo_bajo = db.query(Inscripcion).filter(Inscripcion.nivel_riesgo == 'BAJO').count()
        stats.seguimientos_totales = db.query(SeguimientoPostulante).count()
        stats.seguimientos_sin_respuesta = db.query(SeguimientoPostulante).filter(SeguimientoPostulante.hubo_respuesta == False).count()
        stats.actividades_pendientes = _actividades_pendientes(db, db.query(Inscripcion).all())
        stats.porcentaje_cumplimiento_promedio = _cumplimiento_promedio(db, db.query(Inscripcion).all())

        # Casos críticos (Riesgo Alto)
        casos_alto = db.query(Inscripcion).filter(Inscripcion.nivel_riesgo == 'ALTO').limit(5).all()
        stats.casos_criticos = [
            {
                "id": c.id,
                "nombre": c.postulante.nombre_completo,
                "programa": c.convocatoria.programa.codigo,
                "motivo": c.motivo_riesgo
            } for c in casos_alto
        ]

    elif rol == "COORDINADOR":
        programas_coord = db.query(CoordinadorPrograma.programa_id).filter(
            CoordinadorPrograma.coordinador_id == current_user.id,
            CoordinadorPrograma.activo == True
        ).all()
        prog_ids = [p[0] for p in programas_coord]

        conv_ids = [c.id for c in db.query(Convocatoria).filter(Convocatoria.programa_id.in_(prog_ids)).all()]
        
        insc_query = db.query(Inscripcion).filter(Inscripcion.convocatoria_id.in_(conv_ids))
        stats.total_postulantes = insc_query.count()
        stats.cursos_activos = db.query(CursoPreparatorio).filter(CursoPreparatorio.convocatoria_id.in_(conv_ids), CursoPreparatorio.estado == 'ACTIVO').count()
        stats.postulantes_aprobados = insc_query.filter(Inscripcion.estado_proceso == 'APROBADO').count()
        stats.postulantes_riesgo_alto = insc_query.filter(Inscripcion.nivel_riesgo == 'ALTO').count()
        stats.postulantes_riesgo_medio = insc_query.filter(Inscripcion.nivel_riesgo == 'MEDIO').count()
        stats.postulantes_riesgo_bajo = insc_query.filter(Inscripcion.nivel_riesgo == 'BAJO').count()

        insc_ids = [i.id for i in insc_query.all()]
        stats.porcentaje_cumplimiento_promedio = _cumplimiento_promedio(db, insc_query.all())
        stats.actividades_pendientes = _actividades_pendientes(db, insc_query.all())
        stats.seguimientos_totales = db.query(SeguimientoPostulante).filter(SeguimientoPostulante.inscripcion_id.in_(insc_ids)).count()
        stats.seguimientos_sin_respuesta = db.query(SeguimientoPostulante).filter(
            SeguimientoPostulante.inscripcion_id.in_(insc_ids),
            SeguimientoPostulante.hubo_respuesta == False
        ).count()

        casos_alto = insc_query.filter(Inscripcion.nivel_riesgo == 'ALTO').limit(5).all()
        stats.casos_criticos = [
            {
                "id": c.id,
                "nombre": c.postulante.nombre_completo,
                "programa": c.convocatoria.programa.codigo,
                "motivo": c.motivo_riesgo
            } for c in casos_alto
        ]

    elif rol == "TUTOR":
        asigs = db.query(AsignacionTutor).filter(
            AsignacionTutor.tutor_id == current_user.id,
            AsignacionTutor.estado == 'ACTIVO'
        ).all()
        insc_ids = [a.inscripcion_id for a in asigs]

        inscripciones_tutor = db.query(Inscripcion).filter(Inscripcion.id.in_(insc_ids)).all()
        stats.total_postulantes = len(insc_ids)
        stats.cursos_activos = db.query(AsignacionCurso.curso_id).filter(AsignacionCurso.inscripcion_id.in_(insc_ids)).distinct().count()
        stats.postulantes_aprobados = sum(1 for i in inscripciones_tutor if i.estado_proceso == 'APROBADO')
        stats.porcentaje_cumplimiento_promedio = _cumplimiento_promedio(db, inscripciones_tutor)
        stats.postulantes_riesgo_alto = db.query(Inscripcion).filter(Inscripcion.id.in_(insc_ids), Inscripcion.nivel_riesgo == 'ALTO').count()
        stats.postulantes_riesgo_medio = db.query(Inscripcion).filter(Inscripcion.id.in_(insc_ids), Inscripcion.nivel_riesgo == 'MEDIO').count()
        stats.postulantes_riesgo_bajo = db.query(Inscripcion).filter(Inscripcion.id.in_(insc_ids), Inscripcion.nivel_riesgo == 'BAJO').count()
        stats.seguimientos_totales = db.query(SeguimientoPostulante).filter(SeguimientoPostulante.inscripcion_id.in_(insc_ids)).count()
        stats.seguimientos_sin_respuesta = db.query(SeguimientoPostulante).filter(
            SeguimientoPostulante.inscripcion_id.in_(insc_ids),
            SeguimientoPostulante.hubo_respuesta == False
        ).count()

        # Evidencias pendientes de calificar para este tutor
        asigs_curso = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id.in_(insc_ids)).all()
        asig_curso_ids = [ac.id for ac in asigs_curso]
        stats.actividades_pendientes = db.query(EntregaEvidencia).filter(
            EntregaEvidencia.asignacion_curso_id.in_(asig_curso_ids),
            EntregaEvidencia.estado_entrega.in_(['ENTREGADO', 'EN_REVISION'])
        ).count()

        casos_alto = db.query(Inscripcion).filter(Inscripcion.id.in_(insc_ids), Inscripcion.nivel_riesgo == 'ALTO').limit(5).all()
        stats.casos_criticos = [
            {
                "id": c.id,
                "nombre": c.postulante.nombre_completo,
                "programa": c.convocatoria.programa.codigo,
                "motivo": c.motivo_riesgo
            } for c in casos_alto
        ]

    elif rol == "POSTULANTE":
        # Todas sus inscripciones vigentes (puede cursar dos maestrías si las fechas no se cruzan)
        inscripciones = db.query(Inscripcion).filter(
            Inscripcion.postulante_id == current_user.id,
            Inscripcion.estado_proceso != "RETIRADO"
        ).order_by(Inscripcion.fecha_inscripcion.desc()).all()
        proximos, calendario, resumen = [], [], []
        cursos = pendientes = 0
        for inscripcion in inscripciones:
            avance = calcular_avance(db, inscripcion)
            cursos += len(avance["cursos"])
            pendientes += avance["actividades_pendientes"] if not inscripcion_cerrada(inscripcion) else 0
            programa = inscripcion.convocatoria.programa.codigo
            resumen.append({
                "inscripcion_id": inscripcion.id, "programa": programa,
                "convocatoria": inscripcion.convocatoria.nombre, "estado": inscripcion.estado_proceso,
                "porcentaje": avance["porcentaje"],
            })
            if inscripcion_cerrada(inscripcion):
                continue
            for asig in asignaciones_del_postulante(db, inscripcion):
                actividades = db.query(ActividadCurso).filter(
                    ActividadCurso.curso_id == asig.curso_id,
                    ActividadCurso.estado == 'ACTIVO'
                ).all()
                for act in actividades:
                    entrega = db.query(EntregaEvidencia).filter(
                        EntregaEvidencia.asignacion_curso_id == asig.id, EntregaEvidencia.actividad_id == act.id
                    ).first()
                    item = {
                        "actividad_id": act.id,
                        "inscripcion_id": inscripcion.id,
                        "programa": programa,
                        "titulo": act.titulo,
                        "curso": asig.curso.nombre,
                        "tipo": act.tipo,
                        "ponderacion": float(act.ponderacion),
                        "fecha_limite": act.fecha_limite.strftime("%Y-%m-%d %H:%M"),
                        "dias_restantes": (act.fecha_limite - ahora).days,
                        "vencida": ahora > act.fecha_limite,
                        "estado_entrega": entrega.estado_entrega if entrega else "PENDIENTE",
                    }
                    proximos.append(item)
                    calendario.append({
                        "tipo": "ACTIVIDAD", "fecha": act.fecha_limite.strftime("%Y-%m-%d %H:%M"),
                        "titulo": act.titulo, "curso": asig.curso.nombre, "programa": programa,
                        "estado": item["estado_entrega"], "url": None,
                    })
                for ses in db.query(MaterialCurso).filter(
                    MaterialCurso.curso_id == asig.curso_id, MaterialCurso.tipo == "SESION"
                ).all():
                    calendario.append({
                        "tipo": "SESION", "fecha": ses.fecha_sesion.strftime("%Y-%m-%d %H:%M"),
                        "titulo": ses.titulo, "curso": asig.curso.nombre, "programa": programa,
                        "estado": "REALIZADA" if ses.fecha_sesion < ahora else "PROGRAMADA", "url": ses.url,
                    })
        vigentes = [r for r in resumen if not inscripcion_cerrada(next(x for x in inscripciones if x.id == r["inscripcion_id"]))]
        stats.total_postulantes = len(inscripciones)
        stats.cursos_activos = cursos
        stats.actividades_pendientes = pendientes
        base = vigentes or resumen
        stats.porcentaje_cumplimiento_promedio = round(sum(r["porcentaje"] for r in base) / len(base), 1) if base else 0.0
        stats.proximos_vencimientos = sorted(proximos, key=lambda p: p["fecha_limite"])
        stats.calendario = sorted(calendario, key=lambda c: c["fecha"])
        stats.inscripciones = resumen

    return stats
