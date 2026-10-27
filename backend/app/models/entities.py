from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, Date, 
    Numeric, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base

class Rol(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(200), nullable=False)
    cedula = Column(String(20), unique=True, nullable=False, index=True)
    telefono = Column(String(30), nullable=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    estado = Column(String(20), default="ACTIVO") # ACTIVO, INACTIVO, BLOQUEADO
    intentos_fallidos = Column(Integer, default=0)
    fecha_bloqueo = Column(DateTime, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    perfil = relationship("PerfilPostulante", back_populates="usuario", uselist=False)
    tutor_perfil = relationship("Tutor", back_populates="usuario", uselist=False)
    coordinaciones = relationship("CoordinadorPrograma", back_populates="coordinador", foreign_keys="CoordinadorPrograma.coordinador_id")

class Programa(Base):
    __tablename__ = "programas"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(250), nullable=False)
    descripcion = Column(Text, nullable=True)
    estado = Column(String(20), default="ACTIVO")
    creado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    convocatorias = relationship("Convocatoria", back_populates="programa")
    coordinadores = relationship("CoordinadorPrograma", back_populates="programa")

class CoordinadorPrograma(Base):
    __tablename__ = "coordinadores_programa"
    id = Column(Integer, primary_key=True, index=True)
    programa_id = Column(Integer, ForeignKey("programas.id"), nullable=False)
    coordinador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    activo = Column(Boolean, default=True)
    asignado_en = Column(DateTime, default=datetime.utcnow)
    asignado_por = Column(Integer, nullable=True)

    programa = relationship("Programa", back_populates="coordinadores")
    coordinador = relationship("Usuario", foreign_keys=[coordinador_id], back_populates="coordinaciones")

class Convocatoria(Base):
    __tablename__ = "convocatorias"
    id = Column(Integer, primary_key=True, index=True)
    programa_id = Column(Integer, ForeignKey("programas.id"), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(200), nullable=False)
    fecha_apertura = Column(Date, nullable=False)
    fecha_cierre = Column(Date, nullable=False)
    fecha_inicio_preparatorio = Column(Date, nullable=False)
    fecha_fin_preparatorio = Column(Date, nullable=False)
    estado = Column(String(20), default="PLANIFICADA")
    creado_en = Column(DateTime, default=datetime.utcnow)

    programa = relationship("Programa", back_populates="convocatorias")
    requisitos = relationship("RequisitoConvocatoria", back_populates="convocatoria")
    cursos = relationship("CursoPreparatorio", back_populates="convocatoria")
    inscripciones = relationship("Inscripcion", back_populates="convocatoria")

class RequisitoConvocatoria(Base):
    __tablename__ = "requisitos_convocatoria"
    id = Column(Integer, primary_key=True, index=True)
    convocatoria_id = Column(Integer, ForeignKey("convocatorias.id"), nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)
    es_obligatorio = Column(Boolean, default=True)
    formato_permitido = Column(String(100), default="pdf")
    tamano_max_mb = Column(Integer, default=10)

    convocatoria = relationship("Convocatoria", back_populates="requisitos")

class CursoPreparatorio(Base):
    __tablename__ = "cursos_preparatorios"
    id = Column(Integer, primary_key=True, index=True)
    convocatoria_id = Column(Integer, ForeignKey("convocatorias.id"), nullable=False)
    codigo = Column(String(50), nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    nota_minima = Column(Numeric(5, 2), default=70.00)
    ponderacion_total = Column(Numeric(5, 2), default=100.00)
    estado = Column(String(20), default="ACTIVO")
    creado_en = Column(DateTime, default=datetime.utcnow)

    convocatoria = relationship("Convocatoria", back_populates="cursos")
    actividades = relationship("ActividadCurso", back_populates="curso")
    asignaciones = relationship("AsignacionCurso", back_populates="curso")

class ActividadCurso(Base):
    __tablename__ = "actividades_curso"
    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("cursos_preparatorios.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    tipo = Column(String(50), default="INDIVIDUAL") # INDIVIDUAL, PROYECTO
    instrucciones = Column(Text, nullable=True)
    fecha_apertura = Column(DateTime, nullable=False)
    fecha_limite = Column(DateTime, nullable=False)
    ponderacion = Column(Numeric(5, 2), default=0.00)
    es_obligatorio = Column(Boolean, default=True)
    extensiones_permitidas = Column(String(100), default="pdf,zip,docx")
    tamano_max_mb = Column(Integer, default=25)
    max_reenvios = Column(Integer, default=3)
    estado = Column(String(20), default="ACTIVO")
    creado_en = Column(DateTime, default=datetime.utcnow)

    curso = relationship("CursoPreparatorio", back_populates="actividades")
    criterios = relationship("CriterioEvaluacion", back_populates="actividad")
    entregas = relationship("EntregaEvidencia", back_populates="actividad")

class CriterioEvaluacion(Base):
    __tablename__ = "criterios_evaluacion"
    id = Column(Integer, primary_key=True, index=True)
    actividad_id = Column(Integer, ForeignKey("actividades_curso.id"), nullable=False)
    criterio = Column(String(250), nullable=False)
    puntaje_maximo = Column(Numeric(5, 2), nullable=False)
    orden = Column(Integer, default=1)

    actividad = relationship("ActividadCurso", back_populates="criterios")

class PerfilPostulante(Base):
    __tablename__ = "perfiles_postulante"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    direccion = Column(String(255), nullable=True)
    ciudad = Column(String(100), nullable=True)
    pais = Column(String(100), default="Ecuador")
    titulo_tercer_nivel = Column(String(200), nullable=True)
    universidad_origen = Column(String(200), nullable=True)
    registrado_senescyt = Column(Boolean, default=True)
    contacto_emergencia = Column(String(150), nullable=True)
    telefono_emergencia = Column(String(30), nullable=True)

    usuario = relationship("Usuario", back_populates="perfil")

class Inscripcion(Base):
    __tablename__ = "inscripciones"
    id = Column(Integer, primary_key=True, index=True)
    postulante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    convocatoria_id = Column(Integer, ForeignKey("convocatorias.id"), nullable=False)
    fecha_inscripcion = Column(DateTime, default=datetime.utcnow)
    estado_proceso = Column(String(30), default="REGISTRADO") 
    # REGISTRADO, DOCUMENTACION_PENDIENTE, DOCUMENTACION_COMPLETA, EN_CURSO, APROBADO, REPROBADO, RETIRADO
    nivel_riesgo = Column(String(20), default="BAJO") # BAJO, MEDIO, ALTO
    motivo_riesgo = Column(String(500), nullable=True)
    fecha_ultimo_avance = Column(DateTime, default=datetime.utcnow)
    creado_en = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    postulante = relationship("Usuario", foreign_keys=[postulante_id])
    convocatoria = relationship("Convocatoria", back_populates="inscripciones")
    documentos = relationship("DocumentoPostulante", back_populates="inscripcion")
    asignaciones_cursos = relationship("AsignacionCurso", back_populates="inscripcion")
    asignacion_tutor = relationship("AsignacionTutor", back_populates="inscripcion", uselist=False)
    seguimientos = relationship("SeguimientoPostulante", back_populates="inscripcion")
    alertas = relationship("AlertaRiesgo", back_populates="inscripcion")

class DocumentoPostulante(Base):
    __tablename__ = "documentos_postulante"
    id = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("inscripciones.id"), nullable=False)
    requisito_id = Column(Integer, ForeignKey("requisitos_convocatoria.id"), nullable=False)
    nombre_original = Column(String(255), nullable=False)
    nombre_seguro = Column(String(255), nullable=False)
    ruta_privada = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    tamano_bytes = Column(BigInteger, nullable=False)
    hash_sha256 = Column(String(64), nullable=False)
    estado_revision = Column(String(30), default="PENDIENTE") # PENDIENTE, APROBADO, REQUIERE_CORRECCION, RECHAZADO
    observaciones = Column(String(1000), nullable=True)
    revisado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha_revision = Column(DateTime, nullable=True)
    fecha_carga = Column(DateTime, default=datetime.utcnow)

    inscripcion = relationship("Inscripcion", back_populates="documentos")
    requisito = relationship("RequisitoConvocatoria")
    revisor = relationship("Usuario", foreign_keys=[revisado_por])

class AsignacionCurso(Base):
    __tablename__ = "asignaciones_curso"
    id = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("inscripciones.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos_preparatorios.id"), nullable=False)
    estado = Column(String(30), default="EN_CURSO")
    nota_final = Column(Numeric(5, 2), nullable=True)
    estado_aprobacion = Column(String(20), default="PENDIENTE") # PENDIENTE, APROBADO, REPROBADO
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)

    inscripcion = relationship("Inscripcion", back_populates="asignaciones_cursos")
    curso = relationship("CursoPreparatorio", back_populates="asignaciones")
    entregas = relationship("EntregaEvidencia", back_populates="asignacion_curso")

