"""
Correos del proceso académico: evidencias, documentos, tutor y resultado final.

Todos usan send_or_queue_notification, así que con SMTP_TEST_MODE=true quedan
registrados en notificaciones_cola sin salir a internet.
"""
from html import escape
from sqlalchemy.orm import Session
from app.models.entities import Inscripcion, Usuario, VersionEvidencia, EvaluacionEvidencia
from app.services.notification_service import send_or_queue_notification

RESULTADO_TEXTO = {
    "APROBADO": "aprobada",
    "REQUIERE_CORRECCION": "requiere corrección",
    "RECHAZADO": "rechazada",
}


def plantilla_uide(titulo: str, nombre: str, cuerpo: str) -> str:
    """Mismo formato de los recordatorios: tarjeta blanca con el título en azul UIDE."""
    return f"""
    <div style="font-family: sans-serif; color: #252533; max-width: 600px; border: 1px solid #E6E9F2; border-radius: 16px; padding: 24px; background: #FFFFFF;">
        <h2 style="color: #910048;">{escape(titulo)}</h2>
        <p>Estimado(a) <strong>{escape(nombre)}</strong>,</p>
        {cuerpo}
        <hr style="border: none; border-top: 1px solid #E6E9F2;">
        <small style="color: #747789;">Sistema de Gestión de Cursos Preparatorios - UIDE</small>
    </div>
    """


def _enviar(db: Session, destinatario: Usuario, tipo: str, asunto: str, titulo: str, cuerpo: str):
    if not destinatario:
        return None
    return send_or_queue_notification(
        db=db,
        destinatario=destinatario,
        tipo_evento=tipo,
        asunto=asunto,
        cuerpo_html=plantilla_uide(titulo, destinatario.nombre_completo, cuerpo),
    )


def correo_evidencia_cargada(db: Session, inscripcion: Inscripcion, version: VersionEvidencia):
    act = version.entrega.actividad
    tardia = "<p style='color:#9A1B1B;'><strong>La entrega se registró fuera de plazo.</strong></p>" if version.es_tardia else ""
    cuerpo = (
        f"<p>Recibimos su evidencia para la actividad <strong>{escape(act.titulo)}</strong> "
        f"({escape(act.curso.codigo)}).</p>"
        f"<ul><li>Archivo: {escape(version.nombre_archivo_original)}</li>"
        f"<li>Versión: {version.numero_version}</li>"
        f"<li>Fecha: {version.fecha_entrega.strftime('%Y-%m-%d %H:%M')}</li></ul>"
        f"{tardia}<p>Su tutor la revisará y recibirá otro aviso con el resultado.</p>"
    )
    _enviar(db, inscripcion.postulante, "EVIDENCIA_CARGADA",
            f"Evidencia recibida: {act.titulo}", "Evidencia recibida", cuerpo)
    # El tutor del curso (o coordinación si el curso no tiene tutor) se entera de la entrega
    tutor = act.curso.tutor
    if tutor:
        _enviar(db, tutor, "ENTREGA_POR_REVISAR",
                f"Nueva entrega por revisar: {act.titulo}", "Nueva entrega",
                f"<p><strong>{escape(inscripcion.postulante.nombre_completo)}</strong> subió la versión "
                f"{version.numero_version} de <strong>{escape(act.titulo)}</strong> ({escape(act.curso.codigo)})"
                + (" fuera de plazo" if version.es_tardia else "") + ". Revísela en Evidencias.</p>")


