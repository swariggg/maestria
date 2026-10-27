-- ============================================================================
-- APP - Maestría: Sistema de Gestión de Cursos Preparatorios (UIDE)
-- Script DML: Datos de Demostración y Configuración Inicial (Autónomo por Lote)
-- ============================================================================

USE app_maestria;
GO

-- 1. Insertar Roles
IF NOT EXISTS (SELECT 1 FROM roles WHERE codigo = 'ADMIN')
BEGIN
    INSERT INTO roles (codigo, nombre, descripcion) VALUES
    ('ADMIN', 'Administrador Global', 'Control total administrativo, gestión de usuarios, auditoría y parámetros globales'),
    ('COORDINADOR', 'Coordinador de Programa', 'Gestión exclusiva de sus programas asignados, convocatorias, cursos, actividades y asignación de tutores'),
    ('TUTOR', 'Tutor Académico', 'Seguimiento y evaluación exclusiva de los postulantes que le han sido asignados'),
    ('POSTULANTE', 'Postulante a Maestría', 'Acceso a sus cursos asignados, entrega de evidencias, consulta de avance y notificaciones');
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
        VALUES ('admin@uide.edu.ec', @PwdHash, 'Dra. María Elena Ramos (Admin)', '1710000001', '0991112222', @RolAdmin, 'ACTIVO');
    END

    -- Coordinadores
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'coordinador.ia@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('coordinador.ia@uide.edu.ec', @PwdHash, 'Dr. Roberto Carlos Andrade (Coord. IA)', '1710000002', '0992223333', @RolCoord, 'ACTIVO'),
        ('coordinador.ciber@uide.edu.ec', @PwdHash, 'MSc. Gabriela Lucía Montalvo (Coord. Ciber)', '1710000003', '0993334444', @RolCoord, 'ACTIVO');
    END

    -- Tutores
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'tutor.ia@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('tutor.ia@uide.edu.ec', @PwdHash, 'Ing. Carlos Patricio Viteri (Tutor IA)', '1710000004', '0994445555', @RolTutor, 'ACTIVO'),
        ('tutor.ciber@uide.edu.ec', @PwdHash, 'Ing. Andrea Sofía Benítez (Tutor Ciber)', '1710000005', '0995556666', @RolTutor, 'ACTIVO');
    END

    -- Postulantes
    IF NOT EXISTS (SELECT 1 FROM usuarios WHERE email = 'postulante.perez@uide.edu.ec')
    BEGIN
        INSERT INTO usuarios (email, password_hash, nombre_completo, cedula, telefono, rol_id, estado)
        VALUES 
        ('postulante.perez@uide.edu.ec', @PwdHash, 'Juan Sebastián Pérez Castro', '1711111111', '0981001001', @RolPost, 'ACTIVO'),
        ('postulante.morales@uide.edu.ec', @PwdHash, 'Ana María Morales Cevallos', '1711111112', '0982002002', @RolPost, 'ACTIVO'),
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
        (@IdTutor1, 'Machine Learning & Matemáticas Computacionales', 25, 1),
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
        (@IdMorales, 'Calle Los Guayacanes 145', 'Guayaquil', 'Ecuador', 'Licenciada en Computación', 'ESPOL', 1, 'Marco Morales (Padre)', '0990002222'),
        (@IdZambrano, 'Av. Amazonas N24-10', 'Quito', 'Ecuador', 'Ingeniero en Electrónica', 'UIDE', 1, 'Lorena Loor (Esposa)', '0990003333'),
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
        ('MIA-01', 'Maestría en Inteligencia Artificial Aplicada', 'Programa de posgrado enfocado en modelos predictivos, deep learning y visión artificial.', 'ACTIVO', @IdAdmin),
        ('MCG-01', 'Maestría en Ciberseguridad y Gestión de Riesgos', 'Especialización en defensa perimetral, respuesta a incidentes y cumplimiento normativo.', 'ACTIVO', @IdAdmin);
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
        (@IdProgIA2, 'CONV-2026-1', 'Convocatoria IA Cohorte I - 2026', '2026-09-01', '2026-11-30', '2026-10-01', '2026-12-15', 'EN_CURSO'),
        (@IdProgCiber2, 'CONV-2026-CIBER', 'Convocatoria Ciberseguridad Cohorte I - 2026', '2026-09-15', '2026-12-05', '2026-10-15', '2026-12-20', 'EN_CURSO');
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
        (@IdConvIA, 'Copia de Título de Tercer Nivel', 'Certificado o copia notariada registrada en Senescyt', 1, 'pdf', 10),
        (@IdConvIA, 'Cédula de Identidad / Pasaporte', 'Documento de identidad legible por ambos lados', 1, 'pdf,jpg,png', 5),
        (@IdConvIA, 'Hoja de Vida Formato UIDE', 'Curriculum vitae académico y profesional actualizado', 1, 'pdf', 10),
        (@IdConvIA, 'Carta de Motivación', 'Exposición de motivos para cursar la maestría (máx. 2 páginas)', 0, 'pdf', 5);
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
        (@IdConvIA2, 'CURSO-IA-101', 'Fundamentos de Matemáticas y Programación para IA', 'Nivelación en álgebra lineal, cálculo diferencial y estructuras en Python.', 70.00, 100.00, 'ACTIVO');
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
        (@IdCursoIA, 'Taller 1: Álgebra Lineal y Operaciones Matriciales', 'INDIVIDUAL', 'Resolver los ejercicios planteados en el cuaderno Jupyter y exportar informe PDF.', '2026-10-01 08:00', '2026-10-20 23:59', 25.00, 1, 'pdf,zip', 15, 3),
        (@IdCursoIA, 'Taller 2: Programación Orientada a Objetos en Python', 'INDIVIDUAL', 'Implementar clases para carga y limpieza de datasets tabulares.', '2026-10-10 08:00', '2026-10-31 23:59', 25.00, 1, 'pdf,py,zip', 15, 3),
        (@IdCursoIA, 'Proyecto Integrador Fase 1: Pipeline de Datos', 'PROYECTO', 'Diseñar e implementar un pipeline ETL de preparación de datos reales.', '2026-10-15 08:00', '2026-11-15 23:59', 20.00, 1, 'pdf,zip', 30, 2),
        (@IdCursoIA, 'Proyecto Integrador Final: Modelo Predictivo Base', 'PROYECTO', 'Entrega del modelo predictivo evaluado con métricas de exactitud y reporte final.', '2026-10-25 08:00', '2026-12-10 23:59', 30.00, 1, 'pdf,zip', 40, 2);
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
        (@IdPostPerez, @IdConvIA3, '2026-09-10 10:00', 'EN_CURSO', 'BAJO', 'Cumplimiento oportuno de entregas y seguimiento al día.', SYSDATETIME()),
        (@IdPostMorales, @IdConvIA3, '2026-09-12 11:30', 'EN_CURSO', 'MEDIO', 'Taller 2 pendiente próximo a vencer (menos de 6 días) y avance inferior al esperado.', DATEADD(DAY, -4, SYSDATETIME())),
        (@IdPostZambrano, @IdConvIA3, '2026-09-15 14:00', 'EN_CURSO', 'ALTO', 'Inactividad mayor a 7 días y 2 contactos del tutor sin respuesta.', DATEADD(DAY, -9, SYSDATETIME())),
        (@IdPostAlvarado, @IdConvIA3, '2026-10-01 09:15', 'DOCUMENTACION_PENDIENTE', 'BAJO', 'Inscripción reciente dentro del plazo reglamentario.', SYSDATETIME());
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
        VALUES (@IdEntregaPerez, 1, 'Taller1_AlgebraLineal_Perez.pdf', 'sec_ev_perez_t1_v1.pdf', 'storage/private/evidencias/sec_ev_perez_t1_v1.pdf', 1048576, 'application/pdf', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 0, '2026-10-18 16:30');

        DECLARE @IdVersionPerez INT = SCOPE_IDENTITY();

        INSERT INTO evaluaciones_evidencia (version_id, evaluador_id, puntaje_obtenido, resultado, observaciones, recomendaciones, fecha_evaluacion)
        VALUES (@IdVersionPerez, @IdTutorIAUser2, 24.50, 'APROBADO', 'Excelente resolución de sistemas lineales y claridad metodológica.', 'Continuar con el mismo rigor para el Taller 2.', '2026-10-19 11:00');
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
        (@IdInscPerez4, @IdTutorIAUser3, '2026-10-12 15:00', 'VIDEOCONFERENCIA', 'Revisión de dudas en Álgebra Lineal', 'Se explicaron conceptos de autovectores y descomposición SVD.', 'Postulante comprendió la teoría y finalizó los ejercicios del Taller 1.', 'Agradeció la sesión y confirmó entrega anticipada.', 1, 'Revisar avance en Proyecto Fase 1', '2026-11-05 10:00', 'RESUELTO'),
        (@IdInscMorales4, @IdTutorIAUser3, '2026-10-21 16:30', 'WHATSAPP', 'Recordatorio de Taller 2 próximo a vencer', 'Mensaje de alerta sobre fecha límite y disponibilidad para tutoría.', 'Postulante indicó tener dudas en estructuras POO.', 'Mencionó que enviará borrador el fin de semana.', 1, 'Agendar sesión de apoyo en vivo', '2026-10-28 17:00', 'EN_PROCESO'),
        (@IdInscZambrano4, @IdTutorIAUser3, '2026-10-18 10:00', 'TELEFONO', 'Alerta de inactividad de 5 días', 'Llamada telefónica a celular registrado.', 'Teléfono sonó sin respuesta. Se envió correo de seguimiento.', 'Sin respuesta del postulante.', 0, 'Reintentar llamada en 48 horas', '2026-10-20 10:00', 'EN_PROCESO'),
        (@IdInscZambrano4, @IdTutorIAUser3, '2026-10-21 11:30', 'CORREO', 'Segundo intento de contacto por inactividad crítica', 'Envío de correo formal de seguimiento académico con copia a coordinación.', 'Mensaje entregado al servidor de correo.', 'Sin respuesta transcurridas 72 horas.', 0, 'Escalar caso a Coordinación de Maestría', '2026-10-26 09:00', 'ESCALADO');
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
        (@IdInscZambrano5, 'INACTIVIDAD', 'ALTO', 'Postulante acumula más de 8 días sin registro de actividad académica significativa.', 0),
        (@IdInscZambrano5, 'CONTACTO_SIN_RESPUESTA', 'ALTO', 'Dos intentos consecutivos de contacto documentados por el tutor sin respuesta del postulante.', 0),
        (@IdInscMorales5, 'VENCIMIENTO_PROXIMO', 'MEDIO', 'Taller 2 vence en menos de 6 días sin evidencia cargada.', 0);
    END
END
GO

PRINT 'Demostración completa y configurada al 100% en app_maestria.';
