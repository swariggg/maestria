-- ============================================================================
-- APP - Maestría: Sistema de Gestión de Cursos Preparatorios (UIDE)
-- Script DML: Datos de Demostración y Configuración Inicial (Autónomo por Lote)
-- Las fechas se calculan a partir del día en que se ejecuta el script (GETDATE()),
-- para que la demostración se vea vigente sin importar cuándo se cargue la base.
-- ============================================================================

USE app_maestria;
GO

-- 1. Insertar Roles
IF NOT EXISTS (SELECT 1 FROM roles WHERE codigo = 'ADMIN')
BEGIN
    INSERT INTO roles (codigo, nombre, descripcion) VALUES
    ('ADMIN', 'Administrador Global', N'Control total administrativo, gestión de usuarios, auditoría y parámetros globales'),
    ('COORDINADOR', 'Coordinador de Programa', N'Gestión exclusiva de sus programas asignados, convocatorias, cursos, actividades y asignación de tutores'),
    ('TUTOR', N'Tutor Académico', N'Seguimiento y evaluación exclusiva de los postulantes que le han sido asignados'),
    ('POSTULANTE', N'Postulante a Maestría', 'Acceso a sus cursos asignados, entrega de evidencias, consulta de avance y notificaciones');
END
GO

-- 2. Insertar Usuarios
BEGIN
    DECLARE @RolAdmin INT = (SELECT id FROM roles WHERE codigo = 'ADMIN');
    DECLARE @RolCoord INT = (SELECT id FROM roles WHERE codigo = 'COORDINADOR');
    DECLARE @RolTutor INT = (SELECT id FROM roles WHERE codigo = 'TUTOR');
    DECLARE @RolPost INT = (SELECT id FROM roles WHERE codigo = 'POSTULANTE');
    DECLARE @PwdHash NVARCHAR(255) = '$2b$12$6Gq7NJGFZW47CU0MZOZ9duLQxWrEUcEtkmLyz4PWGYhjnKOwZzzRa'; -- Demo2026!

    -- Administrador
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'admin@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES ('admin@uide.edu.ec', @PwdHash, N'Dra. María Elena Ramos (Admin)', '1710000001', '0991112222', @RolAdmin, 'ACTIVO');
    END

    -- Coordinadores
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'coordinador.ia@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('coordinador.ia@uide.edu.ec', @PwdHash, 'Dr. Roberto Carlos Andrade (Coord. IA)', '1710000002', '0992223333', @RolCoord, 'ACTIVO'),
        ('coordinador.ciber@uide.edu.ec', @PwdHash, N'MSc. Gabriela Lucía Montalvo (Coord. Ciber)', '1710000003', '0993334444', @RolCoord, 'ACTIVO');
    END

    -- Tutores
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('tutor.ia@uide.edu.ec', @PwdHash, 'Ing. Carlos Patricio Viteri (Tutor IA)', '1710000004', '0994445555', @RolTutor, 'ACTIVO'),
        ('tutor.ciber@uide.edu.ec', @PwdHash, N'Ing. Andrea Sofía Benítez (Tutor Ciber)', '1710000005', '0995556666', @RolTutor, 'ACTIVO');
    END

    -- Postulantes
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('postulante.perez@uide.edu.ec', @PwdHash, N'Juan Sebastián Pérez Castro', '1711111111', '0981001001', @RolPost, 'ACTIVO'),
        ('postulante.morales@uide.edu.ec', @PwdHash, N'Ana María Morales Cevallos', '1711111112', '0982002002', @RolPost, 'ACTIVO'),
        ('postulante.zambrano@uide.edu.ec', @PwdHash, 'David Fernando Zambrano Loor', '1711111113', '0983003003', @RolPost, 'ACTIVO'),
        ('postulante.alvarado@uide.edu.ec', @PwdHash, 'Elena Patricia Alvarado Vega', '1711111114', '0984004004', @RolPost, 'ACTIVO');
    END
END
GO

