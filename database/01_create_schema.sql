-- ============================================================================
-- APP - Maestría: Sistema de Gestión de Cursos Preparatorios (UIDE)
-- Script DDL: Creación de Esquema de Base de Datos
-- Motor: Microsoft SQL Server 2022 / 2025
-- ============================================================================

USE app_maestria;
GO

-- 1. Tabla de Roles del Sistema
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'roles')
BEGIN
    CREATE TABLE roles (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo NVARCHAR(50) NOT NULL UNIQUE,
        nombre NVARCHAR(100) NOT NULL,
        descripcion NVARCHAR(255) NULL,
        creado_en DATETIME2 DEFAULT SYSDATETIME()
    );
END
GO

-- 2. Tabla de Usuarios
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'usuarios')
BEGIN
    CREATE TABLE usuarios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        email NVARCHAR(150) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        nombre_completo NVARCHAR(200) NOT NULL,
        cedula NVARCHAR(20) NOT NULL UNIQUE,
        telefono NVARCHAR(30) NULL,
        rol_id INT NOT NULL,
        estado NVARCHAR(20) NOT NULL DEFAULT 'ACTIVO', -- ACTIVO, INACTIVO, BLOQUEADO
        intentos_fallidos INT NOT NULL DEFAULT 0,
        fecha_bloqueo DATETIME2 NULL,
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        actualizado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_usuarios_roles FOREIGN KEY (rol_id) REFERENCES roles(id)
    );
    CREATE INDEX IX_usuarios_email ON usuarios(email);
    CREATE INDEX IX_usuarios_cedula ON usuarios(cedula);
END
GO

-- 3. Programas de Maestría
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'programas')
BEGIN
    CREATE TABLE programas (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo NVARCHAR(50) NOT NULL UNIQUE,
        nombre NVARCHAR(250) NOT NULL,
        descripcion NVARCHAR(MAX) NULL,
        estado NVARCHAR(20) NOT NULL DEFAULT 'ACTIVO', -- ACTIVO, INACTIVO
        creado_por INT NULL,
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        actualizado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_programas_creador FOREIGN KEY (creado_por) REFERENCES usuarios(id)
    );
END
GO

-- 4. Asignación de Coordinador a Programas (Alcance ABAC)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'coordinadores_programa')
BEGIN
    CREATE TABLE coordinadores_programa (
        id INT IDENTITY(1,1) PRIMARY KEY,
        programa_id INT NOT NULL,
        coordinador_id INT NOT NULL,
        activo BIT NOT NULL DEFAULT 1,
        asignado_en DATETIME2 DEFAULT SYSDATETIME(),
        asignado_por INT NULL,
        CONSTRAINT FK_cp_programa FOREIGN KEY (programa_id) REFERENCES programas(id),
        CONSTRAINT FK_cp_coordinador FOREIGN KEY (coordinador_id) REFERENCES usuarios(id),
        CONSTRAINT UQ_coordinador_programa UNIQUE (programa_id, coordinador_id)
    );
END
GO

-- 5. Convocatorias
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'convocatorias')
BEGIN
    CREATE TABLE convocatorias (
        id INT IDENTITY(1,1) PRIMARY KEY,
        programa_id INT NOT NULL,
        codigo NVARCHAR(50) NOT NULL,
        nombre NVARCHAR(200) NOT NULL,
        fecha_apertura DATE NOT NULL,
        fecha_cierre DATE NOT NULL,
        fecha_inicio_preparatorio DATE NOT NULL,
        fecha_fin_preparatorio DATE NOT NULL,
        estado NVARCHAR(20) NOT NULL DEFAULT 'PLANIFICADA', -- PLANIFICADA, ABIERTA, EN_CURSO, CERRADA, FINALIZADA
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_convocatorias_programa FOREIGN KEY (programa_id) REFERENCES programas(id),
        CONSTRAINT UQ_convocatoria_codigo UNIQUE (programa_id, codigo)
    );
    CREATE INDEX IX_convocatorias_fechas ON convocatorias(fecha_apertura, fecha_cierre);
END
GO