class Tutor(Base):
    __tablename__ = "tutores"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    especialidad = Column(String(150), nullable=False)
    max_postulantes = Column(Integer, default=30)
    activo = Column(Boolean, default=True)

    usuario = relationship("Usuario", back_populates="tutor_perfil")

class AsignacionTutor(Base):
    __tablename__ = "asignaciones_tutor"
    id = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("inscripciones.id"), nullable=False)
    tutor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    coordinador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_asignacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(20), default="ACTIVO") # ACTIVO, REASIGNADO, FINALIZADO
    motivo_reasignacion = Column(String(255), nullable=True)

    inscripcion = relationship("Inscripcion", back_populates="asignacion_tutor")
    tutor = relationship("Usuario", foreign_keys=[tutor_id])
    coordinador = relationship("Usuario", foreign_keys=[coordinador_id])

class EntregaEvidencia(Base):
    __tablename__ = "entregas_evidencia"
    id = Column(Integer, primary_key=True, index=True)
    asignacion_curso_id = Column(Integer, ForeignKey("asignaciones_curso.id"), nullable=False)
    actividad_id = Column(Integer, ForeignKey("actividades_curso.id"), nullable=False)
    estado_entrega = Column(String(30), default="PENDIENTE")
    # PENDIENTE, ENTREGADO, REVISADO, REQUIERE_CORRECCION, APROBADO, RECHAZADO
    numero_versiones = Column(Integer, default=0)
    creada_en = Column(DateTime, default=datetime.utcnow)
    actualizada_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asignacion_curso = relationship("AsignacionCurso", back_populates="entregas")
    actividad = relationship("ActividadCurso", back_populates="entregas")
    versiones = relationship("VersionEvidencia", back_populates="entrega", order_by="VersionEvidencia.numero_version")

