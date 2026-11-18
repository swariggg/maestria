-- ============================================================================
-- APP - Maestría: Sistema de Gestión de Cursos Preparatorios (UIDE)
-- Script DDL: Creación de Esquema de Base de Datos
-- Motor: Microsoft SQL Server 2022 / 2025
-- ============================================================================

IF DB_ID('app_maestria') IS NULL
    CREATE DATABASE app_maestria;
GO

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

-- Campos de seguimiento agregados después de la primera versión.
-- Cada bloque revisa si la columna ya existe, así el script se puede volver a correr sin borrar datos.
IF COL_LENGTH('seguimientos_postulante', 'numero_seguimiento') IS NULL
    ALTER TABLE seguimientos_postulante ADD numero_seguimiento INT NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'observaciones') IS NULL
    ALTER TABLE seguimientos_postulante ADD observaciones NVARCHAR(MAX) NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'recomendaciones') IS NULL
    ALTER TABLE seguimientos_postulante ADD recomendaciones NVARCHAR(MAX) NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'evidencia_nombre_original') IS NULL
    ALTER TABLE seguimientos_postulante ADD evidencia_nombre_original NVARCHAR(255) NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'evidencia_ruta_privada') IS NULL
    ALTER TABLE seguimientos_postulante ADD evidencia_ruta_privada NVARCHAR(500) NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'evidencia_mime_type') IS NULL
    ALTER TABLE seguimientos_postulante ADD evidencia_mime_type NVARCHAR(100) NULL;
GO
IF COL_LENGTH('seguimientos_postulante', 'evidencia_hash_sha256') IS NULL
    ALTER TABLE seguimientos_postulante ADD evidencia_hash_sha256 NVARCHAR(64) NULL;
GO

-- Numera los seguimientos que ya existían (1, 2, 3... por postulante, en orden de fecha)
UPDATE s SET numero_seguimiento = n.numero
FROM seguimientos_postulante s
JOIN (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY inscripcion_id ORDER BY fecha_contacto, id) AS numero
    FROM seguimientos_postulante
) n ON n.id = s.id
WHERE s.numero_seguimiento IS NULL;
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

-- ============================================================================
-- Cambios de la ronda de reglas (16-nov-2026). Se pueden volver a correr sin borrar datos.
-- ============================================================================
IF COL_LENGTH('convocatorias', 'cupo_maximo') IS NULL
    ALTER TABLE convocatorias ADD cupo_maximo INT NOT NULL CONSTRAINT DF_conv_cupo DEFAULT 60;
GO
IF COL_LENGTH('convocatorias', 'modalidad') IS NULL
    ALTER TABLE convocatorias ADD modalidad NVARCHAR(20) NOT NULL CONSTRAINT DF_conv_modalidad DEFAULT 'EN_LINEA';
GO
IF COL_LENGTH('usuarios', 'debe_cambiar_password') IS NULL
    ALTER TABLE usuarios ADD debe_cambiar_password BIT NOT NULL CONSTRAINT DF_usr_cambiar DEFAULT 0;
GO
IF COL_LENGTH('usuarios', 'acepto_datos_en') IS NULL
    ALTER TABLE usuarios ADD acepto_datos_en DATETIME2 NULL;
GO
-- El pago y las becas se manejan fuera de la app: se quitan las columnas si una versión anterior las creó
IF OBJECT_ID('DF_insc_pago', 'D') IS NOT NULL ALTER TABLE inscripciones DROP CONSTRAINT DF_insc_pago;
IF OBJECT_ID('DF_insc_beca', 'D') IS NOT NULL ALTER TABLE inscripciones DROP CONSTRAINT DF_insc_beca;
GO
IF COL_LENGTH('inscripciones', 'estado_pago') IS NOT NULL ALTER TABLE inscripciones DROP COLUMN estado_pago;
IF COL_LENGTH('inscripciones', 'tiene_beca') IS NOT NULL ALTER TABLE inscripciones DROP COLUMN tiene_beca;
IF COL_LENGTH('inscripciones', 'porcentaje_beca') IS NOT NULL ALTER TABLE inscripciones DROP COLUMN porcentaje_beca;
GO
IF COL_LENGTH('inscripciones', 'requiere_adaptaciones') IS NULL
    ALTER TABLE inscripciones ADD requiere_adaptaciones BIT NOT NULL CONSTRAINT DF_insc_adapt DEFAULT 0;
GO
IF COL_LENGTH('inscripciones', 'nota_adaptaciones') IS NULL
    ALTER TABLE inscripciones ADD nota_adaptaciones NVARCHAR(500) NULL;
GO
IF COL_LENGTH('inscripciones', 'retiro_solicitado_en') IS NULL
    ALTER TABLE inscripciones ADD retiro_solicitado_en DATETIME2 NULL;
GO
IF COL_LENGTH('inscripciones', 'motivo_retiro') IS NULL
    ALTER TABLE inscripciones ADD motivo_retiro NVARCHAR(500) NULL;