-- 6. Requisitos Documentales por Convocatoria
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'requisitos_convocatoria')
BEGIN
    CREATE TABLE requisitos_convocatoria (
        id INT IDENTITY(1,1) PRIMARY KEY,
        convocatoria_id INT NOT NULL,
        nombre NVARCHAR(150) NOT NULL,
        descripcion NVARCHAR(500) NULL,
        es_obligatorio BIT NOT NULL DEFAULT 1,
        formato_permitido NVARCHAR(100) NOT NULL DEFAULT 'pdf', -- 'pdf,jpg,png'
        tamano_max_mb INT NOT NULL DEFAULT 10,
        CONSTRAINT FK_req_convocatoria FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id)
    );
END
GO

-- 7. Cursos Preparatorios
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'cursos_preparatorios')
BEGIN
    CREATE TABLE cursos_preparatorios (
        id INT IDENTITY(1,1) PRIMARY KEY,
        convocatoria_id INT NOT NULL,
        codigo NVARCHAR(50) NOT NULL,
        nombre NVARCHAR(200) NOT NULL,
        descripcion NVARCHAR(MAX) NULL,
        nota_minima DECIMAL(5,2) NOT NULL DEFAULT 70.00,
        ponderacion_total DECIMAL(5,2) NOT NULL DEFAULT 100.00,
        estado NVARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_cursos_convocatoria FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id),
        CONSTRAINT UQ_curso_codigo UNIQUE (convocatoria_id, codigo)
    );
END
GO

-- 8. Actividades y Proyectos del Curso
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'actividades_curso')
BEGIN
    CREATE TABLE actividades_curso (
        id INT IDENTITY(1,1) PRIMARY KEY,
        curso_id INT NOT NULL,
        titulo NVARCHAR(200) NOT NULL,
        tipo NVARCHAR(50) NOT NULL DEFAULT 'INDIVIDUAL', -- INDIVIDUAL, PROYECTO
        instrucciones NVARCHAR(MAX) NULL,
        fecha_apertura DATETIME2 NOT NULL,
        fecha_limite DATETIME2 NOT NULL,
        ponderacion DECIMAL(5,2) NOT NULL DEFAULT 0.00,
        es_obligatorio BIT NOT NULL DEFAULT 1,
        extensiones_permitidas NVARCHAR(100) NOT NULL DEFAULT 'pdf,zip,docx',
        tamano_max_mb INT NOT NULL DEFAULT 25,
        max_reenvios INT NOT NULL DEFAULT 3,
        estado NVARCHAR(20) NOT NULL DEFAULT 'ACTIVO',
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_actividades_curso FOREIGN KEY (curso_id) REFERENCES cursos_preparatorios(id)
    );
    CREATE INDEX IX_actividades_fechas ON actividades_curso(fecha_limite);
END
GO

-- 9. Criterios de Evaluación
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'criterios_evaluacion')
BEGIN
    CREATE TABLE criterios_evaluacion (
        id INT IDENTITY(1,1) PRIMARY KEY,
        actividad_id INT NOT NULL,
        criterio NVARCHAR(250) NOT NULL,
        puntaje_maximo DECIMAL(5,2) NOT NULL,
        orden INT NOT NULL DEFAULT 1,
        CONSTRAINT FK_criterios_actividad FOREIGN KEY (actividad_id) REFERENCES actividades_curso(id)
    );
END
GO

-- 10. Perfiles de Postulante
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'perfiles_postulante')
BEGIN
    CREATE TABLE perfiles_postulante (
        id INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id INT NOT NULL UNIQUE,
        direccion NVARCHAR(255) NULL,
        ciudad NVARCHAR(100) NULL,
        pais NVARCHAR(100) NOT NULL DEFAULT 'Ecuador',
        titulo_tercer_nivel NVARCHAR(200) NULL,
        universidad_origen NVARCHAR(200) NULL,
        registrado_senescyt BIT NOT NULL DEFAULT 1,
        contacto_emergencia NVARCHAR(150) NULL,
        telefono_emergencia NVARCHAR(30) NULL,
        CONSTRAINT FK_perfil_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
END
GO

-- 11. Inscripciones a Convocatorias
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'inscripciones')
BEGIN
    CREATE TABLE inscripciones (
        id INT IDENTITY(1,1) PRIMARY KEY,
        postulante_id INT NOT NULL, -- FK usuarios
        convocatoria_id INT NOT NULL,
        fecha_inscripcion DATETIME2 DEFAULT SYSDATETIME(),
        estado_proceso NVARCHAR(30) NOT NULL DEFAULT 'REGISTRADO', 
        -- REGISTRADO, DOCUMENTACION_COMPLETA, EN_CURSO, APROBADO, REPROBADO, RETIRADO
        nivel_riesgo NVARCHAR(20) NOT NULL DEFAULT 'BAJO', -- BAJO, MEDIO, ALTO
        motivo_riesgo NVARCHAR(500) NULL,
        fecha_ultimo_avance DATETIME2 DEFAULT SYSDATETIME(),
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        actualizado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_inscripcion_postulante FOREIGN KEY (postulante_id) REFERENCES usuarios(id),
        CONSTRAINT FK_inscripcion_convocatoria FOREIGN KEY (convocatoria_id) REFERENCES convocatorias(id),
        CONSTRAINT UQ_postulante_convocatoria UNIQUE (postulante_id, convocatoria_id)
    );
    CREATE INDEX IX_inscripciones_riesgo ON inscripciones(nivel_riesgo, estado_proceso);