def correo_evidencia_evaluada(db: Session, inscripcion: Inscripcion, evaluacion: EvaluacionEvidencia):
    act = evaluacion.version.entrega.actividad
    resultado = RESULTADO_TEXTO.get(evaluacion.resultado, evaluacion.resultado)
    extra = ""
    if evaluacion.observaciones:
        extra += f"<p><strong>Observaciones:</strong> {escape(evaluacion.observaciones)}</p>"
    if evaluacion.recomendaciones:
        extra += f"<p><strong>Recomendaciones:</strong> {escape(evaluacion.recomendaciones)}</p>"
    if evaluacion.resultado != "APROBADO":
        entrega = evaluacion.version.entrega
        quedan = max(0, act.max_reenvios - entrega.numero_versiones)
        if quedan:
            extra += (f"<p>Le quedan <strong>{quedan}</strong> intento(s). Cargue una nueva versión en la plataforma "
                      "antes de la fecha límite.</p>")
        else:
            extra += "<p>Ya usó todos los intentos de esta actividad.</p>"
    cuerpo = (
        f"<p>Su evidencia de <strong>{escape(act.titulo)}</strong> ({escape(act.curso.codigo)}) fue "
        f"<strong>{resultado}</strong>, con una nota de <strong>{float(evaluacion.puntaje_obtenido):g} / "
        f"{float(act.ponderacion):g}</strong>.</p>{extra}"
    )
    return _enviar(db, inscripcion.postulante, "EVIDENCIA_EVALUADA",
                   f"UIDE: Evidencia {resultado} - {act.titulo}", "Resultado de su evidencia", cuerpo)


def _tabla_cursos(inscripcion: Inscripcion) -> str:
    filas = "".join(
        f"<tr><td style='padding:4px 8px;'>{escape(a.curso.codigo)} · {escape(a.curso.nombre)}</td>"
        f"<td style='padding:4px 8px;text-align:right;'>{float(a.nota_final or 0):g} / mín. {float(a.curso.nota_minima):g}</td>"
        f"<td style='padding:4px 8px;'>{escape(a.estado_aprobacion)}</td></tr>"
        for a in inscripcion.asignaciones_cursos
    )
    return f"<table style='border-collapse:collapse;font-size:14px;'>{filas}</table>"


def correo_proceso_aprobado(db: Session, inscripcion: Inscripcion):
    conv = inscripcion.convocatoria
    cuerpo = (
        f"<p>¡Felicitaciones! Aprobó el preparatorio de <strong>{escape(conv.programa.nombre)}</strong> "
        f"({escape(conv.nombre)}).</p><p>Resumen de sus cursos:</p>{_tabla_cursos(inscripcion)}"
        f"<p>Coordinación se comunicará con usted para los siguientes pasos de admisión.</p>"
    )
    return _enviar(db, inscripcion.postulante, "PROCESO_APROBADO",
                   "UIDE: Aprobó el curso preparatorio", "Preparatorio aprobado", cuerpo)


def correo_no_aprobado_por_intentos(db: Session, inscripcion: Inscripcion, motivo: str):
    cuerpo = (
        f"<p>Su proceso en <strong>{escape(inscripcion.convocatoria.nombre)}</strong> quedó como "
        f"<strong>no aprobado</strong>.</p><p>{escape(motivo)}</p>"
        f"<p>Resumen de sus cursos:</p>{_tabla_cursos(inscripcion)}"
        f"<p>Si tiene dudas, comuníquese con coordinación.</p>"
    )
    return _enviar(db, inscripcion.postulante, "PROCESO_NO_APROBADO",
                   "UIDE: Resultado del curso preparatorio", "Resultado del preparatorio", cuerpo)


def _coordinadores(db: Session, inscripcion: Inscripcion) -> list:
    from app.models.entities import CoordinadorPrograma
    filas = db.query(CoordinadorPrograma).filter(
        CoordinadorPrograma.programa_id == inscripcion.convocatoria.programa_id,
        CoordinadorPrograma.activo == True  # noqa: E712
    ).all()
    return [f.coordinador for f in filas if f.coordinador.estado == "ACTIVO"]


def correo_retiro_solicitado(db: Session, inscripcion: Inscripcion):
    p = inscripcion.postulante
    for coord in _coordinadores(db, inscripcion):
        _enviar(db, coord, "RETIRO_SOLICITADO",
                f"UIDE: Solicitud de retiro - {p.nombre_completo}", "Solicitud de retiro",
                f"<p><strong>{escape(p.nombre_completo)}</strong> (CI {escape(p.cedula)}) pidió retirarse de "
                f"<strong>{escape(inscripcion.convocatoria.nombre)}</strong>.</p>"
                f"<p><strong>Motivo:</strong> {escape(inscripcion.motivo_retiro or '')}</p>"
                f"<p>Apruebe o rechace la solicitud desde la lista de postulantes.</p>")