-- 3. Registrar Perfil de Tutores
BEGIN
    DECLARE @IdTutor1 INT = (SELECT id FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec');
    DECLARE @IdTutor2 INT = (SELECT id FROM usuarios WHERE email = 'tutor.ciber@uide.edu.ec');

    IF NOT EXISTS (SELECT 1 FROM tutores WHERE usuario_id = @IdTutor1)
    BEGIN
        INSERT INTO tutores (usuario_id, especialidad, max_postulantes, activo)
        VALUES 
        (@IdTutor1, N'Machine Learning & Matemáticas Computacionales', 25, 1),
        (@IdTutor2, 'Ciberseguridad y Normativas ISO 27001', 20, 1);
    END
END
GO

-- 4. Registrar Perfiles de Postulantes
BEGIN
    DECLARE @IdPerez INT = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec');
    DECLARE @IdMorales INT = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec');
    DECLARE @IdZambrano INT = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec');
    DECLARE @IdAlvarado INT = (SELECT id FROM usuarios WHERE email = 'postulante.alvarado@uide.edu.ec');

    IF NOT EXISTS (SELECT 1 FROM perfiles_postulante WHERE usuario_id = @IdPerez)
    BEGIN
        INSERT INTO perfiles_postulante (usuario_id, direccion, ciudad, pais, titulo_tercer_nivel, universidad_origen, registrado_senescyt, contacto_emergencia, telefono_emergencia)
        VALUES
        (@IdPerez, 'Av. 6 de Diciembre y Orellana', 'Quito', 'Ecuador', 'Ingeniero en Sistemas', 'EPN', 1, 'Rosa Castro (Madre)', '0990001111'),
        (@IdMorales, 'Calle Los Guayacanes 145', 'Guayaquil', 'Ecuador', N'Licenciada en Computación', 'ESPOL', 1, 'Marco Morales (Padre)', '0990002222'),
        (@IdZambrano, 'Av. Amazonas N24-10', 'Quito', 'Ecuador', N'Ingeniero en Electrónica', 'UIDE', 1, 'Lorena Loor (Esposa)', '0990003333'),
        (@IdAlvarado, 'Av. Remigio Crespo 402', 'Cuenca', 'Ecuador', 'Ingeniera de Software', 'Universidad de Cuenca', 1, 'Pedro Alvarado (Hermano)', '0990004444');
    END
END
GO

-- 5. Programas de Maestría
BEGIN
    DECLARE @IdAdmin INT = (SELECT id FROM usuarios WHERE email = 'admin@uide.edu.ec');
    IF NOT EXISTS (SELECT 1 FROM programas WHERE codigo = 'MIA-01')
    BEGIN
        INSERT INTO programas (codigo, nombre, descripcion, estado, creado_por)
        VALUES 
        ('MIA-01', N'Maestría en Inteligencia Artificial Aplicada', N'Programa de posgrado enfocado en modelos predictivos, deep learning y visión artificial.', 'ACTIVO', @IdAdmin),
        ('MCG-01', N'Maestría en Ciberseguridad y Gestión de Riesgos', N'Especialización en defensa perimetral, respuesta a incidentes y cumplimiento normativo.', 'ACTIVO', @IdAdmin);
    END
END
GO

-- 6. Asignación de Coordinador a Programas
BEGIN
    DECLARE @IdProgIA INT = (SELECT id FROM programas WHERE codigo = 'MIA-01');
    DECLARE @IdProgCiber INT = (SELECT id FROM programas WHERE codigo = 'MCG-01');
    DECLARE @IdCoordIA INT = (SELECT id FROM usuarios WHERE email = 'coordinador.ia@uide.edu.ec');
    DECLARE @IdCoordCiber INT = (SELECT id FROM usuarios WHERE email = 'coordinador.ciber@uide.edu.ec');

    IF NOT EXISTS (SELECT 1 FROM coordinadores_programa WHERE programa_id = @IdProgIA AND coordinador_id = @IdCoordIA)
    BEGIN
        INSERT INTO coordinadores_programa (programa_id, coordinador_id, activo)
        VALUES 
        (@IdProgIA, @IdCoordIA, 1),
        (@IdProgCiber, @IdCoordCiber, 1);
    END
END
GO

-- 7. Convocatorias
BEGIN
    DECLARE @IdProgIA2 INT = (SELECT id FROM programas WHERE codigo = 'MIA-01');
    DECLARE @IdProgCiber2 INT = (SELECT id FROM programas WHERE codigo = 'MCG-01');

    IF NOT EXISTS (SELECT 1 FROM convocatorias WHERE codigo = 'CONV-2026-1')
    BEGIN
        INSERT INTO convocatorias (programa_id, codigo, nombre, fecha_apertura, fecha_cierre, fecha_inicio_preparatorio, fecha_fin_preparatorio, estado)
        VALUES 
        (@IdProgIA2, 'CONV-2026-1', 'Convocatoria IA Cohorte I - 2026', CAST(DATEADD(DAY, -60, GETDATE()) AS DATE), CAST(DATEADD(DAY, 30, GETDATE()) AS DATE), CAST(DATEADD(DAY, -30, GETDATE()) AS DATE), CAST(DATEADD(DAY, 50, GETDATE()) AS DATE), 'EN_CURSO'),
        (@IdProgCiber2, 'CONV-2026-CIBER', 'Convocatoria Ciberseguridad Cohorte I - 2026', CAST(DATEADD(DAY, -45, GETDATE()) AS DATE), CAST(DATEADD(DAY, 40, GETDATE()) AS DATE), CAST(DATEADD(DAY, -15, GETDATE()) AS DATE), CAST(DATEADD(DAY, 55, GETDATE()) AS DATE), 'EN_CURSO');
    END
END
GO

-- 8. Requisitos Documentales
BEGIN
    DECLARE @IdConvIA INT = (SELECT id FROM convocatorias WHERE codigo = 'CONV-2026-1');
    IF NOT EXISTS (SELECT 1 FROM requisitos_convocatoria WHERE convocatoria_id = @IdConvIA)
    BEGIN
        INSERT INTO requisitos_convocatoria (convocatoria_id, nombre, descripcion, es_obligatorio, formato_permitido, tamano_max_mb)
        VALUES 
        (@IdConvIA, N'Copia de Título de Tercer Nivel', 'Certificado o copia notariada registrada en Senescyt', 1, 'pdf', 10),
        (@IdConvIA, N'Cédula de Identidad / Pasaporte', 'Documento de identidad legible por ambos lados', 1, 'pdf,jpg,png', 5),
        (@IdConvIA, 'Hoja de Vida Formato UIDE', N'Curriculum vitae académico y profesional actualizado', 1, 'pdf', 10),
        (@IdConvIA, N'Carta de Motivación', N'Exposición de motivos para cursar la maestría (máx. 2 páginas)', 0, 'pdf', 5);
    END
END
GO

-- 9. Cursos Preparatorios
BEGIN
    DECLARE @IdConvIA2 INT = (SELECT id FROM convocatorias WHERE codigo = 'CONV-2026-1');
    IF NOT EXISTS (SELECT 1 FROM cursos_preparatorios WHERE codigo = 'CURSO-IA-101')
    BEGIN
        INSERT INTO cursos_preparatorios (convocatoria_id, codigo, nombre, descripcion, nota_minima, ponderacion_total, estado)
        VALUES 
        (@IdConvIA2, 'CURSO-IA-101', N'Fundamentos de Matemáticas y Programación para IA', N'Nivelación en álgebra lineal, cálculo diferencial y estructuras en Python.', 70.00, 100.00, 'ACTIVO');
    END
END
GO

-- 10. Actividades y Proyectos del Curso
BEGIN
    DECLARE @IdCursoIA INT = (SELECT id FROM cursos_preparatorios WHERE codigo = 'CURSO-IA-101');
    IF NOT EXISTS (SELECT 1 FROM actividades_curso WHERE curso_id = @IdCursoIA)
    BEGIN
        INSERT INTO actividades_curso (curso_id, titulo, tipo, instrucciones, fecha_apertura, fecha_limite, ponderacion, es_obligatorio, extensiones_permitidas, tamano_max_mb, max_reenvios)
        VALUES 
        (@IdCursoIA, N'Taller 1: Álgebra Lineal y Operaciones Matriciales', 'INDIVIDUAL', 'Resolver los ejercicios planteados en el cuaderno Jupyter y exportar informe PDF.', DATEADD(MINUTE, 480, CAST(CAST(DATEADD(DAY, -30, GETDATE()) AS DATE) AS DATETIME2)), DATEADD(MINUTE, 1439, CAST(CAST(DATEADD(DAY, -7, GETDATE()) AS DATE) AS DATETIME2)), 25.00, 1, 'pdf,zip', 15, 3),
        (@IdCursoIA, N'Taller 2: Programación Orientada a Objetos en Python', 'INDIVIDUAL', 'Implementar clases para carga y limpieza de datasets tabulares.', DATEADD(MINUTE, 480, CAST(CAST(DATEADD(DAY, -20, GETDATE()) AS DATE) AS DATETIME2)), DATEADD(MINUTE, 1439, CAST(CAST(DATEADD(DAY, 8, GETDATE()) AS DATE) AS DATETIME2)), 25.00, 1, 'pdf,py,zip', 15, 3),
        (@IdCursoIA, 'Proyecto Integrador Fase 1: Pipeline de Datos', 'PROYECTO', N'Diseñar e implementar un pipeline ETL de preparación de datos reales.', DATEADD(MINUTE, 480, CAST(CAST(DATEADD(DAY, -15, GETDATE()) AS DATE) AS DATETIME2)), DATEADD(MINUTE, 1439, CAST(CAST(DATEADD(DAY, 19, GETDATE()) AS DATE) AS DATETIME2)), 20.00, 1, 'pdf,zip', 30, 2),
        (@IdCursoIA, 'Proyecto Integrador Final: Modelo Predictivo Base', 'PROYECTO', N'Entrega del modelo predictivo evaluado con métricas de exactitud y reporte final.', DATEADD(MINUTE, 480, CAST(CAST(DATEADD(DAY, -5, GETDATE()) AS DATE) AS DATETIME2)), DATEADD(MINUTE, 1439, CAST(CAST(DATEADD(DAY, 44, GETDATE()) AS DATE) AS DATETIME2)), 30.00, 1, 'pdf,zip', 40, 2);
    END
END
GO

-- 11. Inscripciones de Postulantes
BEGIN
    DECLARE @IdPostPerez INT = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec');
    DECLARE @IdPostMorales INT = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec');
    DECLARE @IdPostZambrano INT = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec');
    DECLARE @IdPostAlvarado INT = (SELECT id FROM usuarios WHERE email = 'postulante.alvarado@uide.edu.ec');
    DECLARE @IdConvIA3 INT = (SELECT id FROM convocatorias WHERE codigo = 'CONV-2026-1');

    IF NOT EXISTS (SELECT 1 FROM inscripciones WHERE postulante_id = @IdPostPerez AND convocatoria_id = @IdConvIA3)
    BEGIN
        INSERT INTO inscripciones (postulante_id, convocatoria_id, fecha_inscripcion, estado_proceso, nivel_riesgo, motivo_riesgo, fecha_ultimo_avance)
        VALUES 
        (@IdPostPerez, @IdConvIA3, DATEADD(MINUTE, 600, CAST(CAST(DATEADD(DAY, -50, GETDATE()) AS DATE) AS DATETIME2)), 'EN_CURSO', 'BAJO', N'Cumplimiento oportuno de entregas y seguimiento al día.', SYSDATETIME()),
        (@IdPostMorales, @IdConvIA3, DATEADD(MINUTE, 690, CAST(CAST(DATEADD(DAY, -48, GETDATE()) AS DATE) AS DATETIME2)), 'EN_CURSO', 'MEDIO', N'Taller 1 vencido sin entrega y avance inferior al esperado.', DATEADD(DAY, -4, SYSDATETIME())),
        (@IdPostZambrano, @IdConvIA3, DATEADD(MINUTE, 840, CAST(CAST(DATEADD(DAY, -45, GETDATE()) AS DATE) AS DATETIME2)), 'EN_CURSO', 'ALTO', N'Inactividad mayor a 7 días y 2 contactos del tutor sin respuesta.', DATEADD(DAY, -15, SYSDATETIME())),
        (@IdPostAlvarado, @IdConvIA3, DATEADD(MINUTE, 555, CAST(CAST(DATEADD(DAY, -10, GETDATE()) AS DATE) AS DATETIME2)), 'DOCUMENTACION_PENDIENTE', 'BAJO', N'Inscripción reciente dentro del plazo reglamentario.', SYSDATETIME());
    END
END
GO

-- 12. Asignación de Curso a Postulantes
BEGIN
    DECLARE @IdInscPerez INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec'));
    DECLARE @IdInscMorales INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec'));
    DECLARE @IdInscZambrano INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec'));
    DECLARE @IdCursoIA2 INT = (SELECT id FROM cursos_preparatorios WHERE codigo = 'CURSO-IA-101');

    IF NOT EXISTS (SELECT 1 FROM asignaciones_curso WHERE inscripcion_id = @IdInscPerez AND curso_id = @IdCursoIA2)
    BEGIN
        INSERT INTO asignaciones_curso (inscripcion_id, curso_id, estado, estado_aprobacion)
        VALUES 
        (@IdInscPerez, @IdCursoIA2, 'EN_CURSO', 'PENDIENTE'),
        (@IdInscMorales, @IdCursoIA2, 'EN_CURSO', 'PENDIENTE'),
        (@IdInscZambrano, @IdCursoIA2, 'EN_CURSO', 'PENDIENTE');
    END
END
GO

-- 13. Asignación Manual de Tutor
BEGIN
    DECLARE @IdInscPerez2 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec'));
    DECLARE @IdInscMorales2 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec'));
    DECLARE @IdInscZambrano2 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec'));
    DECLARE @IdTutorIAUser INT = (SELECT id FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec');
    DECLARE @IdCoordIAUser INT = (SELECT id FROM usuarios WHERE email = 'coordinador.ia@uide.edu.ec');

    IF NOT EXISTS (SELECT 1 FROM asignaciones_tutor WHERE inscripcion_id = @IdInscPerez2)
    BEGIN
        INSERT INTO asignaciones_tutor (inscripcion_id, tutor_id, coordinador_id, estado)
        VALUES 
        (@IdInscPerez2, @IdTutorIAUser, @IdCoordIAUser, 'ACTIVO'),
        (@IdInscMorales2, @IdTutorIAUser, @IdCoordIAUser, 'ACTIVO'),
        (@IdInscZambrano2, @IdTutorIAUser, @IdCoordIAUser, 'ACTIVO');
    END
END
GO

-- 14. Entregas y Versiones de Evidencias
BEGIN
    DECLARE @IdInscPerez3 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec'));
    DECLARE @IdAsigCursoPerez INT = (SELECT id FROM asignaciones_curso WHERE inscripcion_id = @IdInscPerez3);
    DECLARE @IdActTaller1 INT = (SELECT id FROM actividades_curso WHERE titulo LIKE 'Taller 1%');
    DECLARE @IdTutorIAUser2 INT = (SELECT id FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec');

    IF @IdAsigCursoPerez IS NOT NULL AND @IdActTaller1 IS NOT NULL AND NOT EXISTS (SELECT 1 FROM entregas_evidencia WHERE asignacion_curso_id = @IdAsigCursoPerez AND actividad_id = @IdActTaller1)
    BEGIN
        INSERT INTO entregas_evidencia (asignacion_curso_id, actividad_id, estado_entrega, numero_versiones)
        VALUES (@IdAsigCursoPerez, @IdActTaller1, 'APROBADO', 1);

        DECLARE @IdEntregaPerez INT = SCOPE_IDENTITY();

        INSERT INTO versiones_evidencia (entrega_id, numero_version, nombre_archivo_original, nombre_archivo_seguro, ruta_privada, tamano_bytes, mime_type, hash_sha256, es_tardia, fecha_entrega)
        VALUES (@IdEntregaPerez, 1, 'Taller1_AlgebraLineal_Perez.pdf', 'sec_ev_perez_t1_v1.pdf', 'storage/private/evidencias/sec_ev_perez_t1_v1.pdf', 1390, 'application/pdf', '08600710e5c0a11d2bdc1c778bf0d4e340b0c3f20556a5f29b073f5519465cfe', 0, DATEADD(MINUTE, 990, CAST(CAST(DATEADD(DAY, -9, GETDATE()) AS DATE) AS DATETIME2)));

        DECLARE @IdVersionPerez INT = SCOPE_IDENTITY();

        INSERT INTO evaluaciones_evidencia (version_id, evaluador_id, puntaje_obtenido, resultado, observaciones, recomendaciones, fecha_evaluacion)
        VALUES (@IdVersionPerez, @IdTutorIAUser2, 24.50, 'APROBADO', N'Excelente resolución de sistemas lineales y claridad metodológica.', 'Continuar con el mismo rigor para el Taller 2.', DATEADD(MINUTE, 660, CAST(CAST(DATEADD(DAY, -8, GETDATE()) AS DATE) AS DATETIME2)));
    END
END
GO

-- 15. Seguimientos Cronológicos
BEGIN
    DECLARE @IdInscPerez4 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec'));
    DECLARE @IdInscMorales4 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec'));
    DECLARE @IdInscZambrano4 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec'));
    DECLARE @IdTutorIAUser3 INT = (SELECT id FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec');

    IF @IdInscPerez4 IS NOT NULL AND NOT EXISTS (SELECT 1 FROM seguimientos_postulante WHERE inscripcion_id = @IdInscPerez4)
    BEGIN
        INSERT INTO seguimientos_postulante (inscripcion_id, tutor_id, fecha_contacto, tipo_contacto, motivo, accion_realizada, resultado, respuesta_postulante, hubo_respuesta, proxima_accion, fecha_proxima_accion, estado_caso)
        VALUES 
        (@IdInscPerez4, @IdTutorIAUser3, DATEADD(MINUTE, 900, CAST(CAST(DATEADD(DAY, -15, GETDATE()) AS DATE) AS DATETIME2)), 'VIDEOCONFERENCIA', N'Revisión de dudas en Álgebra Lineal', N'Se explicaron conceptos de autovectores y descomposición SVD.', N'Postulante comprendió la teoría y finalizó los ejercicios del Taller 1.', N'Agradeció la sesión y confirmó entrega anticipada.', 1, 'Revisar avance en Proyecto Fase 1', DATEADD(MINUTE, 600, CAST(CAST(DATEADD(DAY, 8, GETDATE()) AS DATE) AS DATETIME2)), 'RESUELTO'),
        (@IdInscMorales4, @IdTutorIAUser3, DATEADD(MINUTE, 990, CAST(CAST(DATEADD(DAY, -6, GETDATE()) AS DATE) AS DATETIME2)), 'WHATSAPP', N'Recordatorio de Taller 2 próximo a vencer', N'Mensaje de alerta sobre fecha límite y disponibilidad para tutoría.', N'Postulante indicó tener dudas en estructuras POO.', N'Mencionó que enviará borrador el fin de semana.', 1, N'Agendar sesión de apoyo en vivo', DATEADD(MINUTE, 1020, CAST(CAST(DATEADD(DAY, 1, GETDATE()) AS DATE) AS DATETIME2)), 'EN_PROCESO'),
        (@IdInscZambrano4, @IdTutorIAUser3, DATEADD(MINUTE, 600, CAST(CAST(DATEADD(DAY, -10, GETDATE()) AS DATE) AS DATETIME2)), 'TELEFONO', N'Alerta de inactividad de 5 días', N'Llamada telefónica a celular registrado.', N'Teléfono sonó sin respuesta. Se envió correo de seguimiento.', 'Sin respuesta del postulante.', 0, 'Reintentar llamada en 48 horas', DATEADD(MINUTE, 600, CAST(CAST(DATEADD(DAY, -8, GETDATE()) AS DATE) AS DATETIME2)), 'EN_PROCESO'),
        (@IdInscZambrano4, @IdTutorIAUser3, DATEADD(MINUTE, 690, CAST(CAST(DATEADD(DAY, -7, GETDATE()) AS DATE) AS DATETIME2)), 'CORREO', N'Segundo intento de contacto por inactividad crítica', N'Envío de correo formal de seguimiento académico con copia a coordinación.', 'Mensaje entregado al servidor de correo.', 'Sin respuesta transcurridas 72 horas.', 0, N'Escalar caso a Coordinación de Maestría', DATEADD(MINUTE, 540, CAST(CAST(DATEADD(DAY, -2, GETDATE()) AS DATE) AS DATETIME2)), 'ESCALADO');
    END
END
GO

-- 16. Alertas de Riesgo Registradas
BEGIN
    DECLARE @IdInscZambrano5 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.zambrano@uide.edu.ec'));
    DECLARE @IdInscMorales5 INT = (SELECT id FROM inscripciones WHERE postulante_id = (SELECT id FROM usuarios WHERE email = 'postulante.morales@uide.edu.ec'));

    IF @IdInscZambrano5 IS NOT NULL AND NOT EXISTS (SELECT 1 FROM alertas_riesgo WHERE inscripcion_id = @IdInscZambrano5)
    BEGIN
        INSERT INTO alertas_riesgo (inscripcion_id, tipo_alerta, nivel_riesgo, motivo_detallado, resuelta)
        VALUES 
        (@IdInscZambrano5, 'INACTIVIDAD', 'ALTO', N'Postulante acumula más de 14 días sin registro de actividad académica significativa.', 0),
        (@IdInscZambrano5, 'CONTACTO_SIN_RESPUESTA', 'ALTO', 'Dos intentos consecutivos de contacto documentados por el tutor sin respuesta del postulante.', 0),
        (@IdInscMorales5, 'VENCIMIENTO_PROXIMO', 'MEDIO', N'Taller 1 vencido sin evidencia cargada.', 0);
    END
END
GO

PRINT N'Demostración completa y configurada al 100% en app_maestria.';