END
GO

-- 12. Documentos Requeridos Cargados por el Postulante
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'documentos_postulante')
BEGIN
    CREATE TABLE documentos_postulante (
        id INT IDENTITY(1,1) PRIMARY KEY,
        inscripcion_id INT NOT NULL,
        requisito_id INT NOT NULL,
        nombre_original NVARCHAR(255) NOT NULL,
        nombre_seguro NVARCHAR(255) NOT NULL,
        ruta_privada NVARCHAR(500) NOT NULL,
        mime_type NVARCHAR(100) NOT NULL,
        tamano_bytes BIGINT NOT NULL,
        hash_sha256 NVARCHAR(64) NOT NULL,
        estado_revision NVARCHAR(30) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE, APROBADO, REQUIERE_CORRECCION, RECHAZADO
        observaciones NVARCHAR(1000) NULL,
        revisado_por INT NULL,
        fecha_revision DATETIME2 NULL,
        fecha_carga DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_doc_inscripcion FOREIGN KEY (inscripcion_id) REFERENCES inscripciones(id),
        CONSTRAINT FK_doc_requisito FOREIGN KEY (requisito_id) REFERENCES requisitos_convocatoria(id),
        CONSTRAINT FK_doc_revisor FOREIGN KEY (revisado_por) REFERENCES usuarios(id)
    );
END
GO

-- 13. Asignaciones de Cursos a Postulantes
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'asignaciones_curso')
BEGIN
    CREATE TABLE asignaciones_curso (
        id INT IDENTITY(1,1) PRIMARY KEY,
        inscripcion_id INT NOT NULL,
        curso_id INT NOT NULL,
        estado NVARCHAR(30) NOT NULL DEFAULT 'EN_CURSO', -- MATRICULADO, EN_CURSO, FINALIZADO
        nota_final DECIMAL(5,2) NULL,
        estado_aprobacion NVARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE, APROBADO, REPROBADO
        fecha_asignacion DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_ac_inscripcion FOREIGN KEY (inscripcion_id) REFERENCES inscripciones(id),
        CONSTRAINT FK_ac_curso FOREIGN KEY (curso_id) REFERENCES cursos_preparatorios(id),
        CONSTRAINT UQ_inscripcion_curso UNIQUE (inscripcion_id, curso_id)
    );
END
GO

-- 14. Perfil / Datos Adicionales de Tutores
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tutores')
BEGIN
    CREATE TABLE tutores (
        id INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id INT NOT NULL UNIQUE,
        especialidad NVARCHAR(150) NOT NULL,
        max_postulantes INT NOT NULL DEFAULT 30,
        activo BIT NOT NULL DEFAULT 1,
        CONSTRAINT FK_tutores_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
END
GO

-- 15. Asignación de Tutor al Postulante
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'asignaciones_tutor')
BEGIN
    CREATE TABLE asignaciones_tutor (
        id INT IDENTITY(1,1) PRIMARY KEY,
        inscripcion_id INT NOT NULL,
        tutor_id INT NOT NULL, -- FK usuarios
        coordinador_id INT NOT NULL, -- FK usuarios
        fecha_asignacion DATETIME2 DEFAULT SYSDATETIME(),
        estado NVARCHAR(20) NOT NULL DEFAULT 'ACTIVO', -- ACTIVO, REASIGNADO, FINALIZADO
        motivo_reasignacion NVARCHAR(255) NULL,
        CONSTRAINT FK_at_inscripcion FOREIGN KEY (inscripcion_id) REFERENCES inscripciones(id),
        CONSTRAINT FK_at_tutor FOREIGN KEY (tutor_id) REFERENCES usuarios(id),
        CONSTRAINT FK_at_coordinador FOREIGN KEY (coordinador_id) REFERENCES usuarios(id)
    );
    CREATE INDEX IX_asignaciones_tutor_activo ON asignaciones_tutor(tutor_id, estado);
