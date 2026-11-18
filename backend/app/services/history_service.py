"""Línea de tiempo de una inscripción: todo lo que pasó con el postulante, en orden."""
import json
from sqlalchemy.orm import Session
from app.models.entities import (
    Inscripcion, RegistroAuditoria, SeguimientoPostulante, NotificacionCola, EntregaEvidencia,
    VersionEvidencia, AsignacionCurso, DocumentoPostulante, AlertaRiesgo
)

TIPO_CONTACTO = {
    "TELEFONO": "Llamada", "CORREO": "Correo", "WHATSAPP": "WhatsApp",
    "VIDEOCONFERENCIA": "Videoconferencia", "PRESENCIAL": "Reunión presencial",
}


def _evento(fecha, tipo, titulo, detalle=None, actor=None):
    return {"fecha": fecha, "tipo": tipo, "titulo": titulo, "detalle": detalle, "actor": actor}


def historial_inscripcion(db: Session, inscripcion: Inscripcion) -> list:
    eventos = []
    postulante = inscripcion.postulante

    eventos.append(_evento(inscripcion.fecha_inscripcion, "INSCRIPCION",
                           f"Inscripción en {inscripcion.convocatoria.nombre}", actor=postulante.nombre_completo))

    # Cambios de estado y acciones registradas sobre la inscripción
    for a in db.query(RegistroAuditoria).filter(
        RegistroAuditoria.entidad == "INSCRIPCION",
        RegistroAuditoria.entidad_id == str(inscripcion.id),
        RegistroAuditoria.accion.in_(["CAMBIO_ESTADO_INSCRIPCION", "DOCUMENTACION_COMPLETA"])
    ).all():
        try:
            nuevo = json.loads(a.datos_nuevos_json or "{}")
            anterior = json.loads(a.datos_anteriores_json or "{}")
        except ValueError:
            nuevo, anterior = {}, {}
        detalle = nuevo.get("motivo")
        eventos.append(_evento(a.fecha_creacion, "ESTADO",
                               f"Estado: {anterior.get('estado_proceso', '?')} → {nuevo.get('estado_proceso', '?')}",
                               detalle, a.usuario.nombre_completo if a.usuario else "Sistema"))

    # Retiro y datos administrativos
    textos = {"SOLICITAR_RETIRO": "Solicitó el retiro", "APROBAR_RETIRO": "Retiro aprobado",
              "RECHAZAR_RETIRO": "Retiro rechazado", "DATOS_ADMINISTRATIVOS": "Adaptaciones actualizadas"}
    for a in db.query(RegistroAuditoria).filter(
        RegistroAuditoria.entidad == "INSCRIPCION",
        RegistroAuditoria.entidad_id == str(inscripcion.id),
        RegistroAuditoria.accion.in_(list(textos))
    ).all():
        try:
            nuevo = json.loads(a.datos_nuevos_json or "{}")
        except ValueError:
            nuevo = {}
        detalle = nuevo.get("motivo") or nuevo.get("observacion")
        eventos.append(_evento(a.fecha_creacion, "ESTADO", textos[a.accion], detalle,
                               a.usuario.nombre_completo if a.usuario else "Sistema"))

    # Seguimientos del tutor
    for s in db.query(SeguimientoPostulante).filter(SeguimientoPostulante.inscripcion_id == inscripcion.id).all():
        respuesta = "con respuesta" if s.hubo_respuesta else "sin respuesta"
        eventos.append(_evento(s.fecha_contacto, "SEGUIMIENTO",
                               f"Seguimiento #{s.numero_seguimiento or '-'}: {TIPO_CONTACTO.get(s.tipo_contacto, s.tipo_contacto)} ({respuesta})",
                               f"{s.motivo}. {s.resultado}", s.tutor.nombre_completo))

    # Evidencias y calificaciones
    asig_ids = [a.id for a in db.query(AsignacionCurso).filter(AsignacionCurso.inscripcion_id == inscripcion.id).all()]
    if asig_ids:
        for v in db.query(VersionEvidencia).join(EntregaEvidencia).filter(EntregaEvidencia.asignacion_curso_id.in_(asig_ids)).all():
            act = v.entrega.actividad
            eventos.append(_evento(v.fecha_entrega, "EVIDENCIA",
                                   f"Evidencia v{v.numero_version}: {act.titulo}" + (" (tardía)" if v.es_tardia else ""),
                                   v.nombre_archivo_original, postulante.nombre_completo))
            if v.evaluacion:
                ev = v.evaluacion
                eventos.append(_evento(ev.fecha_evaluacion, "CALIFICACION",
                                       ("Recalificación" if ev.motivo_recalificacion else "Calificación")
                                       + f" {ev.resultado}: {act.titulo} ({float(ev.puntaje_obtenido):g}/{float(act.ponderacion):g})",
                                       (f"Motivo del cambio: {ev.motivo_recalificacion}. " if ev.motivo_recalificacion else "")
                                       + (ev.observaciones or ""), ev.evaluador.nombre_completo if ev.evaluador else None))

    # Documentos personales
    for d in db.query(DocumentoPostulante).filter(DocumentoPostulante.inscripcion_id == inscripcion.id).all():
        eventos.append(_evento(d.fecha_carga, "DOCUMENTO", f"Documento cargado: {d.requisito.nombre}",
                               d.nombre_original, postulante.nombre_completo))
        if d.fecha_revision:
            eventos.append(_evento(d.fecha_revision, "DOCUMENTO", f"Documento {d.estado_revision}: {d.requisito.nombre}",
                                   d.observaciones, d.revisor.nombre_completo if d.revisor else None))

    # Alertas de riesgo
    for al in db.query(AlertaRiesgo).filter(AlertaRiesgo.inscripcion_id == inscripcion.id).all():
        eventos.append(_evento(al.fecha_deteccion, "ALERTA", f"Alerta {al.nivel_riesgo}: {al.tipo_alerta}", al.motivo_detallado, "Sistema"))
        if al.derivada_a and al.fecha_derivacion:
            eventos.append(_evento(al.fecha_derivacion, "ALERTA", f"Alerta derivada a {al.usuario_derivado.nombre_completo}",
                                   al.nota_derivacion, None))
        if al.resuelta and al.fecha_resolucion:
            eventos.append(_evento(al.fecha_resolucion, "ALERTA", f"Alerta cerrada: {al.tipo_alerta}", al.accion_tomada,
                                   al.usuario_resolutor.nombre_completo if al.usuario_resolutor else "Sistema"))

    # Correos enviados al postulante desde su inscripción
    for n in db.query(NotificacionCola).filter(
        NotificacionCola.destinatario_id == postulante.id,
        NotificacionCola.fecha_creacion >= inscripcion.fecha_inscripcion
    ).all():
        eventos.append(_evento(n.fecha_creacion, "CORREO", n.asunto, f"Estado del envío: {n.estado}", "Sistema"))

    eventos = [e for e in eventos if e["fecha"]]
    eventos.sort(key=lambda e: e["fecha"], reverse=True)
    return eventos