def correo_retiro_resuelto(db: Session, inscripcion: Inscripcion, aprobado: bool, observacion: str = None):
    obs = f"<p><strong>Observación:</strong> {escape(observacion)}</p>" if observacion else ""
    texto = ("su retiro fue <strong>aprobado</strong>. Su inscripción quedó cerrada."
             if aprobado else "su solicitud de retiro fue <strong>rechazada</strong>. Su inscripción sigue vigente.")
    return _enviar(db, inscripcion.postulante, "RETIRO_RESUELTO",
                   "UIDE: Respuesta a su solicitud de retiro", "Solicitud de retiro",
                   f"<p>En <strong>{escape(inscripcion.convocatoria.nombre)}</strong>, {texto}</p>{obs}")


def correo_alerta_nueva(db: Session, inscripcion: Inscripcion, tutor: Usuario, motivos: list):
    lista = "".join(f"<li>{escape(m)}</li>" for m in motivos)
    return _enviar(db, tutor, "ALERTA_RIESGO",
                   f"UIDE: Alerta de riesgo - {inscripcion.postulante.nombre_completo}", "Nueva alerta de riesgo",
                   f"<p>Se detectó una alerta en <strong>{escape(inscripcion.postulante.nombre_completo)}</strong>:</p>"
                   f"<ul>{lista}</ul><p>Revise la pestaña <strong>Alertas</strong>. Puede resolverla o derivarla a coordinación.</p>")


def correo_alerta_derivada(db: Session, alerta, destinatario: Usuario, remitente: Usuario):
    insc = alerta.inscripcion
    return _enviar(db, destinatario, "ALERTA_DERIVADA",
                   f"UIDE: Alerta derivada - {insc.postulante.nombre_completo}", "Alerta derivada",
                   f"<p>{escape(remitente.nombre_completo)} le derivó una alerta de "
                   f"<strong>{escape(insc.postulante.nombre_completo)}</strong>:</p>"
                   f"<p>{escape(alerta.motivo_detallado)}</p>"
                   f"<p><strong>Nota:</strong> {escape(alerta.nota_derivacion or '')}</p>")


def correo_proceso_no_aprobado(db: Session, inscripcion: Inscripcion):
    conv = inscripcion.convocatoria
    pendientes = [a for a in inscripcion.asignaciones_cursos if a.estado_aprobacion != "APROBADO"]
    motivo = ""
    if not pendientes:
        motivo = "<p>Sus cursos estaban aprobados, pero la documentación obligatoria no se completó.</p>"
    cuerpo = (
        f"<p>La convocatoria <strong>{escape(conv.nombre)}</strong> finalizó y su proceso quedó como "
        f"<strong>no aprobado</strong>.</p>{motivo}<p>Resumen de sus cursos:</p>{_tabla_cursos(inscripcion)}"
        f"<p>Puede inscribirse en una próxima convocatoria cuando esté abierta.</p>"
    )
    return _enviar(db, inscripcion.postulante, "PROCESO_NO_APROBADO",
                   "UIDE: Resultado del curso preparatorio", "Resultado del preparatorio", cuerpo)


def correo_tutor_curso(db: Session, curso):
    """Al tutor nuevo del curso, y a los postulantes del curso para que sepan quién les acompaña."""
    tutor = curso.tutor
    programa = curso.convocatoria.programa.nombre
    _enviar(db, tutor, "TUTOR_ASIGNADO",
            f"UIDE: Tutor(a) del curso {curso.nombre}", "Nuevo curso a su cargo",
            f"<p>Se le asignó como tutor(a) del curso <strong>{escape(curso.nombre)}</strong> "
            f"de <strong>{escape(programa)}</strong>.</p>")
    for asig in curso.asignaciones:
        postulante = asig.inscripcion.postulante
        if asig.inscripcion.estado_proceso in ("APROBADO", "NO_APROBADO", "RETIRADO"):
            continue
        _enviar(db, postulante, "TUTOR_ASIGNADO",
                f"UIDE: Su tutor(a) de {curso.nombre}", "Tutor asignado",
                f"<p>Su tutor(a) del curso <strong>{escape(curso.nombre)}</strong> es "
                f"<strong>{escape(tutor.nombre_completo)}</strong> ({escape(tutor.email)}).</p>")


