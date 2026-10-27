from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Programa, Convocatoria, CoordinadorPrograma, Usuario, RegistroAuditoria
from app.schemas.pydantic_models import ProgramOut, ProgramCreate, ConvocatoriaOut, ConvocatoriaCreate

router = APIRouter(prefix="/programas", tags=["Programas y Convocatorias"])

@router.get("", response_model=List[ProgramOut])
def list_programs(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.rol.codigo == "ADMIN":
        return db.query(Programa).all()
    elif current_user.rol.codigo == "COORDINADOR":
        # Solo sus programas asignados
        return db.query(Programa).join(CoordinadorPrograma).filter(
            CoordinadorPrograma.coordinador_id == current_user.id,
            CoordinadorPrograma.activo == True
        ).all()
    else:
        # Postulante / Tutor: programas activos
        return db.query(Programa).filter(Programa.estado == "ACTIVO").all()

@router.post("", response_model=ProgramOut)
def create_program(
    data: ProgramCreate, 
    current_user: Usuario = Depends(require_roles("ADMIN")), 
    db: Session = Depends(get_db)
):
    if db.query(Programa).filter(Programa.codigo == data.codigo.upper()).first():
        raise HTTPException(status_code=400, detail="El código de programa ya existe.")

    prog = Programa(
        codigo=data.codigo.upper(),
        nombre=data.nombre,
        descripcion=data.descripcion,
        estado="ACTIVO",
        creado_por=current_user.id
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_PROGRAMA",
        entidad="PROGRAMA",
        entidad_id=str(prog.id),
        datos_nuevos_json=f'{{"codigo": "{prog.codigo}", "nombre": "{prog.nombre}"}}'
    ))
    db.commit()
    return prog

@router.get("/{programa_id}/convocatorias", response_model=List[ConvocatoriaOut])
def list_convocatorias_by_program(
    programa_id: int, 
    current_user: Usuario = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not verify_program_access(current_user, programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este programa.")
    return db.query(Convocatoria).filter(Convocatoria.programa_id == programa_id).all()

@router.post("/convocatorias", response_model=ConvocatoriaOut)
def create_convocatoria(
    data: ConvocatoriaCreate, 
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")), 
    db: Session = Depends(get_db)
):
    if not verify_program_access(current_user, data.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización para crear convocatorias en este programa.")

    if data.fecha_cierre < data.fecha_apertura:
        raise HTTPException(status_code=400, detail="La fecha de cierre no puede ser anterior a la fecha de apertura.")
    if data.fecha_fin_preparatorio < data.fecha_inicio_preparatorio:
        raise HTTPException(status_code=400, detail="El fin del preparatorio no puede ser anterior al inicio.")

    conv = Convocatoria(
        programa_id=data.programa_id,
        codigo=data.codigo,
        nombre=data.nombre,
        fecha_apertura=data.fecha_apertura,
        fecha_cierre=data.fecha_cierre,
        fecha_inicio_preparatorio=data.fecha_inicio_preparatorio,
        fecha_fin_preparatorio=data.fecha_fin_preparatorio,
        estado="ABIERTA"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_CONVOCATORIA",
        entidad="CONVOCATORIA",
        entidad_id=str(conv.id)
    ))
    db.commit()
    return conv