GO
IF COL_LENGTH('inscripciones', 'estado_previo_cierre') IS NULL
    ALTER TABLE inscripciones ADD estado_previo_cierre NVARCHAR(30) NULL;
GO
IF COL_LENGTH('documentos_postulante', 'reabierto') IS NULL
    ALTER TABLE documentos_postulante ADD reabierto BIT NOT NULL CONSTRAINT DF_doc_reabierto DEFAULT 0;
GO
IF COL_LENGTH('evaluaciones_evidencia', 'motivo_recalificacion') IS NULL
    ALTER TABLE evaluaciones_evidencia ADD motivo_recalificacion NVARCHAR(500) NULL;
GO
IF COL_LENGTH('alertas_riesgo', 'bloquea_reapertura') IS NULL
    ALTER TABLE alertas_riesgo ADD bloquea_reapertura BIT NOT NULL CONSTRAINT DF_ar_bloquea DEFAULT 0;
GO
IF COL_LENGTH('alertas_riesgo', 'derivada_a') IS NULL
    ALTER TABLE alertas_riesgo ADD derivada_a INT NULL;
GO
IF COL_LENGTH('alertas_riesgo', 'nota_derivacion') IS NULL
    ALTER TABLE alertas_riesgo ADD nota_derivacion NVARCHAR(500) NULL;
GO
IF COL_LENGTH('alertas_riesgo', 'fecha_derivacion') IS NULL
    ALTER TABLE alertas_riesgo ADD fecha_derivacion DATETIME2 NULL;
GO

-- 30. Programas en los que puede trabajar cada tutor
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tutores_programa')
BEGIN
    CREATE TABLE tutores_programa (
        id INT IDENTITY(1,1) PRIMARY KEY,
        tutor_id INT NOT NULL,
        programa_id INT NOT NULL,
        activo BIT NOT NULL DEFAULT 1,
        asignado_en DATETIME2 DEFAULT SYSDATETIME(),
        asignado_por INT NULL,
        CONSTRAINT FK_tp_tutor FOREIGN KEY (tutor_id) REFERENCES usuarios(id),
        CONSTRAINT FK_tp_programa FOREIGN KEY (programa_id) REFERENCES programas(id)
    );
END
GO

-- 31. Materiales y sesiones en vivo de cada curso
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'materiales_curso')
BEGIN
    CREATE TABLE materiales_curso (
        id INT IDENTITY(1,1) PRIMARY KEY,
        curso_id INT NOT NULL,
        tipo NVARCHAR(20) NOT NULL, -- ARCHIVO, ENLACE, SESION
        titulo NVARCHAR(200) NOT NULL,
        descripcion NVARCHAR(1000) NULL,
        url NVARCHAR(1000) NULL,
        fecha_sesion DATETIME2 NULL,
        nombre_original NVARCHAR(255) NULL,
        ruta_privada NVARCHAR(500) NULL,
        mime_type NVARCHAR(100) NULL,
        subido_por INT NOT NULL,
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_mc_curso FOREIGN KEY (curso_id) REFERENCES cursos_preparatorios(id),
        CONSTRAINT FK_mc_usuario FOREIGN KEY (subido_por) REFERENCES usuarios(id)
    );
END
GO

-- 32. Puntaje por criterio de la rúbrica
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'puntajes_criterio')
BEGIN
    CREATE TABLE puntajes_criterio (
        id INT IDENTITY(1,1) PRIMARY KEY,
        evaluacion_id INT NOT NULL,
        criterio_id INT NOT NULL,
        puntaje DECIMAL(5,2) NOT NULL,
        CONSTRAINT FK_pc_evaluacion FOREIGN KEY (evaluacion_id) REFERENCES evaluaciones_evidencia(id),
        CONSTRAINT FK_pc_criterio FOREIGN KEY (criterio_id) REFERENCES criterios_evaluacion(id)
    );
END
GO

-- 33. Un tutor por curso preparatorio (obligatorio para abrir la convocatoria)
IF COL_LENGTH('cursos_preparatorios', 'tutor_id') IS NULL
    ALTER TABLE cursos_preparatorios ADD tutor_id INT NULL CONSTRAINT FK_curso_tutor FOREIGN KEY REFERENCES usuarios(id);
GO

-- 34. Plantillas de actividad por programa (las deja el coordinador para los tutores)
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'plantillas_actividad')
BEGIN
    CREATE TABLE plantillas_actividad (
        id INT IDENTITY(1,1) PRIMARY KEY,
        programa_id INT NOT NULL,
        titulo NVARCHAR(200) NOT NULL,
        tipo NVARCHAR(50) NOT NULL DEFAULT 'ASIGNACION', -- ASIGNACION, PRUEBA, PROYECTO
        instrucciones NVARCHAR(MAX) NULL,
        ponderacion DECIMAL(5,2) NOT NULL,
        es_obligatorio BIT NOT NULL DEFAULT 1,
        extensiones_permitidas NVARCHAR(100) NOT NULL DEFAULT 'pdf,docx',
        tamano_max_mb INT NOT NULL DEFAULT 25,
        max_reenvios INT NOT NULL DEFAULT 3,
        activo BIT NOT NULL DEFAULT 1,
        creado_por INT NULL,
        creado_en DATETIME2 DEFAULT SYSDATETIME(),
        CONSTRAINT FK_pa_programa FOREIGN KEY (programa_id) REFERENCES programas(id),
        CONSTRAINT FK_pa_usuario FOREIGN KEY (creado_por) REFERENCES usuarios(id)
    );
