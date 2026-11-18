import json
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles, verify_program_access
from app.models.entities import Programa, Convocatoria, CoordinadorPrograma, Usuario, RegistroAuditoria, Inscripcion
from app.schemas.pydantic_models import (
    ProgramOut, ProgramCreate, ConvocatoriaOut, ConvocatoriaCreate,
    ConvocatoriaUpdate, ConvocatoriaEstadoUpdate
)

from app.services.progress_service import cerrar_convocatoria, reabrir_convocatoria, inscritos_vigentes
from app.services.tutoria import cursos_sin_tutor
from app.models.entities import CursoPreparatorio
from app.services.process_emails import correo_proceso_aprobado, correo_proceso_no_aprobado

router = APIRouter(prefix="/programas", tags=["Programas y Convocatorias"])

# Ciclo de vida de una convocatoria. Además del paso al estado siguiente se permite:
# - EN_CURSO -> ABIERTA: reabrir inscripciones por un tiempo corto (con una fecha de cierre futura)
# - FINALIZADA -> CERRADA: reabrir una convocatoria finalizada, con motivo
FLUJO_ESTADOS_CONVOCATORIA = ["PLANIFICADA", "ABIERTA", "EN_CURSO", "CERRADA", "FINALIZADA"]
TRANSICIONES_CONVOCATORIA = {
    "PLANIFICADA": ["ABIERTA"],
    "ABIERTA": ["EN_CURSO"],
    "EN_CURSO": ["CERRADA", "ABIERTA"],
    "CERRADA": ["FINALIZADA"],
    "FINALIZADA": ["CERRADA"],
}
MODALIDADES = ["PRESENCIAL", "EN_LINEA", "HIBRIDA"]


def convocatoria_out(db: Session, conv: Convocatoria) -> ConvocatoriaOut:
    out = ConvocatoriaOut.model_validate(conv)
    out.inscritos = inscritos_vigentes(db, conv.id)
    return out


def _validar_fechas_convocatoria(data):
    if data.modalidad not in MODALIDADES:
        raise HTTPException(status_code=400, detail=f"Modalidad inválida. Use: {', '.join(MODALIDADES)}.")
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
        "cupo_maximo": conv.cupo_maximo,
        "modalidad": conv.modalidad,
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
    return [convocatoria_out(db, c) for c in db.query(Convocatoria).filter(Convocatoria.programa_id == programa_id).all()]

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
        cupo_maximo=data.cupo_maximo,
        modalidad=data.modalidad,
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
    return convocatoria_out(db, conv)

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
    inscritos = inscritos_vigentes(db, conv.id)
    if data.cupo_maximo < inscritos:
        raise HTTPException(status_code=400, detail=f"Ya hay {inscritos} inscritos; el cupo no puede ser menor.")
    conv.cupo_maximo = data.cupo_maximo
    conv.modalidad = data.modalidad

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
    return convocatoria_out(db, conv)

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

    permitidos = TRANSICIONES_CONVOCATORIA.get(conv.estado, [])
    if nuevo_estado not in permitidos:
        raise HTTPException(status_code=400, detail=f"Desde {conv.estado} solo se puede pasar a {' o '.join(permitidos)}.")
    motivo = (data.motivo or "").strip()
    if conv.estado == "EN_CURSO" and nuevo_estado == "ABIERTA" and conv.fecha_cierre < date.today():
        raise HTTPException(status_code=400, detail="Para reabrir las inscripciones, primero ponga una nueva fecha de cierre (hoy o después).")
    if conv.estado == "PLANIFICADA" and nuevo_estado == "ABIERTA":
        # No se abre una convocatoria sin cursos ni con cursos sin tutor
        hay_cursos = db.query(CursoPreparatorio.id).filter(
            CursoPreparatorio.convocatoria_id == conv.id, CursoPreparatorio.estado == "ACTIVO").first()
        if not hay_cursos:
            raise HTTPException(status_code=400, detail="Agregue al menos un curso preparatorio antes de abrir la convocatoria.")
        faltan = cursos_sin_tutor(db, conv.id)
        if faltan:
            raise HTTPException(status_code=400, detail="Cada curso necesita un tutor antes de abrir la convocatoria. Sin tutor: "
                                + ", ".join(c.nombre for c in faltan) + ".")
    if conv.estado == "FINALIZADA" and len(motivo) < 5:
        raise HTTPException(status_code=400, detail="Para reabrir una convocatoria finalizada indique el motivo (al menos 5 caracteres).")

    anterior = conv.estado
    conv.estado = nuevo_estado

    # Al finalizar, quien no aprobó todos sus cursos queda NO_APROBADO; al reabrir, vuelve a su estado anterior
    resumen_cierre = cerrar_convocatoria(db, conv, current_user.id) if nuevo_estado == "FINALIZADA" else None
    resumen_reapertura = reabrir_convocatoria(db, conv, current_user.id) if anterior == "FINALIZADA" else None
    db.add(RegistroAuditoria(
        usuario_id=current_user.id,
        accion="CAMBIAR_ESTADO_CONVOCATORIA",
        entidad="CONVOCATORIA",
        entidad_id=str(conv.id),
        datos_anteriores_json=json.dumps({"estado": anterior}),
        datos_nuevos_json=json.dumps({"estado": nuevo_estado, "cierre": resumen_cierre,
                                      "reapertura": resumen_reapertura, "motivo": motivo or None}, ensure_ascii=False)
    ))
    db.commit()

    # Cada postulante recibe su resultado final
    if resumen_cierre:
        for insc_id in resumen_cierre["ids_aprobados"]:
            correo_proceso_aprobado(db, db.get(Inscripcion, insc_id))
        for insc_id in resumen_cierre["ids_no_aprobados"]:
            correo_proceso_no_aprobado(db, db.get(Inscripcion, insc_id))
    db.refresh(conv)
    return convocatoria_out(db, conv)
