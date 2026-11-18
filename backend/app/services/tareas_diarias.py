"""
Tareas automáticas que no dependen de una acción del usuario:
- cerrar las inscripciones cuando llega la fecha de cierre de la convocatoria;
- enviar cada mañana un resumen de pendientes a tutores y coordinadores.
"""
import json
from datetime import datetime, date, timedelta
from html import escape
from sqlalchemy.orm import Session
from app.models.entities import (
    Convocatoria, Inscripcion, SeguimientoPostulante, CompromisoSeguimiento,
    EntregaEvidencia, AsignacionCurso, DocumentoPostulante, CoordinadorPrograma, Usuario, Rol,
    NotificacionCola, RegistroAuditoria
)
from app.services.tutoria import inscripciones_del_tutor
from app.services.progress_service import ESTADOS_INSCRIPCION_CERRADA
from app.services.process_emails import _enviar

DIAS_SIN_CONTACTO = 7


def cerrar_inscripciones_vencidas(db: Session, hoy: date = None) -> dict:
    """Una convocatoria ABIERTA pasa a EN_CURSO al día siguiente de su fecha de cierre."""
    hoy = hoy or date.today()
    vencidas = db.query(Convocatoria).filter(Convocatoria.estado == "ABIERTA", Convocatoria.fecha_cierre < hoy).all()
    for conv in vencidas:
        conv.estado = "EN_CURSO"
        db.add(RegistroAuditoria(
            usuario_id=None, accion="CAMBIAR_ESTADO_CONVOCATORIA", entidad="CONVOCATORIA", entidad_id=str(conv.id),
            datos_anteriores_json=json.dumps({"estado": "ABIERTA"}),
            datos_nuevos_json=json.dumps({"estado": "EN_CURSO", "motivo": f"Cierre automático de inscripciones ({conv.fecha_cierre})"})
        ))
    db.commit()
    return {"convocatorias_cerradas": [c.codigo for c in vencidas]}


def _inscripciones_del_tutor(db: Session, tutor_id: int) -> list:
    return inscripciones_del_tutor(db, tutor_id).filter(
        Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()


def pendientes_tutor(db: Session, tutor_id: int, ahora: datetime = None) -> dict:
    ahora = ahora or datetime.now()
    por_calificar, sin_contacto, compromisos = [], [], []
    for insc in _inscripciones_del_tutor(db, tutor_id):
        nombre = insc.postulante.nombre_completo
        entregas = db.query(EntregaEvidencia).join(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == insc.id).all()
        for e in entregas:
            if e.versiones and not e.versiones[-1].evaluacion:
                por_calificar.append(f"{nombre}: {e.actividad.titulo}")
        if insc.nivel_riesgo == "ALTO":
            ultimo = db.query(SeguimientoPostulante).filter(
                SeguimientoPostulante.inscripcion_id == insc.id
            ).order_by(SeguimientoPostulante.fecha_contacto.desc()).first()
            if not ultimo or (ahora - ultimo.fecha_contacto).days >= DIAS_SIN_CONTACTO:
                sin_contacto.append(nombre)
        vencidos = db.query(CompromisoSeguimiento).join(SeguimientoPostulante).filter(
            SeguimientoPostulante.inscripcion_id == insc.id,
            CompromisoSeguimiento.cumplido == False,  # noqa: E712
            CompromisoSeguimiento.fecha_compromiso < ahora.date()
        ).all()
        compromisos += [f"{nombre}: {c.descripcion} ({c.fecha_compromiso})" for c in vencidos]
    return {"por_calificar": por_calificar, "riesgo_sin_contacto": sin_contacto, "compromisos_vencidos": compromisos}


def pendientes_coordinador(db: Session, coordinador_id: int, hoy: date = None) -> dict:
    hoy = hoy or date.today()
    programas = [p[0] for p in db.query(CoordinadorPrograma.programa_id).filter(
        CoordinadorPrograma.coordinador_id == coordinador_id, CoordinadorPrograma.activo == True  # noqa: E712
    ).all()]
    if not programas:
        return {"documentos": [], "retiros": [], "por_finalizar": []}
    inscripciones = db.query(Inscripcion).join(Convocatoria).filter(
        Convocatoria.programa_id.in_(programas), Inscripcion.estado_proceso.notin_(ESTADOS_INSCRIPCION_CERRADA)
    ).all()
    documentos, retiros = [], []
    for insc in inscripciones:
        ultimos = {}
        for d in sorted(insc.documentos, key=lambda d: d.id):
            ultimos[d.requisito_id] = d
        documentos += [f"{insc.postulante.nombre_completo}: {d.requisito.nombre}"
                       for d in ultimos.values() if d.estado_revision == "PENDIENTE"]
        if insc.retiro_solicitado_en:
            retiros.append(insc.postulante.nombre_completo)
    por_finalizar = [c.nombre for c in db.query(Convocatoria).filter(
        Convocatoria.programa_id.in_(programas), Convocatoria.estado != "FINALIZADA",
        Convocatoria.fecha_fin_preparatorio < hoy
    ).all()]
    return {"documentos": documentos, "retiros": retiros, "por_finalizar": por_finalizar}


def _lista(titulo: str, items: list) -> str:
    if not items:
        return ""
    filas = "".join(f"<li>{escape(i)}</li>" for i in items[:30])
    extra = f"<li>... y {len(items) - 30} más</li>" if len(items) > 30 else ""
    return f"<p><strong>{escape(titulo)} ({len(items)})</strong></p><ul>{filas}{extra}</ul>"


def enviar_resumenes_diarios(db: Session, ahora: datetime = None) -> dict:
    """Un correo por persona y por día, solo si tiene algo pendiente."""
    ahora = ahora or datetime.now()
    clave = f"RESUMEN_DIARIO_{ahora.strftime('%Y%m%d')}"
    enviados = 0
    usuarios = db.query(Usuario).join(Rol).filter(Rol.codigo.in_(["TUTOR", "COORDINADOR"]), Usuario.estado == "ACTIVO").all()
    for u in usuarios:
        if db.query(NotificacionCola).filter(NotificacionCola.destinatario_id == u.id, NotificacionCola.tipo_evento == clave).first():
            continue
        if u.rol.codigo == "TUTOR":
            p = pendientes_tutor(db, u.id, ahora)
            cuerpo = (_lista("Evidencias por calificar", p["por_calificar"])
                      + _lista(f"Postulantes en riesgo alto sin contacto en {DIAS_SIN_CONTACTO} días", p["riesgo_sin_contacto"])
                      + _lista("Compromisos vencidos sin cumplir", p["compromisos_vencidos"]))
        else:
            p = pendientes_coordinador(db, u.id, ahora.date())
            cuerpo = (_lista("Documentos por revisar", p["documentos"])
                      + _lista("Solicitudes de retiro", p["retiros"])
                      + _lista("Convocatorias cuyo preparatorio terminó y falta finalizar", p["por_finalizar"]))
        if not cuerpo:
            continue
        _enviar(db, u, clave, "UIDE: Sus pendientes de hoy", "Resumen del día", cuerpo)
        enviados += 1
    return {"resumenes_enviados": enviados}