END
GO

-- Tipos de actividad: asignación (4 pts), prueba (6 pts) o proyecto
UPDATE actividades_curso SET tipo = 'ASIGNACION' WHERE tipo = 'INDIVIDUAL';
GO

-- 35. Certificado de cada curso: se emite al aprobarlo y el tutor lo verifica
IF COL_LENGTH('asignaciones_curso', 'certificado_estado') IS NULL
    ALTER TABLE asignaciones_curso ADD certificado_estado NVARCHAR(20) NULL; -- PENDIENTE, APROBADO, DEVUELTO
IF COL_LENGTH('asignaciones_curso', 'certificado_emitido_en') IS NULL
    ALTER TABLE asignaciones_curso ADD certificado_emitido_en DATETIME2 NULL;
IF COL_LENGTH('asignaciones_curso', 'certificado_revisado_por') IS NULL
    ALTER TABLE asignaciones_curso ADD certificado_revisado_por INT NULL CONSTRAINT FK_ac_cert_revisor FOREIGN KEY REFERENCES usuarios(id);
IF COL_LENGTH('asignaciones_curso', 'certificado_revisado_en') IS NULL
    ALTER TABLE asignaciones_curso ADD certificado_revisado_en DATETIME2 NULL;
IF COL_LENGTH('asignaciones_curso', 'certificado_observacion') IS NULL
    ALTER TABLE asignaciones_curso ADD certificado_observacion NVARCHAR(500) NULL;
GO
-- Los cursos que ya estaban aprobados quedan con su certificado pendiente de verificación
-- (si el proceso ya estaba aprobado, se dan por verificados)
UPDATE ac SET ac.certificado_estado = CASE WHEN i.estado_proceso = 'APROBADO' THEN 'APROBADO' ELSE 'PENDIENTE' END,
              ac.certificado_emitido_en = SYSDATETIME()
FROM asignaciones_curso ac JOIN inscripciones i ON i.id = ac.inscripcion_id
WHERE ac.estado_aprobacion = 'APROBADO' AND ac.certificado_estado IS NULL;
GO

-- 36. Avisos dentro de la app (campana): mientras no haya conexión con Outlook no se envían correos
IF COL_LENGTH('notificaciones_cola', 'leida') IS NULL
    ALTER TABLE notificaciones_cola ADD leida BIT NOT NULL CONSTRAINT DF_nc_leida DEFAULT 0;
IF COL_LENGTH('notificaciones_cola', 'fecha_lectura') IS NULL
    ALTER TABLE notificaciones_cola ADD fecha_lectura DATETIME2 NULL;
GO

-- 37. Perfil: foto, fecha de nacimiento, enlaces y datos de contacto del tutor
IF COL_LENGTH('usuarios', 'foto_ruta') IS NULL
    ALTER TABLE usuarios ADD foto_ruta NVARCHAR(500) NULL;
IF COL_LENGTH('usuarios', 'foto_mime') IS NULL
    ALTER TABLE usuarios ADD foto_mime NVARCHAR(50) NULL;
IF COL_LENGTH('perfiles_postulante', 'fecha_nacimiento') IS NULL
    ALTER TABLE perfiles_postulante ADD fecha_nacimiento DATE NULL;
IF COL_LENGTH('perfiles_postulante', 'enlaces') IS NULL
    ALTER TABLE perfiles_postulante ADD enlaces NVARCHAR(500) NULL;
IF COL_LENGTH('tutores', 'correo_outlook') IS NULL
    ALTER TABLE tutores ADD correo_outlook NVARCHAR(150) NULL;
IF COL_LENGTH('tutores', 'usuario_teams') IS NULL
    ALTER TABLE tutores ADD usuario_teams NVARCHAR(150) NULL;
IF COL_LENGTH('tutores', 'horario_atencion') IS NULL
    ALTER TABLE tutores ADD horario_atencion NVARCHAR(300) NULL;
IF COL_LENGTH('tutores', 'presentacion') IS NULL
    ALTER TABLE tutores ADD presentacion NVARCHAR(1000) NULL;
GO

-- 38. Seguimiento: dato de contacto usado (número, correo o cuenta de Teams)
IF COL_LENGTH('seguimientos_postulante', 'dato_contacto') IS NULL
    ALTER TABLE seguimientos_postulante ADD dato_contacto NVARCHAR(150) NULL;
GO

PRINT N'Esquema completo de APP - Maestría creado exitosamente en app_maestria.';
