from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_applicant_access
from app.models.entities import (
    Inscripcion, Usuario, Programa, Convocatoria, 
    CoordinadorPrograma, AsignacionCurso, ActividadCurso, EntregaEvidencia
)
from app.services.tutoria import subconsulta_inscripciones_tutor, nombres_tutores
from app.schemas.pydantic_models import ApplicantListItem
from datetime import datetime
from app.services.progress_service import calcular_avance
from app.services.estado_actividades import actividades_de_inscripcion, ESTADOS_ABIERTOS
from app.services.parametros import get_int

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
        query = query.filter(Inscripcion.id.in_(subconsulta_inscripciones_tutor(db, current_user.id)))
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

    ahora = datetime.now()
    dias_alerta = get_int(db, "DIAS_PROXIMA_A_VENCER")
    # El tutor ve el peligro solo en las actividades de los cursos que dicta
    solo_tutor = current_user.id if current_user.rol.codigo == "TUTOR" else None

    resultados = []
    for insc in inscripciones:
        post = insc.postulante
        acts = actividades_de_inscripcion(db, insc, ahora, dias_alerta, solo_tutor)
        abiertas = [a for a in acts if a["estado"] in ESTADOS_ABIERTOS and a["dias_restantes"] >= 0]
        conv = insc.convocatoria
        prog = conv.programa

        tutor_nombre = nombres_tutores(db, insc)

        # Avance sumando todos los cursos asignados
        pct_avance = calcular_avance(db, insc)["porcentaje"]

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
            programa_id=prog.id,
            porcentaje_avance=pct_avance,
            requiere_adaptaciones=bool(insc.requiere_adaptaciones),
            nota_adaptaciones=insc.nota_adaptaciones,
            retiro_solicitado=bool(insc.retiro_solicitado_en),
            motivo_retiro=insc.motivo_retiro,
            actividades_por_vencer=sum(1 for a in acts if a["vence_pronto"]),
            actividades_vencidas=sum(1 for a in acts if a["estado"] == "VENCIDA"),
            proxima_entrega=min((a["fecha_limite"] for a in abiertas), default=None),
        ))

    return resultados


@router.get("/{inscripcion_id}/ficha")
def applicant_sheet(inscripcion_id: int, current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
                    db: Session = Depends(get_db)):
    """Seguimiento individual: datos personales y actividades hechas y por hacer, con las que vencen pronto."""
    insc = db.query(Inscripcion).filter(Inscripcion.id == inscripcion_id).first()
    if not insc or not verify_applicant_access(current_user, insc.postulante_id, db):
        raise HTTPException(status_code=404, detail="Postulante no encontrado.")
    post = insc.postulante
    perfil = post.perfil
    ahora = datetime.now()
    dias_alerta = get_int(db, "DIAS_PROXIMA_A_VENCER")
    solo_tutor = current_user.id if current_user.rol.codigo == "TUTOR" else None
    acts = actividades_de_inscripcion(db, insc, ahora, dias_alerta, solo_tutor)
    avance = calcular_avance(db, insc)
    cursos = [c for c in avance["cursos"] if solo_tutor is None or c["tutor_id"] == solo_tutor]
    return {
        "inscripcion_id": insc.id,
        "estado_proceso": insc.estado_proceso,
        "nivel_riesgo": insc.nivel_riesgo,
        "motivo_riesgo": insc.motivo_riesgo,
        "programa": insc.convocatoria.programa.nombre,
        "convocatoria": insc.convocatoria.nombre,
        "fecha_inscripcion": insc.fecha_inscripcion,
        "dias_alerta": dias_alerta,
        "postulante": {
            "nombre_completo": post.nombre_completo,
            "cedula": post.cedula,
            "email": post.email,
            "telefono": post.telefono,
            "fecha_nacimiento": perfil.fecha_nacimiento if perfil else None,
            "ciudad": perfil.ciudad if perfil else None,
            "titulo_tercer_nivel": perfil.titulo_tercer_nivel if perfil else None,
            "universidad_origen": perfil.universidad_origen if perfil else None,
            "contacto_emergencia": perfil.contacto_emergencia if perfil else None,
            "telefono_emergencia": perfil.telefono_emergencia if perfil else None,
            "enlaces": [e for e in (perfil.enlaces or "").splitlines() if e] if perfil else [],
        },
        "cursos": [{"curso_id": c["curso_id"], "codigo": c["codigo"], "nombre": c["nombre"], "porcentaje": c["porcentaje"],
                    "nota_final": c["nota_final"], "nota_minima": c["nota_minima"], "estado_aprobacion": c["estado_aprobacion"]}
                   for c in cursos],
        "actividades": acts,
        "resumen": {
            "hechas": sum(1 for a in acts if a["estado"] in ("APROBADA", "EN_REVISION")),
            "por_hacer": sum(1 for a in acts if a["estado"] in ESTADOS_ABIERTOS or a["estado"] == "PROXIMA"),
            "vencidas": sum(1 for a in acts if a["estado"] in ("VENCIDA", "RECHAZADA")),
            "por_vencer": sum(1 for a in acts if a["vence_pronto"]),
        },
    }
