import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access, cursos_visibles
from app.models.entities import (
    CursoPreparatorio, ActividadCurso, Convocatoria, Usuario, RegistroAuditoria,
    EntregaEvidencia, VersionEvidencia, EvaluacionEvidencia, Inscripcion, CriterioEvaluacion, TutorPrograma
)
from app.schemas.pydantic_models import (
    CourseOut, CourseCreate, CourseUpdate, ActivityOut, ActivityCreate, ActivityUpdate
)
from app.services.process_emails import correo_proceso_aprobado
from app.services.progress_service import (
    asignar_curso_a_inscritos, actualizar_estado_inscripcion, CONV_PERMITE_CURSOS, ESTADOS_INSCRIPCION_CERRADA
)

router = APIRouter(prefix="/cursos", tags=["Cursos y Actividades"])

TIPOS_ACTIVIDAD = ["INDIVIDUAL", "PROYECTO"]


# ---------- Utilidades ----------

def _convocatoria_editable(db: Session, user: Usuario, convocatoria_id: int, que: str) -> Convocatoria:
    convocatoria = db.query(Convocatoria).filter(Convocatoria.id == convocatoria_id).first()
    if not convocatoria:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")
    if not verify_program_access(user, convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail=f"No tiene permiso para modificar {que} en esta convocatoria.")
    if convocatoria.estado not in CONV_PERMITE_CURSOS:
        raise HTTPException(status_code=400, detail=f"La convocatoria está {convocatoria.estado}; ya no se pueden modificar {que}.")
    return convocatoria


def _curso_editable(db: Session, user: Usuario, curso_id: int, que: str = "actividades") -> CursoPreparatorio:
    curso = db.query(CursoPreparatorio).filter(CursoPreparatorio.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    _convocatoria_editable(db, user, curso.convocatoria_id, que)
    return curso


def _codigo_unico(db: Session, convocatoria_id: int, codigo: str, excluir_id: int = None):
    q = db.query(CursoPreparatorio).filter(
        CursoPreparatorio.convocatoria_id == convocatoria_id,
        CursoPreparatorio.codigo == codigo
    )
    if excluir_id:
        q = q.filter(CursoPreparatorio.id != excluir_id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"Ya existe un curso con el código {codigo} en esta convocatoria.")


def _validar_actividad(db: Session, curso: CursoPreparatorio, data, excluir_id: int = None):
    """Fechas, tipo y regla del 100 %: la suma de las actividades activas no supera la del curso."""
    if data.tipo not in TIPOS_ACTIVIDAD:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(TIPOS_ACTIVIDAD)}.")
    if data.fecha_limite <= data.fecha_apertura:
        raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a la fecha de apertura.")
    otras = db.query(ActividadCurso).filter(
        ActividadCurso.curso_id == curso.id,
        ActividadCurso.estado == "ACTIVO"
    )
    if excluir_id:
        otras = otras.filter(ActividadCurso.id != excluir_id)
    suma = sum(float(a.ponderacion) for a in otras.all()) + float(data.ponderacion)
    if suma > float(curso.ponderacion_total):
        raise HTTPException(
            status_code=400,
            detail=f"La ponderación acumulada ({suma:.1f}%) excede el {float(curso.ponderacion_total):.0f}% del curso."
        )


def _normalizar_extensiones(valor: str) -> str:
    lista = [e.strip().lower().lstrip(".") for e in valor.split(",") if e.strip()]
    if not lista:
        raise HTTPException(status_code=400, detail="Indique al menos una extensión permitida.")
    return ",".join(dict.fromkeys(lista))


