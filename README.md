# APP - Maestría: Sistema de Gestión de Cursos Preparatorios

**Institución:** Universidad Internacional del Ecuador (UIDE)  
**Versión:** 1.0.0  
**Fecha:** Octubre 2026  
**Estado:** Totalmente Funcional, Probado y Verificado Localmente  

---

## 1. Descripción General del Proyecto

**APP - Maestría** es una plataforma web integral diseñada para la gestión, seguimiento académico y supervisión administrativa de los cursos preparatorios para postulantes a programas de posgrado y maestría de la UIDE.

El sistema centraliza y estandariza:
1. **Programas de Maestría y Convocatorias:** Control de fechas de apertura, cierre y calendarios del preparatorio.
2. **Cursos, Actividades y Proyectos:** Gestión curricular con validación estricta de ponderaciones (hasta el 100%), fechas límite y tipos de archivo admitidos.
3. **Inscripciones y Postulantes:** Expediente individual con trazabilidad y porcentaje real de avance.
4. **Almacenamiento Privado de Evidencias:** Archivos resguardados fuera de la raíz web con hash SHA-256, versionado inmutable y control estricto de acceso.
5. **Calificaciones y Retroalimentación:** Registro de notas, observaciones y recomendaciones por los tutores asignados.
6. **Seguimiento Cronológico (Bitácora):** Registro de contactos multicanal (teléfono, correo, WhatsApp, videoconferencia, presencial) con estado de respuesta del postulante.
7. **Motor Automático de Riesgos:** Detección de inactividad académica prolongada (7 días) y acumulación de contactos sin respuesta (2 intentos), clasificando en Riesgo Alto, Medio o Bajo.
8. **Notificaciones y Recordatorios:** Recordatorios automatizados de vencimiento a los 15, 10, 5, 3 y 1 día previo a la fecha límite, con modo de prueba SMTP local.
9. **Reportes Universitarios:** Descarga de Informes Individuales en PDF formal y Matriz Consolidada de Seguimiento en Microsoft Excel (`.xlsx`).
10. **Auditoría Global:** Bitácora inmutable de eventos sensibles con usuario, IP, acción y correlación.
11. **Diseño Pastel Moderno (Sección 25):** Paleta académica suave de alto contraste, diseño 100% responsivo y **cero botones sin funcionalidad**.

---

## 2. Tecnologías y Versiones Utilizadas

- **Base de Datos:** Microsoft SQL Server 2022 / 2025 (Instancia `MSSQLSERVER` local, ODBC Driver 18).
- **Backend:** Python 3.14 / 3.12, FastAPI 0.115+, SQLAlchemy 2.0+, PyODBC 5.3+, Pydantic v2, APScheduler 3.11+, ReportLab 5.1+, OpenPyXL 3.1+.
- **Frontend:** React 18, Vite 5.4, Lucide React (iconos académicos), CSS Tokens Centralizados.
- **Herramientas de Empaquetado y Pruebas:** `uv` 0.11+, `npm` 11+, `pytest` 9.1+.

---

## 3. Acceso a SQL Server y Creación de la Base de Datos

> [!NOTE]
> **Respuesta a la consulta explícita:**  
> Sí, nos conectamos directamente a la instancia local de Microsoft SQL Server mediante `sqlcmd` con autenticación integrada de Windows y se creó la base de datos `app_maestria` con sus 29 tablas normalizadas, claves foráneas, restricciones, índices y datos iniciales de demostración.

### Scripts SQL Incluidos en `/database`:
1. `01_create_schema.sql`: Script DDL que genera las 29 tablas relacionales e índices.
2. `02_seed_data.sql`: Script DML que carga los 4 roles, parámetros globales, plantillas y registros de prueba.

---

## 4. Cuentas de Demostración para Evaluación Inmediata

Todas las cuentas de prueba están preconfiguradas con la contraseña: **`Demo2026!`**