def correo_certificado_emitido(db: Session, asig):
    if asig.curso.tutor:
        _enviar(db, asig.curso.tutor, "CERTIFICADO_POR_VERIFICAR",
                f"Certificado por verificar: {asig.inscripcion.postulante.nombre_completo}", "Certificado por verificar",
                f"<p><strong>{escape(asig.inscripcion.postulante.nombre_completo)}</strong> aprobó "
                f"<strong>{escape(asig.curso.nombre)}</strong> con {float(asig.nota_final or 0):g}/100. "
                "Verifique su certificado en la sección Certificados para que cuente en el avance de la maestría.</p>")
    return _enviar(db, asig.inscripcion.postulante, "CERTIFICADO_EMITIDO",
                   f"UIDE: Aprobó {asig.curso.nombre}", "Curso aprobado",
                   f"<p>¡Felicitaciones! Aprobó el curso <strong>{escape(asig.curso.nombre)}</strong> con "
                   f"{float(asig.nota_final or 0):g}/100. Su certificado ya está en la sección <strong>Certificados</strong>; "
                   "su tutor(a) lo verificará para que cuente en el avance de la maestría.</p>")


def correo_certificado_revisado(db: Session, asig):
    if asig.certificado_estado == "APROBADO":
        cuerpo = (f"<p>Su tutor(a) verificó el certificado de <strong>{escape(asig.curso.nombre)}</strong>. "
                  "Ya cuenta en el avance de su maestría.</p>")
    else:
        cuerpo = (f"<p>Su tutor(a) devolvió el certificado de <strong>{escape(asig.curso.nombre)}</strong>.</p>"
                  f"<p><strong>Observación:</strong> {escape(asig.certificado_observacion or '')}</p>")
    return _enviar(db, asig.inscripcion.postulante, "CERTIFICADO_REVISADO",
                   f"UIDE: Certificado de {asig.curso.nombre}", "Certificado del curso", cuerpo)


def correo_documento_cargado(db: Session, inscripcion: Inscripcion, nombre_requisito: str, archivo: str):
    return _enviar(db, inscripcion.postulante, "DOCUMENTO_CARGADO",
                   f"UIDE: Documento recibido - {nombre_requisito}", "Documento recibido",
                   f"<p>Recibimos su documento <strong>{escape(nombre_requisito)}</strong> "
                   f"({escape(archivo)}). Coordinación lo revisará y le notificaremos el resultado.</p>")


def correo_documento_revisado(db: Session, inscripcion: Inscripcion, nombre_requisito: str, estado: str, observaciones: str = None):
    resultado = {"APROBADO": "aprobado", "REQUIERE_CORRECCION": "requiere corrección", "RECHAZADO": "rechazado"}.get(estado, estado)
    obs = f"<p><strong>Observaciones:</strong> {escape(observaciones)}</p>" if observaciones else ""
    if estado == "APROBADO":
        accion = ""
    elif estado == "RECHAZADO":
        accion = "<p>El rechazo es definitivo: este documento ya no admite otra versión. Comuníquese con coordinación si tiene dudas.</p>"
    else:
        accion = "<p>Ingrese a <strong>Mi perfil</strong> para cargar el documento corregido.</p>"
    return _enviar(db, inscripcion.postulante, "DOCUMENTO_REVISADO",
                   f"UIDE: Documento {resultado} - {nombre_requisito}", "Revisión de documento",
                   f"<p>Su documento <strong>{escape(nombre_requisito)}</strong> fue <strong>{resultado}</strong>.</p>{obs}{accion}")