END
GO

-- 16. Entregas de Evidencias (Contenedor general por actividad)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'entregas_evidencia')
BEGIN
    CREATE TABLE entregas_evidencia (
        id INT IDENTITY(1,1) PRIMARY KEY,
        asignacion_curso_id INT NOT NULL,
        actividad_id INT NOT NULL,
        estado_entrega NVARCHAR(30) NOT NULL DEFAULT 'PENDIENTE', 
        -- PENDIENTE, ENTREGADO, EN_REVISION, REQUIERE_CORRECCION, APROBADO, RECHAZADO
        numero_versiones INT NOT NULL DEFAULT 0,
        creada_en DATETIME2 DEFAULT SYSDATETIME(),
        actualizada_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_ee_asignacion FOREIGN KEY (asignacion_curso_id) REFERENCES asignaciones_curso(id),
        CONSTRAINT FK_ee_actividad FOREIGN KEY (actividad_id) REFERENCES actividades_curso(id),
        CONSTRAINT UQ_entrega_actividad UNIQUE (asignacion_curso_id, actividad_id)
    );
END
GO

-- 17. Versiones de Evidencias (Historial inmutable de entregas y reenvíos)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'versiones_evidencia')
BEGIN
    CREATE TABLE versiones_evidencia (
        id INT IDENTITY(1,1) PRIMARY KEY,
        entrega_id INT NOT NULL,
        numero_version INT NOT NULL,
        nombre_archivo_original NVARCHAR(255) NOT NULL,
        nombre_archivo_seguro NVARCHAR(255) NOT NULL,
        ruta_privada NVARCHAR(500) NOT NULL,
        tamano_bytes BIGINT NOT NULL,
        mime_type NVARCHAR(100) NOT NULL,
        hash_sha256 NVARCHAR(64) NOT NULL,
        es_tardia BIT NOT NULL DEFAULT 0,
        fecha_entrega DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_ve_entrega FOREIGN KEY (entrega_id) REFERENCES entregas_evidencia(id),
        CONSTRAINT UQ_version_entrega UNIQUE (entrega_id, numero_version)
    );
    CREATE INDEX IX_versiones_entrega_fecha ON versiones_evidencia(fecha_entrega);
END
GO

-- 18. Evaluaciones y Calificaciones de Evidencias
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'evaluaciones_evidencia')
BEGIN
    CREATE TABLE evaluaciones_evidencia (
        id INT IDENTITY(1,1) PRIMARY KEY,
        version_id INT NOT NULL UNIQUE,
        evaluador_id INT NOT NULL, -- FK usuarios (Tutor o Coordinador)
        puntaje_obtenido DECIMAL(5,2) NOT NULL,
        resultado NVARCHAR(30) NOT NULL, -- APROBADO, REQUIERE_CORRECCION, RECHAZADO
        observaciones NVARCHAR(MAX) NULL,
        recomendaciones NVARCHAR(MAX) NULL,
        fecha_evaluacion DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_eval_version FOREIGN KEY (version_id) REFERENCES versiones_evidencia(id),
        CONSTRAINT FK_eval_evaluador FOREIGN KEY (evaluador_id) REFERENCES usuarios(id)
    );
END
GO

-- 19. Seguimientos Realizados por Tutores
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'seguimientos_postulante')
BEGIN
    CREATE TABLE seguimientos_postulante (
        id INT IDENTITY(1,1) PRIMARY KEY,
        inscripcion_id INT NOT NULL,
        tutor_id INT NOT NULL, -- FK usuarios
        fecha_contacto DATETIME2 NOT NULL,
        tipo_contacto NVARCHAR(30) NOT NULL, 
        -- TELEFONO, CORREO, WHATSAPP, VIDEOCONFERENCIA, PRESENCIAL
        motivo NVARCHAR(200) NOT NULL,
        accion_realizada NVARCHAR(MAX) NOT NULL,
        resultado NVARCHAR(MAX) NOT NULL,
        respuesta_postulante NVARCHAR(MAX) NULL,
        hubo_respuesta BIT NOT NULL DEFAULT 1,
        proxima_accion NVARCHAR(255) NULL,
        fecha_proxima_accion DATETIME2 NULL,
        estado_caso NVARCHAR(30) NOT NULL DEFAULT 'ABIERTO', -- EN_PROCESO, RESUELTO, ESCALADO
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_seg_inscripcion FOREIGN KEY (inscripcion_id) REFERENCES inscripciones(id),
        CONSTRAINT FK_seg_tutor FOREIGN KEY (tutor_id) REFERENCES usuarios(id)
    );
    CREATE INDEX IX_seguimientos_inscripcion ON seguimientos_postulante(inscripcion_id, fecha_contacto);