class VersionEvidencia(Base):
    __tablename__ = "versiones_evidencia"
    id = Column(Integer, primary_key=True, index=True)
    entrega_id = Column(Integer, ForeignKey("entregas_evidencia.id"), nullable=False)
    numero_version = Column(Integer, nullable=False)
    nombre_archivo_original = Column(String(255), nullable=False)
    nombre_archivo_seguro = Column(String(255), nullable=False)
    ruta_privada = Column(String(500), nullable=False)
    tamano_bytes = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    hash_sha256 = Column(String(64), nullable=False)
    es_tardia = Column(Boolean, default=False)
    fecha_entrega = Column(DateTime, default=datetime.utcnow)

    entrega = relationship("EntregaEvidencia", back_populates="versiones")
    evaluacion = relationship("EvaluacionEvidencia", back_populates="version", uselist=False)

class EvaluacionEvidencia(Base):
    __tablename__ = "evaluaciones_evidencia"
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("versiones_evidencia.id"), unique=True, nullable=False)
    evaluador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    puntaje_obtenido = Column(Numeric(5, 2), nullable=False)
    resultado = Column(String(30), nullable=False) # APROBADO, REQUIERE_CORRECCION, RECHAZADO
    observaciones = Column(Text, nullable=True)
    recomendaciones = Column(Text, nullable=True)
    fecha_evaluacion = Column(DateTime, default=datetime.utcnow)

    version = relationship("VersionEvidencia", back_populates="evaluacion")
    evaluador = relationship("Usuario", foreign_keys=[evaluador_id])

class SeguimientoPostulante(Base):
    __tablename__ = "seguimientos_postulante"
    id = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("inscripciones.id"), nullable=False)
    tutor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha_contacto = Column(DateTime, nullable=False)
    tipo_contacto = Column(String(30), nullable=False)
    # TELEFONO, CORREO, WHATSAPP, VIDEOCONFERENCIA, PRESENCIAL
    motivo = Column(String(200), nullable=False)
    accion_realizada = Column(Text, nullable=False)
    resultado = Column(Text, nullable=False)
    respuesta_postulante = Column(Text, nullable=True)
    hubo_respuesta = Column(Boolean, default=True)
    proxima_accion = Column(String(255), nullable=True)
    fecha_proxima_accion = Column(DateTime, nullable=True)
    estado_caso = Column(String(30), default="ABIERTO") # ABIERTO, EN_PROCESO, RESUELTO, ESCALADO
    creado_en = Column(DateTime, default=datetime.utcnow)

    inscripcion = relationship("Inscripcion", back_populates="seguimientos")
    tutor = relationship("Usuario", foreign_keys=[tutor_id])
    compromisos = relationship("CompromisoSeguimiento", back_populates="seguimiento")

