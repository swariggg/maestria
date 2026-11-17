"""
Parámetros del proceso que el administrador puede cambiar sin tocar el código.

Se leen de la tabla configuracion_sistema. Si la clave no existe (por ejemplo,
con la tabla vacía), se usa el valor del .env, así nada se rompe.
"""
from typing import List
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import ConfiguracionSistema

# clave: (tipo, valor por defecto, descripción, categoría, mínimo, máximo)
PARAMETROS = {
    "DIAS_INACTIVIDAD_RIESGO": ("int", lambda: settings.DIAS_INACTIVIDAD_RIESGO,
                                "Días sin avance para marcar riesgo alto por inactividad", "RIESGO", 1, 90),
    "INTENTOS_SIN_RESPUESTA_ALERTA": ("int", lambda: settings.INTENTOS_SIN_RESPUESTA_ALERTA,
                                      "Contactos seguidos sin respuesta para marcar riesgo alto", "RIESGO", 1, 10),
    "DIAS_PROXIMA_A_VENCER": ("int", lambda: 5,
                              "Días antes del vencimiento en que una actividad pendiente da riesgo medio", "RIESGO", 1, 30),
    "MARGEN_BAJO_AVANCE": ("int", lambda: settings.MARGEN_BAJO_AVANCE,
                           "Puntos por debajo del avance esperado para marcar riesgo medio", "RIESGO", 5, 100),
    "DIAS_RECORDATORIO": ("lista", lambda: "5,3,1",
                          "Días antes del vencimiento en que se envía un recordatorio por correo", "NOTIFICACIONES", 1, 60),
}


def _crudo(db: Session, clave: str) -> str:
    fila = db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave == clave).first()
    return fila.valor if fila else str(PARAMETROS[clave][1]())


def validar_valor(clave: str, valor: str) -> str:
    """Devuelve el valor normalizado o lanza ValueError con un mensaje para el usuario."""
    tipo, _, _, _, minimo, maximo = PARAMETROS[clave]
    if tipo == "int":
        try:
            n = int(str(valor).strip())
        except ValueError:
            raise ValueError("Debe ser un número entero.")
        if not minimo <= n <= maximo:
            raise ValueError(f"Debe estar entre {minimo} y {maximo}.")
        return str(n)
    try:
        dias = sorted({int(x.strip()) for x in str(valor).split(",") if x.strip()}, reverse=True)
    except ValueError:
        raise ValueError("Use números separados por coma, por ejemplo 15,10,5,3,1.")
    if not dias or any(not minimo <= d <= maximo for d in dias):
        raise ValueError(f"Cada día debe estar entre {minimo} y {maximo}.")
    return ",".join(str(d) for d in dias)


def get_int(db: Session, clave: str) -> int:
    try:
        return int(validar_valor(clave, _crudo(db, clave)))
    except ValueError:
        return int(PARAMETROS[clave][1]())


def get_lista(db: Session, clave: str) -> List[int]:
    try:
        valor = validar_valor(clave, _crudo(db, clave))
    except ValueError:
        valor = validar_valor(clave, PARAMETROS[clave][1]())
    return [int(x) for x in valor.split(",")]


def listar(db: Session) -> list:
    filas = {f.clave: f for f in db.query(ConfiguracionSistema).filter(ConfiguracionSistema.clave.in_(PARAMETROS.keys())).all()}
    resultado = []
    for clave, (tipo, defecto, descripcion, categoria, minimo, maximo) in PARAMETROS.items():
        fila = filas.get(clave)
        resultado.append({
            "clave": clave,
            "valor": fila.valor if fila else str(defecto()),
            "descripcion": descripcion,
            "categoria": categoria,
            "tipo": tipo,
            "minimo": minimo,
            "maximo": maximo,
            "origen": "BASE_DE_DATOS" if fila else "ENV",
            "actualizado_en": fila.actualizado_en if fila else None,
            "actualizado_por": fila.actualizado_por if fila else None,
        })
    return resultado