END
GO

-- 20. Compromisos de Seguimiento
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'compromisos_seguimiento')
BEGIN
    CREATE TABLE compromisos_seguimiento (
        id INT IDENTITY(1,1) PRIMARY KEY,
        seguimiento_id INT NOT NULL,
        descripcion NVARCHAR(500) NOT NULL,
        fecha_compromiso DATE NOT NULL,
        cumplido BIT NOT NULL DEFAULT 0,
        fecha_cumplimiento DATETIME2 NULL,
        CONSTRAINT FK_comp_seguimiento FOREIGN KEY (seguimiento_id) REFERENCES seguimientos_postulante(id)
    );
END
GO

-- 21. Reglas de Riesgo Configurables
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'reglas_riesgo')
BEGIN
    CREATE TABLE reglas_riesgo (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo NVARCHAR(50) NOT NULL UNIQUE,
        nombre NVARCHAR(150) NOT NULL,
        descripcion NVARCHAR(500) NULL,
        dias_inactividad INT NOT NULL DEFAULT 7,
        intentos_contacto_sin_respuesta INT NOT NULL DEFAULT 2,
        activo BIT NOT NULL DEFAULT 1,
        parametros_json NVARCHAR(MAX) NULL,
        actualizado_en DATETIME2 DEFAULT SYSDATETIME()
    );
END
GO

-- 22. Historial de Alertas de Riesgo
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'alertas_riesgo')
BEGIN
    CREATE TABLE alertas_riesgo (
        id INT IDENTITY(1,1) PRIMARY KEY,
        inscripcion_id INT NOT NULL,
        tipo_alerta NVARCHAR(50) NOT NULL, -- INACTIVIDAD, CONTACTO_SIN_RESPUESTA, VENCIMIENTO_PROXIMO, REPROBACION
        nivel_riesgo NVARCHAR(20) NOT NULL, -- MEDIO, ALTO
        motivo_detallado NVARCHAR(MAX) NOT NULL,
        fecha_deteccion DATETIME2 DEFAULT SYSDATETIME(),
        resuelta BIT NOT NULL DEFAULT 0,
        fecha_resolucion DATETIME2 NULL,
        resuelta_por INT NULL,
        accion_tomada NVARCHAR(500) NULL,
        CONSTRAINT FK_ar_inscripcion FOREIGN KEY (inscripcion_id) REFERENCES inscripciones(id),
        CONSTRAINT FK_ar_resuelto_por FOREIGN KEY (resuelta_por) REFERENCES usuarios(id)
    );
    CREATE INDEX IX_alertas_activas ON alertas_riesgo(inscripcion_id, resuelta);
END
GO

-- 23. Plantillas de Notificación
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'plantillas_notificacion')
BEGIN
    CREATE TABLE plantillas_notificacion (
        id INT IDENTITY(1,1) PRIMARY KEY,
        codigo NVARCHAR(50) NOT NULL UNIQUE,
        asunto NVARCHAR(200) NOT NULL,
        cuerpo_html NVARCHAR(MAX) NOT NULL,
        cuerpo_texto NVARCHAR(MAX) NOT NULL,
        variables_esperadas NVARCHAR(255) NULL,
        activo BIT NOT NULL DEFAULT 1
    );
END
GO