class CompromisoSeguimiento(Base):
    __tablename__ = "compromisos_seguimiento"
    id = Column(Integer, primary_key=True, index=True)
    seguimiento_id = Column(Integer, ForeignKey("seguimientos_postulante.id"), nullable=False)
    descripcion = Column(String(500), nullable=False)
    fecha_compromiso = Column(Date, nullable=False)
    cumplido = Column(Boolean, default=False)
    fecha_cumplimiento = Column(DateTime, nullable=True)

    seguimiento = relationship("SeguimientoPostulante", back_populates="compromisos")

class ReglaRiesgo(Base):
    __tablename__ = "reglas_riesgo"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)
    dias_inactividad = Column(Integer, default=7)
    intentos_contacto_sin_respuesta = Column(Integer, default=2)
    activo = Column(Boolean, default=True)
    parametros_json = Column(Text, nullable=True)
    actualizado_en = Column(DateTime, default=datetime.utcnow)

class AlertaRiesgo(Base):
    __tablename__ = "alertas_riesgo"
    id = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("inscripciones.id"), nullable=False)
    tipo_alerta = Column(String(50), nullable=False) # INACTIVIDAD, CONTACTO_SIN_RESPUESTA, VENCIMIENTO_PROXIMO, REPROBACION
    nivel_riesgo = Column(String(20), nullable=False) # MEDIO, ALTO
    motivo_detallado = Column(Text, nullable=False)
    fecha_deteccion = Column(DateTime, default=datetime.utcnow)
    resuelta = Column(Boolean, default=False)
    fecha_resolucion = Column(DateTime, nullable=True)
    resuelta_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    accion_tomada = Column(String(500), nullable=True)

    inscripcion = relationship("Inscripcion", back_populates="alertas")
    usuario_resolutor = relationship("Usuario", foreign_keys=[resuelta_por])

class PlantillaNotificacion(Base):
    __tablename__ = "plantillas_notificacion"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    asunto = Column(String(200), nullable=False)
    cuerpo_html = Column(Text, nullable=False)
    cuerpo_texto = Column(Text, nullable=False)
    variables_esperadas = Column(String(255), nullable=True)
    activo = Column(Boolean, default=True)

class NotificacionCola(Base):
    __tablename__ = "notificaciones_cola"
    id = Column(Integer, primary_key=True, index=True)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    email_destinatario = Column(String(150), nullable=False)
    tipo_evento = Column(String(50), nullable=False)
    asunto = Column(String(200), nullable=False)
    cuerpo_html = Column(Text, nullable=False)
    estado = Column(String(20), default="PENDIENTE") # PENDIENTE, ENVIADO, FALLIDO
    intentos = Column(Integer, default=0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_ultimo_intento = Column(DateTime, nullable=True)

    destinatario = relationship("Usuario", foreign_keys=[destinatario_id])

class RegistroIntentoEnvio(Base):
    __tablename__ = "registros_intento_envio"
    id = Column(Integer, primary_key=True, index=True)
    notificacion_id = Column(Integer, ForeignKey("notificaciones_cola.id"), nullable=False)
    exito = Column(Boolean, nullable=False)
    respuesta_smtp = Column(String(500), nullable=True)
    error_detalle = Column(Text, nullable=True)
    fecha_intento = Column(DateTime, default=datetime.utcnow)

class RegistroAuditoria(Base):
    __tablename__ = "registros_auditoria"
    id = Column(BigInteger, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    accion = Column(String(50), nullable=False)
    entidad = Column(String(100), nullable=False)
    entidad_id = Column(String(50), nullable=True)
    datos_anteriores_json = Column(Text, nullable=True)
    datos_nuevos_json = Column(Text, nullable=True)
    ip_origen = Column(String(50), nullable=True)
    correlacion_id = Column(String(100), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])

class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    clave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=False)
    descripcion = Column(String(255), nullable=True)
    categoria = Column(String(50), default="GENERAL")
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actualizado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

class RegistroEjecucionJob(Base):
    __tablename__ = "registros_ejecucion_job"
    id = Column(Integer, primary_key=True, index=True)
    nombre_job = Column(String(100), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(20), nullable=False) # EJECUTANDO, COMPLETADO, FALLIDO
    resultado_json = Column(Text, nullable=True)
    error_detalle = Column(Text, nullable=True)

class IntegracionSimulada(Base):
    __tablename__ = "integraciones_simuladas"
    id = Column(Integer, primary_key=True, index=True)
    sistema_externo = Column(String(50), nullable=False) # SENESCYT, BANNER_UIDE, ACTIVE_DIRECTORY
    endpoint_simulado = Column(String(255), nullable=False)
    payload_recibido_json = Column(Text, nullable=True)
    respuesta_simulada_json = Column(Text, nullable=True)
    codigo_estado = Column(Integer, default=200)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
