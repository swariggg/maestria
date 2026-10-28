import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Programa, Convocatoria, CoordinadorPrograma, Usuario, RegistroAuditoria
from app.schemas.pydantic_models import (
    ProgramOut, ProgramCreate, ConvocatoriaOut, ConvocatoriaCreate,
    ConvocatoriaUpdate, ConvocatoriaEstadoUpdate
)

router = APIRouter(prefix="/programas", tags=["Programas y Convocatorias"])

# Ciclo de vida de una convocatoria: solo se avanza al estado siguiente
FLUJO_ESTADOS_CONVOCATORIA = ["PLANIFICADA", "ABIERTA", "EN_CURSO", "CERRADA", "FINALIZADA"]

def _validar_fechas_convocatoria(data):
    if data.fecha_cierre < data.fecha_apertura:
        raise HTTPException(status_code=400, detail="La fecha de cierre no puede ser anterior a la fecha de apertura.")
    if data.fecha_fin_preparatorio < data.fecha_inicio_preparatorio:
        raise HTTPException(status_code=400, detail="El fin del preparatorio no puede ser anterior al inicio.")

def _datos_convocatoria(conv: Convocatoria) -> str:
    return json.dumps({
        "nombre": conv.nombre,
        "estado": conv.estado,
        "fecha_apertura": str(conv.fecha_apertura),
        "fecha_cierre": str(conv.fecha_cierre),
        "fecha_inicio_preparatorio": str(conv.fecha_inicio_preparatorio),
        "fecha_fin_preparatorio": str(conv.fecha_fin_preparatorio),
    }, ensure_ascii=False)

def _obtener_convocatoria_gestionable(convocatoria_id: int, current_user: Usuario, db: Session) -> Convocatoria:
    conv = db.query(Convocatoria).filter(Convocatoria.id == convocatoria_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada.")
    if not verify_program_access(current_user, conv.programa_id, db):
        raise HTTPException(status_code=403, detail="No tiene autorización sobre este programa.")
    return conv

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
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")), 
    db: Session = Depends(get_db)
):
    codigo = data.codigo.strip().upper()
    if db.query(Programa).filter(Programa.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="El código de programa ya existe.")

    prog = Programa(
        codigo=codigo,
        nombre=data.nombre,
        descripcion=data.descripcion,
        estado="ACTIVO",
        creado_por=current_user.id
    )
    db.add(prog)
    db.flush()

    # El coordinador que crea el programa queda asignado a él para poder gestionarlo
    if current_user.rol.codigo == "COORDINADOR":
        db.add(CoordinadorPrograma(
            programa_id=prog.id,
            coordinador_id=current_user.id,
            activo=True,
            asignado_por=current_user.id
        ))

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_PROGRAMA",
        entidad="PROGRAMA",
        entidad_id=str(prog.id),
        datos_nuevos_json=json.dumps({"codigo": prog.codigo, "nombre": prog.nombre}, ensure_ascii=False)
    ))
    db.commit()
    db.refresh(prog)
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

    _validar_fechas_convocatoria(data)

    codigo = data.codigo.strip().upper()
    if db.query(Convocatoria).filter(Convocatoria.programa_id == data.programa_id, Convocatoria.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="Ya existe una convocatoria con ese código en el programa.")

    conv = Convocatoria(
        programa_id=data.programa_id,
        codigo=codigo,
        nombre=data.nombre,
        fecha_apertura=data.fecha_apertura,
        fecha_cierre=data.fecha_cierre,
        fecha_inicio_preparatorio=data.fecha_inicio_preparatorio,
        fecha_fin_preparatorio=data.fecha_fin_preparatorio,
        estado="PLANIFICADA"
    )
    db.add(conv)
    db.flush()

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CREAR_CONVOCATORIA",
        entidad="CONVOCATORIA",
        entidad_id=str(conv.id),
        datos_nuevos_json=_datos_convocatoria(conv)
    ))
    db.commit()
    db.refresh(conv)
    return conv

@router.put("/convocatorias/{convocatoria_id}", response_model=ConvocatoriaOut)
def update_convocatoria(
    convocatoria_id: int,
    data: ConvocatoriaUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    conv = _obtener_convocatoria_gestionable(convocatoria_id, current_user, db)
    if conv.estado == "FINALIZADA":
        raise HTTPException(status_code=400, detail="Una convocatoria finalizada no se puede editar.")

    _validar_fechas_convocatoria(data)

    anteriores = _datos_convocatoria(conv)
    conv.nombre = data.nombre
    conv.fecha_apertura = data.fecha_apertura
    conv.fecha_cierre = data.fecha_cierre
    conv.fecha_inicio_preparatorio = data.fecha_inicio_preparatorio
    conv.fecha_fin_preparatorio = data.fecha_fin_preparatorio

    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="EDITAR_CONVOCATORIA",
        entidad="CONVOCATORIA",
        entidad_id=str(conv.id),
        datos_anteriores_json=anteriores,
        datos_nuevos_json=_datos_convocatoria(conv)
    ))
    db.commit()
    db.refresh(conv)
    return conv

@router.patch("/convocatorias/{convocatoria_id}/estado", response_model=ConvocatoriaOut)
def change_convocatoria_estado(
    convocatoria_id: int,
    data: ConvocatoriaEstadoUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN", "COORDINADOR")),
    db: Session = Depends(get_db)
):
    conv = _obtener_convocatoria_gestionable(convocatoria_id, current_user, db)

    nuevo_estado = data.estado.strip().upper()
    if nuevo_estado not in FLUJO_ESTADOS_CONVOCATORIA:
        raise HTTPException(status_code=400, detail="Estado de convocatoria no válido.")

    indice_actual = FLUJO_ESTADOS_CONVOCATORIA.index(conv.estado)
    if indice_actual == len(FLUJO_ESTADOS_CONVOCATORIA) - 1:
        raise HTTPException(status_code=400, detail="La convocatoria ya está finalizada.")
    siguiente = FLUJO_ESTADOS_CONVOCATORIA[indice_actual + 1]
    if nuevo_estado != siguiente:
        raise HTTPException(
            status_code=400,
            detail=f"Desde {conv.estado} solo se puede pasar a {siguiente}."
        )

    anterior = conv.estado
    conv.estado = nuevo_estado
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CAMBIAR_ESTADO_CONVOCATORIA",
        entidad="CONVOCATORIA",
        entidad_id=str(conv.id),
        datos_anteriores_json=json.dumps({"estado": anterior}),
        datos_nuevos_json=json.dumps({"estado": nuevo_estado})
    ))
    db.commit()
    db.refresh(conv)
    return conv
