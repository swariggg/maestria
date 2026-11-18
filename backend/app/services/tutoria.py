"""
Un tutor por curso preparatorio.

El coordinador elige el tutor de cada curso. Un tutor acompaña a todos los postulantes
asignados a sus cursos: los ve, los califica en esos cursos y les da seguimiento.
"""
from typing import List
from sqlalchemy.orm import Session
from app.models.entities import AsignacionCurso, CursoPreparatorio, Inscripcion, Usuario


def subconsulta_inscripciones_tutor(db: Session, tutor_id: int):
    """Ids de las inscripciones que tienen al menos un curso con este tutor."""
    return db.query(AsignacionCurso.inscripcion_id).join(
        CursoPreparatorio, CursoPreparatorio.id == AsignacionCurso.curso_id
    ).filter(CursoPreparatorio.tutor_id == tutor_id)


def inscripciones_del_tutor(db: Session, tutor_id: int):
    """Consulta de inscripciones de los postulantes que el tutor acompaña."""
    return db.query(Inscripcion).filter(Inscripcion.id.in_(subconsulta_inscripciones_tutor(db, tutor_id)))


def es_tutor_de_inscripcion(db: Session, tutor_id: int, inscripcion_id: int) -> bool:
    return db.query(AsignacionCurso.id).join(
        CursoPreparatorio, CursoPreparatorio.id == AsignacionCurso.curso_id
    ).filter(AsignacionCurso.inscripcion_id == inscripcion_id, CursoPreparatorio.tutor_id == tutor_id).first() is not None


def tutores_de_inscripcion(db: Session, inscripcion: Inscripcion) -> List[Usuario]:
    """Tutores de los cursos del postulante, sin repetir, en el orden de los cursos."""
    cursos = db.query(CursoPreparatorio).join(
        AsignacionCurso, AsignacionCurso.curso_id == CursoPreparatorio.id
    ).filter(AsignacionCurso.inscripcion_id == inscripcion.id).order_by(CursoPreparatorio.id).all()
    vistos, tutores = set(), []
    for c in cursos:
        if c.tutor and c.tutor.id not in vistos:
            vistos.add(c.tutor.id)
            tutores.append(c.tutor)
    return tutores


def nombres_tutores(db: Session, inscripcion: Inscripcion, vacio: str = None) -> str:
    nombres = [t.nombre_completo for t in tutores_de_inscripcion(db, inscripcion)]
    return ", ".join(nombres) if nombres else vacio


def cursos_sin_tutor(db: Session, convocatoria_id: int) -> List[CursoPreparatorio]:
    return db.query(CursoPreparatorio).filter(
        CursoPreparatorio.convocatoria_id == convocatoria_id,
        CursoPreparatorio.estado == "ACTIVO",
        CursoPreparatorio.tutor_id.is_(None),
    ).all()