| Rol | Correo Electrónico | Perfil / Casos de Prueba |
|---|---|---|
| **Administrador** | `admin@uide.edu.ec` | Control global, auditoría, gestión de programas y usuarios. |
| **Coordinador IA** | `coordinador.ia@uide.edu.ec` | Asignado a "Maestría en IA", gestión de cursos, asignación manual de tutores y reportes. |
| **Tutor IA** | `tutor.ia@uide.edu.ec` | Calificación de evidencias, registro de bitácora y seguimiento a postulantes asignados. |
| **Postulante (Riesgo Bajo)** | `postulante.perez@uide.edu.ec` | Juan Pérez: Avance al día, evidencia calificada con 24.5/25 pts. |
| **Postulante (Riesgo Medio)**| `postulante.morales@uide.edu.ec`| Ana Morales: Taller 2 próximo a vencer y avance rezagado. |
| **Postulante (Riesgo Alto)** | `postulante.zambrano@uide.edu.ec`| David Zambrano: Inactivo más de 8 días y 2 contactos sin respuesta. |

*(La pantalla de inicio de sesión incluye botones de acceso rápido con 1 solo clic para alternar entre roles).*

---

## 5. Instrucciones de Instalación y Ejecución Local

### Paso 1: Inicialización de la Base de Datos en SQL Server
Si requiere crear o reiniciar la base de datos desde la consola de Windows:
```powershell
sqlcmd -S "." -C -E -i "database\01_create_schema.sql"
sqlcmd -S "." -C -E -i "database\02_seed_data.sql"
```

### Paso 2: Iniciar el Backend (FastAPI)
Ejecute el archivo por lotes `start_backend.bat` o mediante la terminal:
```powershell
cd backend
# Activar entorno virtual
.\.venv\Scripts\activate
# Iniciar servidor Uvicorn
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API REST disponible en: `http://127.0.0.1:8000`
- Documentación Interactiva Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

### Paso 3: Iniciar el Frontend (React + Vite)
Ejecute el archivo por lotes `start_frontend.bat` o mediante la terminal:
```powershell
cd frontend
npm run dev
```
- Aplicación web disponible en: `http://localhost:5173`

---

## 6. Pruebas Automatizadas

Se entrega una suite de pruebas con **Pytest** que valida las reglas de negocio críticas:
- Cifrado de contraseñas con Bcrypt.
- Creación y verificación de tokens JWT.
- Conexión real a SQL Server 2022/2025.
- Motor de riesgos (caso Zambrano detecta ALTO, caso Pérez detecta BAJO).
- Validación de ponderaciones (suma exactamente 100.0%).
- Idempotencia en recordatorios (previene envíos duplicados).
- Generación de informe PDF individual universitario con ReportLab.
- Generación de matriz Excel `.xlsx` con OpenPyXL.

Para ejecutar las pruebas:
```powershell
cd backend
.\.venv\Scripts\activate
pytest -v
```
*(Resultado actual: 9 de 9 pruebas aprobadas exitosamente).*

---

## 7. Procedimiento de Respaldo y Restauración de Base de Datos

### Respaldo Local (Backup)
Haga doble clic en `backup_database.bat` o ejecute:
```powershell
sqlcmd -S "." -C -E -Q "BACKUP DATABASE [app_maestria] TO DISK = N'database\backups\app_maestria.bak' WITH NOFORMAT, NOINIT, SKIP, STATS = 10"
```

### Restauración Limpia (Restore)
```powershell
sqlcmd -S "." -C -E -Q "ALTER DATABASE [app_maestria] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; RESTORE DATABASE [app_maestria] FROM DISK = N'database\backups\app_maestria.bak' WITH REPLACE; ALTER DATABASE [app_maestria] SET MULTI_USER;"
```

---

## 8. Asuntos Pendientes de Validación Institucional (UIDE)

1. **Nota Mínima Institucional:** Actualmente configurada en 70/100 (editable por Coordinador). Requiere confirmación del Consejo de Posgrados.
2. **Entregas Tardías:** Se registran con marca temporal y se permite su revisión por el tutor. Debe validarse si existirá penalización porcentual fija.
3. **Plazo de Retención de Auditoría:** Propuesto en 5 años según la Ley Orgánica de Protección de Datos Personales (LOPDP) de Ecuador.
4. **Integración con Sistemas Centrales (Banner / SENESCYT):** Se incluye el módulo `integraciones_simuladas` con contratos mock hasta recibir los endpoints y credenciales oficiales de la universidad.
