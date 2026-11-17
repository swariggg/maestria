import json
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.entities import Usuario, ConfiguracionSistema, RegistroAuditoria
from app.services import parametros

router = APIRouter(prefix="/configuracion", tags=["Configuración del Sistema"])


class ParametrosUpdate(BaseModel):
    valores: Dict[str, str]


@router.get("")
def list_parameters(current_user: Usuario = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)):
    return parametros.listar(db)


@router.put("")
def update_parameters(
    data: ParametrosUpdate,
    current_user: Usuario = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db)
):
    errores = {}
    normalizados = {}
    for clave, valor in data.valores.items():
        if clave not in parametros.PARAMETROS:
            errores[clave] = "Parámetro desconocido."
            continue
        try:
            normalizados[clave] = parametros.validar_valor(clave, valor)
        except ValueError as e:
            errores[clave] = str(e)
    if errores:
        raise HTTPException(status_code=400, detail="; ".join(f"{k}: {v}" for k, v in errores.items()))

    ahora = datetime.now()
    cambios = {}
    for clave, valor in normalizados.items():
        fila = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()
        anterior = fila.valor if fila else None
        if anterior == valor:
            continue
        if not fila:
            _, _, descripcion, categoria, _, _ = parametros.PARAMETROS[clave]
            fila = ConfiguracionSistema(clave=clave, descripcion=descripcion, categoria=categoria)
            db.add(fila)
        fila.valor = valor
        fila.actualizado_en = ahora
        fila.actualizado_por = current_user.id
        cambios[clave] = {"antes": anterior, "despues": valor}

    if cambios:
        db.add(RegistroAuditoria(
            usuario_id=current_user.id,
            accion="ACTUALIZAR_CONFIGURACION",
            entidad="CONFIGURACION_SISTEMA",
            datos_anteriores_json=json.dumps({k: v["antes"] for k, v in cambios.items()}),
            datos_nuevos_json=json.dumps({k: v["despues"] for k, v in cambios.items()})
        ))
    db.commit()
    return {"mensaje": f"{len(cambios)} parámetro(s) actualizado(s).", "parametros": parametros.listar(db)}
