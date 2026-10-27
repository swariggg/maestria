from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import CursoPreparatorio, ActividadCurso, Convocatoria, Usuario, RegistroAuditoria
from app.schemas.pydantic_models import CourseOut, CourseCreate, ActivityOut, ActivityCreate

router = APIRouter(prefix="/cursos", tags=["Cursos y Actividades"])

@router.get("", response_model=List[CourseOut])
def list_courses(convocatoria_id: int = None, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CursoPreparatorio)
    if convocatoria_id:
        query = query.filter(CursoPreparatorio.convocatoria_id == convocatoria_id)
    return query.all()

@router.post("", response_model=CourseOut)
def create_course(
    data: CourseCreate, 
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")), 
    db: Session = Depends(get_db)
):
    convocatoria = db.query(Convocatoria).filter(Convocatoria.id == data.convocatoria_id).first()
    if not convocatoria:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")

    if not verify_program_access(current_user, convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene permiso para crear cursos en esta convocatoria.")

    curso = CursoPreparatorio(
        convocatoria_id=data.convocatoria_id,
        codigo=data.codigo,
        nombre=data.nombre,
        descripcion=data.descripcion,
        nota_minima=data.nota_minima,
        ponderacion_total=data.ponderacion_total,
        estado="ACTIVO"
    )
    db.add(curso)
    db.commit()
    db.refresh(curso)

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_CURSO",
        entidad="CURSO_PREPARATORIO",
        entidad_id=str(curso.id)
    ))
    db.commit()
    return curso

@router.get("/{curso_id}/actividades", response_model=List[ActivityOut])
def list_activities(curso_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ActividadCurso).filter(ActividadCurso.curso_id == curso_id).order_by(ActividadCurso.fecha_limite.asc()).all()

@router.post("/actividades", response_model=ActivityOut)
def create_activity(
    data: ActivityCreate, 
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")), 
    db: Session = Depends(get_db)
):
    curso = db.query(CursoPreparatorio).filter(CursoPreparatorio.id == data.curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")

    convocatoria = db.query(Convocatoria).filter(Convocatoria.id == curso.convocatoria_id).first()
    if not verify_program_access(current_user, convocatoria.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene permiso para agregar actividades en este curso.")

    # Validar sumatoria de ponderaciones
    actividades_actuales = db.query(ActividadCurso).filter(ActividadCurso.curso_id == curso.id).all()
    suma_actual = sum(float(a.ponderacion) for a in actividades_actuales)
    if (suma_actual + float(data.ponderacion)) > float(curso.ponderacion_total):
        raise HTTPException(
            status_code=400, 
            detail=f"La ponderación acumulada ({suma_actual + float(data.ponderacion):.1f}%) excede el 100% del curso ({curso.ponderacion_total:.1f}%)."
        )

    if data.fecha_limite <= data.fecha_apertura:
        raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a la fecha de apertura.")

    act = ActividadCurso(
        curso_id=data.curso_id,
        titulo=data.titulo,
        tipo=data.tipo,
        instrucciones=data.instrucciones,
        fecha_apertura=data.fecha_apertura,
        fecha_limite=data.fecha_limite,
        ponderacion=data.ponderacion,
        es_obligatorio=data.es_obligatorio,
        extensiones_permitidas=data.extensiones_permitidas,
        tamano_max_mb=data.tamano_max_mb,
        max_reenvios=data.max_reenvios,
        estado="ACTIVO"
    )
    db.add(act)
    db.commit()
    db.refresh(act)

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_ACTIVIDAD",
        entidad="ACTIVIDAD_CURSO",
        entidad_id=str(act.id)
    ))
    db.commit()
    return act