def _recalcular_inscritos(db: Session, curso: CursoPreparatorio, usuario_id: int) -> list:
    """
    Tras cambiar un curso o sus actividades, se recalcula la nota y el estado de cada inscrito vigente.
    Devuelve las inscripciones que acaban de aprobar, para avisarles por correo tras el commit.
    """
    inscripciones = db.query(Inscripcion).filter(
        Inscripcion.convocatoria_id == curso.convocatoria_id,
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()
    return [insc for insc in inscripciones if actualizar_estado_inscripcion(db, insc, usuario_id)]


def _avisar_aprobados(db: Session, aprobados: list):
    for insc in aprobados:
        correo_proceso_aprobado(db, insc)


def _auditar(db, usuario_id, accion, entidad, entidad_id, antes=None, despues=None):
    db.add(RegistroAuditoria(
        usuario_id=usuario_id, accion=accion, entidad=entidad, entidad_id=str(entidad_id),
        datos_anteriores_json=json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
        datos_nuevos_json=json.dumps(despues, ensure_ascii=False, default=str) if despues is not None else None,
    ))


# ---------- Cursos ----------

@router.get("", response_model=List[CourseOut])
def list_courses(convocatoria_id: int = None, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    # Coordinador: cursos de sus programas. Tutor y postulante: los cursos asignados
    query = cursos_visibles(current_user, db)
    if convocatoria_id:
        query = query.filter(CursoPreparatorio.convocatoria_id == convocatoria_id)
    return query.order_by(CursoPreparatorio.id.asc()).all()


@router.post("", response_model=CourseOut)
def create_course(
    data: CourseCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    _convocatoria_editable(db, current_user, data.convocatoria_id, "cursos")
    codigo = data.codigo.strip().upper()
    _codigo_unico(db, data.convocatoria_id, codigo)

    curso = CursoPreparatorio(
        convocatoria_id=data.convocatoria_id,
        codigo=codigo,
        nombre=data.nombre.strip(),
        descripcion=data.descripcion,
        nota_minima=data.nota_minima,
        ponderacion_total=data.ponderacion_total,
        estado="ACTIVO"
    )
    db.add(curso)
    db.flush()

    # Los postulantes ya inscritos en la convocatoria también reciben el curso nuevo
    asignados = asignar_curso_a_inscritos(db, curso)

    _auditar(db, current_user.id, "CREAR_CURSO", "CURSO_PREPARATORIO", curso.id,
             despues={"convocatoria_id": curso.convocatoria_id, "codigo": codigo, "asignado_a_inscritos": asignados})
    db.commit()
    db.refresh(curso)
    return curso


@router.put("/{curso_id}", response_model=CourseOut)
def update_course(
    curso_id: int,
    data: CourseUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    curso = _curso_editable(db, current_user, curso_id, "cursos")
    codigo = data.codigo.strip().upper()
    _codigo_unico(db, curso.convocatoria_id, codigo, excluir_id=curso.id)

    antes = {"codigo": curso.codigo, "nombre": curso.nombre, "nota_minima": float(curso.nota_minima)}
    curso.codigo = codigo
    curso.nombre = data.nombre.strip()
    curso.descripcion = data.descripcion
    nota_cambio = float(curso.nota_minima) != float(data.nota_minima)
    curso.nota_minima = data.nota_minima

    db.flush()
    # Con otra nota mínima, algunos postulantes pueden aprobar o dejar de aprobar el curso
    aprobados = _recalcular_inscritos(db, curso, current_user.id) if nota_cambio else []

    _auditar(db, current_user.id, "EDITAR_CURSO", "CURSO_PREPARATORIO", curso.id, antes=antes,
             despues={"codigo": codigo, "nombre": curso.nombre, "nota_minima": float(data.nota_minima)})
    db.commit()
    _avisar_aprobados(db, aprobados)
    db.refresh(curso)
    return curso


# ---------- Actividades ----------

@router.get("/{curso_id}/actividades", response_model=List[ActivityOut])
def list_activities(curso_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if not cursos_visibles(current_user, db).filter(CursoPreparatorio.id == curso_id).first():
        raise HTTPException(status_code=404, detail="Curso no encontrado.")
    query = db.query(ActividadCurso).filter(ActividadCurso.curso_id == curso_id)
    # El postulante solo ve las actividades vigentes; el personal ve también las dadas de baja
    if current_user.rol.codigo == "POSTULANTE":
        query = query.filter(ActividadCurso.estado == "ACTIVO")
    return query.order_by(ActividadCurso.fecha_limite.asc()).all()


@router.post("/actividades", response_model=ActivityOut)
def create_activity(
    data: ActivityCreate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    curso = _curso_editable(db, current_user, data.curso_id)
    _validar_actividad(db, curso, data)

    act = ActividadCurso(
        curso_id=data.curso_id,
        titulo=data.titulo.strip(),
        tipo=data.tipo,
        instrucciones=data.instrucciones,
        fecha_apertura=data.fecha_apertura,
        fecha_limite=data.fecha_limite,
        ponderacion=data.ponderacion,
        es_obligatorio=data.es_obligatorio,
        extensiones_permitidas=_normalizar_extensiones(data.extensiones_permitidas),
        tamano_max_mb=data.tamano_max_mb,
        max_reenvios=data.max_reenvios,
        estado="ACTIVO"
    )
    db.add(act)
    db.flush()
    # Una actividad obligatoria nueva puede dejar pendiente a quien ya tenía el curso aprobado
    aprobados = _recalcular_inscritos(db, curso, current_user.id)
    _auditar(db, current_user.id, "CREAR_ACTIVIDAD", "ACTIVIDAD_CURSO", act.id,
             despues={"curso_id": curso.id, "titulo": act.titulo, "ponderacion": float(data.ponderacion)})
    db.commit()
    _avisar_aprobados(db, aprobados)
    db.refresh(act)
    return act


def _actividad_editable(db: Session, user: Usuario, actividad_id: int) -> ActividadCurso:
    act = db.query(ActividadCurso).filter(ActividadCurso.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    _curso_editable(db, user, act.curso_id)
    return act


def _datos_actividad(act: ActividadCurso) -> dict:
    return {
        "titulo": act.titulo, "tipo": act.tipo, "fecha_apertura": act.fecha_apertura,
        "fecha_limite": act.fecha_limite, "ponderacion": float(act.ponderacion),
        "es_obligatorio": act.es_obligatorio, "extensiones_permitidas": act.extensiones_permitidas,
        "tamano_max_mb": act.tamano_max_mb, "max_reenvios": act.max_reenvios, "estado": act.estado,
    }


@router.put("/actividades/{actividad_id}", response_model=ActivityOut)
def update_activity(
    actividad_id: int,
    data: ActivityUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    act = _actividad_editable(db, current_user, actividad_id)
    if act.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="La actividad está dada de baja y no se puede editar.")
    curso = act.curso
    _validar_actividad(db, curso, data, excluir_id=act.id)

    # No se puede bajar la ponderación por debajo de una nota ya puesta
    nota_maxima = db.query(EvaluacionEvidencia.puntaje_obtenido).join(VersionEvidencia).join(EntregaEvidencia).filter(
        EntregaEvidencia.actividad_id == act.id
    ).order_by(EvaluacionEvidencia.puntaje_obtenido.desc()).first()
    if nota_maxima and float(nota_maxima[0]) > float(data.ponderacion):
        raise HTTPException(
            status_code=400,
            detail=f"Ya hay una calificación de {float(nota_maxima[0]):g} puntos; la ponderación no puede ser menor."
        )
    max_versiones = db.query(EntregaEvidencia.numero_versiones).filter(
        EntregaEvidencia.actividad_id == act.id
    ).order_by(EntregaEvidencia.numero_versiones.desc()).first()
    if max_versiones and max_versiones[0] > data.max_reenvios:
        raise HTTPException(
            status_code=400,
            detail=f"Un postulante ya hizo {max_versiones[0]} envíos; el máximo no puede ser menor."
        )

    antes = _datos_actividad(act)
    act.titulo = data.titulo.strip()
    act.tipo = data.tipo
    act.instrucciones = data.instrucciones
    act.fecha_apertura = data.fecha_apertura
    act.fecha_limite = data.fecha_limite
    act.ponderacion = data.ponderacion
    act.es_obligatorio = data.es_obligatorio
    act.extensiones_permitidas = _normalizar_extensiones(data.extensiones_permitidas)
    act.tamano_max_mb = data.tamano_max_mb
    act.max_reenvios = data.max_reenvios
    db.flush()
    aprobados = _recalcular_inscritos(db, curso, current_user.id)
    _auditar(db, current_user.id, "EDITAR_ACTIVIDAD", "ACTIVIDAD_CURSO", act.id, antes=antes, despues=_datos_actividad(act))
    db.commit()
    _avisar_aprobados(db, aprobados)
    db.refresh(act)
    return act


@router.delete("/actividades/{actividad_id}")
def delete_activity(
    actividad_id: int,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    """
    Sin entregas: se borra. Con entregas: se da de baja (INACTIVO) para no perder evidencias
    ni notas; deja de contar en el avance pero queda en el historial.
    """
    act = _actividad_editable(db, current_user, actividad_id)
    curso = act.curso
    antes = _datos_actividad(act)
    tiene_entregas = db.query(EntregaEvidencia).filter(EntregaEvidencia.actividad_id == act.id).count() > 0

    if tiene_entregas:
        if act.estado != "ACTIVO":
            raise HTTPException(status_code=400, detail="La actividad ya está dada de baja.")
        act.estado = "INACTIVO"
        accion, mensaje = "DAR_BAJA_ACTIVIDAD", "La actividad tiene entregas: se dio de baja y se conservan sus evidencias."
    else:
        db.query(CriterioEvaluacion).filter(CriterioEvaluacion.actividad_id == act.id).delete()
        db.delete(act)
        accion, mensaje = "ELIMINAR_ACTIVIDAD", "Actividad eliminada."
    db.flush()
    aprobados = _recalcular_inscritos(db, curso, current_user.id)
    _auditar(db, current_user.id, accion, "ACTIVIDAD_CURSO", actividad_id, antes=antes)
    db.commit()
    _avisar_aprobados(db, aprobados)
    return {"mensaje": mensaje, "dada_de_baja": tiene_entregas}


# ---------- Rúbrica (criterios de evaluación) ----------

class CriterioIn(BaseModel):
    criterio: str = Field(min_length=3, max_length=250)
    puntaje_maximo: float = Field(gt=0)


class RubricaUpdate(BaseModel):
    criterios: List[CriterioIn]


def _criterios_out(db: Session, actividad_id: int) -> list:
    filas = db.query(CriterioEvaluacion).filter(CriterioEvaluacion.actividad_id == actividad_id).order_by(CriterioEvaluacion.orden).all()
    return [{"id": c.id, "criterio": c.criterio, "puntaje_maximo": float(c.puntaje_maximo), "orden": c.orden} for c in filas]


@router.get("/actividades/{actividad_id}/criterios")
def list_criteria(actividad_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    act = db.query(ActividadCurso).filter(ActividadCurso.id == actividad_id).first()
    if not act or not cursos_visibles(current_user, db).filter(CursoPreparatorio.id == act.curso_id).first():
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    return {"actividad_id": act.id, "ponderacion": float(act.ponderacion), "criterios": _criterios_out(db, act.id)}


@router.put("/actividades/{actividad_id}/criterios")
def set_criteria(
    actividad_id: int,
    data: RubricaUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR", "TUTOR")),
    db: Session = Depends(get_db)
):
    """
    Reemplaza la rúbrica de la actividad. Los puntajes máximos deben sumar la ponderación.
    Una lista vacía quita la rúbrica. No se cambia si ya hay calificaciones.
    """
    act = db.query(ActividadCurso).filter(ActividadCurso.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada.")
    programa_id = act.curso.convocatoria.programa_id
    if current_user.rol.codigo == "TUTOR":
        permitido = db.query(TutorPrograma).filter(
            TutorPrograma.tutor_id == current_user.id, TutorPrograma.programa_id == programa_id, TutorPrograma.activo == True
        ).first()
    else:
        permitido = verify_program_access(current_user, programa_id, db)
    if not permitido:
        raise HTTPException(status_code=403, detail="No tiene permiso para editar la rúbrica de esta actividad.")
    if act.estado != "ACTIVO":
        raise HTTPException(status_code=400, detail="La actividad está dada de baja.")
    calificadas = db.query(EvaluacionEvidencia).join(VersionEvidencia).join(EntregaEvidencia).filter(
        EntregaEvidencia.actividad_id == act.id
    ).count()
    if calificadas:
        raise HTTPException(status_code=400, detail="Ya hay entregas calificadas; la rúbrica no se puede cambiar.")
    if data.criterios:
        suma = round(sum(c.puntaje_maximo for c in data.criterios), 2)
        if abs(suma - float(act.ponderacion)) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Los criterios suman {suma:g} puntos y deben sumar la ponderación de la actividad ({float(act.ponderacion):g})."
            )
    antes = _criterios_out(db, act.id)
    db.query(CriterioEvaluacion).filter(CriterioEvaluacion.actividad_id == act.id).delete()
    for i, c in enumerate(data.criterios, start=1):
        db.add(CriterioEvaluacion(actividad_id=act.id, criterio=c.criterio.strip(), puntaje_maximo=c.puntaje_maximo, orden=i))
    db.flush()
    _auditar(db, current_user.id, "EDITAR_RUBRICA", "ACTIVIDAD_CURSO", act.id, antes={"criterios": antes},
             despues={"criterios": _criterios_out(db, act.id)})
    db.commit()
    return {"actividad_id": act.id, "ponderacion": float(act.ponderacion), "criterios": _criterios_out(db, act.id)}
