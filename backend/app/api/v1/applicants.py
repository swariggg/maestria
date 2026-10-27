from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Inscripcion, Usuario, Programa, Convocatoria, AsignacionTutor, 
    CoordinadorPrograma, AsignacionCurso, ActividadCurso, EntregaEvidencia
)
from app.schemas.pydantic_models import ApplicantListItem

router = APIRouter(prefix="/postulantes", tags=["Postulantes e Inscripciones"])

@router.get("", response_model=List[ApplicantListItem])
def list_applicants(
    search: Optional[str] = Query(None, description="Búsqueda por nombre o cédula"),
    programa_id: Optional[int] = Query(None),
    convocatoria_id: Optional[int] = Query(None),
    nivel_riesgo: Optional[str] = Query(None),
    estado_proceso: Optional[str] = Query(None),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Inscripcion).join(Usuario, Inscripcion.postulante_id == Usuario.id).join(Convocatoria).join(Programa)

    # Filtrado según alcance por Rol (ABAC)
    if current_user.rol.codigo == "POSTULANTE":
        query = query.filter(Inscripcion.postulante_id == current_user.id)
    elif current_user.rol.codigo == "TUTOR":
        query = query.join(AsignacionTutor, AsignacionTutor.inscripcion_id == Inscripcion.id).filter(
            AsignacionTutor.tutor_id == current_user.id,
            AsignacionTutor.estado == 'ACTIVO'
        )
    elif current_user.rol.codigo == "COORDINADOR":
        query = query.join(
            CoordinadorPrograma, CoordinadorPrograma.programa_id == Convocatoria.programa_id
        ).filter(
            CoordinadorPrograma.coordinador_id == current_user.id,
            CoordinadorPrograma.activo == True
        )
    # ADMIN tiene acceso global a todos los registros

    # Filtros opcionales
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(or_(Usuario.nombre_completo.ilike(search_fmt), Usuario.cedula.ilike(search_fmt)))
    if programa_id:
        query = query.filter(Convocatoria.programa_id == programa_id)
    if convocatoria_id:
        query = query.filter(Inscripcion.convocatoria_id == convocatoria_id)
    if nivel_riesgo:
        query = query.filter(Inscripcion.nivel_riesgo == nivel_riesgo.upper())
    if estado_proceso:
        query = query.filter(Inscripcion.estado_proceso == estado_proceso)

    inscripciones = query.order_by(Inscripcion.fecha_inscripcion.desc()).all()

    resultados = []
    for insc in inscripciones:
        post = insc.postulante
        conv = insc.convocatoria
        prog = conv.programa

        tutor_asig = db.query(AsignacionTutor).filter(
            AsignacionTutor.inscripcion_id == insc.id,
            AsignacionTutor.estado == 'ACTIVO'
        ).first()
        tutor_nombre = tutor_asig.tutor.nombre_completo if tutor_asig else None

        # Calcular avance real
        asig_c = db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == insc.id).first()
        pct_avance = 0.0
        if asig_c:
            total_acts = db.query(ActividadCurso).filter(ActividadCurso.curso_id == asig_c.curso_id).count()
            if total_acts > 0:
                aprobadas = db.query(EntregaEvidencia).filter(
                    EntregaEvidencia.asignacion_curso_id == asig_c.id,
                    EntregaEvidencia.estado_entrega == 'APROBADO'
                ).count()
                pct_avance = round((aprobadas / total_acts) * 100.0, 1)

        resultados.append(ApplicantListItem(
            id=insc.id,
            postulante_id=post.id,
            nombre_completo=post.nombre_completo,
            email=post.email,
            cedula=post.cedula,
            programa_codigo=prog.codigo,
            programa_nombre=prog.nombre,
            convocatoria_nombre=conv.nombre,
            estado_proceso=insc.estado_proceso,
            nivel_riesgo=insc.nivel_riesgo,
            motivo_riesgo=insc.motivo_riesgo,
            fecha_inscripcion=insc.fecha_inscripcion,
            tutor_nombre=tutor_nombre,
            porcentaje_avance=pct_avance
        ))

    return resultados