-- 24. Cola y Registro de Notificaciones
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'notificaciones_cola')
BEGIN
    CREATE TABLE notificaciones_cola (
        id INT IDENTITY(1,1) PRIMARY KEY,
        destinatario_id INT NOT NULL,
        email_destinatario NVARCHAR(150) NOT NULL,
        tipo_evento NVARCHAR(50) NOT NULL,
        asunto NVARCHAR(200) NOT NULL,
        cuerpo_html NVARCHAR(MAX) NOT NULL,
        estado NVARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE, ENVIADO, FALLIDO
        intentos INT NOT NULL DEFAULT 0,
        fecha_creacion DATETIME2 DEFAULT SYSDATETIME(),
        fecha_ultimo_intento DATETIME2 NULL,
        CONSTRAINT FK_nc_destinatario FOREIGN KEY (destinatario_id) REFERENCES usuarios(id)
    );
    CREATE INDEX IX_notif_cola_estado ON notificaciones_cola(estado);
END
GO

-- 25. Registro de Intentos de Envío SMTP
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'registros_intento_envio')
BEGIN
    CREATE TABLE registros_intento_envio (
        id INT IDENTITY(1,1) PRIMARY KEY,
        notificacion_id INT NOT NULL,
        exito BIT NOT NULL,
        respuesta_smtp NVARCHAR(500) NULL,
        error_detalle NVARCHAR(MAX) NULL,
        fecha_intento DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_rie_notificacion FOREIGN KEY (notificacion_id) REFERENCES notificaciones_cola(id)
    );
END
GO

-- 26. Bitácora de Auditoría Inmutable
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'registros_auditoria')
BEGIN
    CREATE TABLE registros_auditoria (
        id BIGINT IDENTITY(1,1) PRIMARY KEY,
        usuario_id INT NULL,
        accion NVARCHAR(50) NOT NULL, -- LOGIN, LOGOUT, CREAR, ACTUALIZAR, ELIMINAR, DESCARGAR, EVALUAR
        entidad NVARCHAR(100) NOT NULL,
        entidad_id NVARCHAR(50) NULL,
        datos_anteriores_json NVARCHAR(MAX) NULL,
        datos_nuevos_json NVARCHAR(MAX) NULL,
        ip_origen NVARCHAR(50) NULL,
        correlacion_id NVARCHAR(100) NULL,
        fecha_creacion DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_ra_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
    CREATE INDEX IX_auditoria_entidad ON registros_auditoria(entidad, entidad_id);
    CREATE INDEX IX_auditoria_fecha ON registros_auditoria(fecha_creacion);
END
GO

-- 27. Parámetros de Configuración Global del Sistema
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'configuracion_sistema')
BEGIN
    CREATE TABLE configuracion_sistema (
        clave NVARCHAR(100) PRIMARY KEY,
        valor NVARCHAR(MAX) NOT NULL,
        descripcion NVARCHAR(255) NULL,
        categoria NVARCHAR(50) NOT NULL DEFAULT 'GENERAL',
        actualizado_en DATETIME2 DEFAULT SYSDATETIME(),
        actualizado_por INT NULL,
        CONSTRAINT FK_cs_usuario FOREIGN KEY (actualizado_por) REFERENCES usuarios(id)
    );
END
GO

-- 28. Registro de Ejecución de Tareas Automáticas (Jobs)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'registros_ejecucion_job')
BEGIN
    CREATE TABLE registros_ejecucion_job (
        id INT IDENTITY(1,1) PRIMARY KEY,
        nombre_job NVARCHAR(100) NOT NULL,
        fecha_inicio DATETIME2 NOT NULL,
        fecha_fin DATETIME2 NULL,
        estado NVARCHAR(20) NOT NULL, -- EJECUTANDO, COMPLETADO, FALLIDO
        resultado_json NVARCHAR(MAX) NULL,
        error_detalle NVARCHAR(MAX) NULL
    );
END
GO

-- 29. Registro de Adaptadores e Integraciones Simuladas (UIDE Mock)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'integraciones_simuladas')
BEGIN
    CREATE TABLE integraciones_simuladas (
        id INT IDENTITY(1,1) PRIMARY KEY,
        sistema_externo NVARCHAR(50) NOT NULL, -- SENESCYT, BANNER_UIDE, ACTIVE_DIRECTORY
        endpoint_simulado NVARCHAR(255) NOT NULL,
        payload_recibido_json NVARCHAR(MAX) NULL,
        respuesta_simulada_json NVARCHAR(MAX) NULL,
        codigo_estado INT NOT NULL DEFAULT 200,
        fecha_registro DATETIME2 DEFAULT SYSDATETIME()
    );
END
GO

PRINT 'Esquema completo de APP - Maestría creado exitosamente en app_maestria.';
