"""Avisos dentro de la app (campana del encabezado). La app no envía correos."""
import re
from datetime import datetime
from html import unescape
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.entities import Usuario, NotificacionCola

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

# A qué sección de la app lleva cada aviso al hacer clic
DESTINO = {
    "EVIDENCIA": "evidences", "ENTREGA": "evidences", "RECORDATORIO": "evidences",
    "CERTIFICADO": "certificates", "DOCUMENTO": "profile", "RETIRO": "applicants",
    "ALERTA": "alerts", "TUTOR": "courses", "PROCESO": "dashboard", "INSCRIPCION": "enrollment",
}


def _texto(html: str, nombre: str) -> str:
    """El cuerpo se guarda en HTML; en la campana se muestra como texto corto."""
    texto = re.sub(r"<(br|/p|/li|/h2)[^>]*>", " ", html or "")
    texto = unescape(re.sub(r"<[^>]+>", "", texto))
    texto = " ".join(texto.split())
    texto = texto.split("Sistema de Gestión de Cursos Preparatorios")[0]
    for saludo in (f"Estimado(a) {nombre},", "Estimado(a)"):
        if saludo in texto:
            texto = texto.split(saludo, 1)[1]
            break
    return texto.strip()[:400]


def _out(n: NotificacionCola, nombre: str) -> dict:
    destino = next((v for k, v in DESTINO.items() if (n.tipo_evento or "").startswith(k)), "dashboard")
    return {
        "id": n.id,
        "tipo": n.tipo_evento,
        "titulo": re.sub(r"^UIDE:\s*", "", n.asunto or ""),
        "texto": _texto(n.cuerpo_html, nombre),
        "fecha": n.fecha_creacion,
        "leida": bool(n.leida),
        "destino": destino,
    }


@router.get("")
def my_notifications(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    base = db.query(NotificacionCola).filter(NotificacionCola.destinatario_id == current_user.id)
    no_leidas = base.filter(NotificacionCola.leida.isnot(True)).count()
    ultimas = base.order_by(NotificacionCola.fecha_creacion.desc(), NotificacionCola.id.desc()).limit(40).all()
    return {"no_leidas": no_leidas, "avisos": [_out(n, current_user.nombre_completo) for n in ultimas]}


@router.patch("/{notificacion_id}/leida")
def mark_read(notificacion_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(NotificacionCola).filter(NotificacionCola.id == notificacion_id,
                                          NotificacionCola.destinatario_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Aviso no encontrado.")
    if not n.leida:
        n.leida, n.fecha_lectura = True, datetime.now()
        db.commit()
    return {"ok": True}


@router.post("/leer-todas")
def mark_all_read(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.query(NotificacionCola).filter(
        NotificacionCola.destinatario_id == current_user.id, NotificacionCola.leida.isnot(True)
    ).update({NotificacionCola.leida: True, NotificacionCola.fecha_lectura: datetime.now()}, synchronize_session=False)
    db.commit()
    return {"marcadas": total}
