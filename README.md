# APP - Maestría
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
- **Backend:** Python 3.14 / 3.12, FastAPI 0.115+ (con `fastapi[standard]`), SQLAlchemy 2.0+, PyODBC 5.3+, Pydantic v2, APScheduler 3.11+, ReportLab 5.1+, OpenPyXL 3.1+.
- **Frontend:** React 18, Vite 5.4, Lucide React (iconos académicos), CSS Tokens Centralizados.
- **Herramientas:** `pip`, `npm`, `pytest`.

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
| **Postulante (Riesgo Medio)**| `postulante.morales@uide.edu.ec`| Ana Morales: Taller 1 vencido sin entrega y avance rezagado. |
| **Postulante (Riesgo Alto)** | `postulante.zambrano@uide.edu.ec`| David Zambrano: Inactivo más de 14 días y 2 contactos sin respuesta. |

*(La pantalla de inicio de sesión incluye botones de acceso rápido con 1 solo clic para alternar entre roles).*

Un postulante nuevo puede crear su cuenta desde **"Crear cuenta"** en la pantalla de inicio de sesión y luego inscribirse en una convocatoria abierta desde la sección **Inscripción**. Al inscribirse se le asignan automáticamente todos los cursos preparatorios activos de esa convocatoria.

---

## 5. Instalación y Ejecución Local

Requisitos previos: SQL Server con ODBC Driver 18, Python 3.12+ y Node.js 20+.

### Paso 1: Crear la base de datos
Desde la raíz del proyecto:
```powershell
sqlcmd -S "." -C -E -f 65001 -i "database\01_create_schema.sql"
sqlcmd -S "." -C -E -f 65001 -i "database\02_seed_data.sql"
```
La opción `-f 65001` hace que `sqlcmd` lea los scripts como UTF-8. Sin ella, las tildes y la ñ se guardan mal (por ejemplo, "MaestrÃa").

Para reiniciar la base desde cero (borra todos los datos), detenga el backend y ejecute antes:
```powershell
sqlcmd -S "." -C -E -Q "ALTER DATABASE [app_maestria] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [app_maestria];"
```

### Paso 2: Backend (FastAPI)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # luego edite .env con sus valores
fastapi dev
```
- API REST: `http://127.0.0.1:8000`
- Documentación Swagger: `http://127.0.0.1:8000/docs`

La próxima vez solo hace falta activar el entorno (`.\.venv\Scripts\activate`) y ejecutar `fastapi dev`.

### Paso 3: Frontend (React + Vite)
En otra terminal:
```powershell
cd frontend
npm install
npm run dev
```
- Aplicación web: `http://localhost:5173`

---

## 6. Pruebas Automatizadas

Se entrega una suite de pruebas con **Pytest** que valida las reglas de negocio críticas:
- Cifrado de contraseñas con Bcrypt.
- Creación y verificación de tokens JWT.
- Conexión real a SQL Server.
- Motor de riesgos (caso Zambrano detecta ALTO, caso Pérez detecta BAJO).
- Validación de ponderaciones (suma exactamente 100.0%).
- Idempotencia en recordatorios (previene envíos duplicados).
- Generación de informe PDF individual con ReportLab.
- Generación de matriz Excel `.xlsx` con OpenPyXL.

Con el entorno del backend activado:
```powershell
cd backend
pytest -v
```

---

## 7. Respaldo y Restauración de la Base de Datos

### Respaldo
```powershell
mkdir database\backups
sqlcmd -S "." -C -E -Q "BACKUP DATABASE [app_maestria] TO DISK = N'C:\ruta\completa\database\backups\app_maestria.bak' WITH INIT, STATS = 10"
```
*(SQL Server necesita una ruta absoluta en la que su servicio tenga permiso de escritura).*

### Restauración
```powershell
sqlcmd -S "." -C -E -Q "ALTER DATABASE [app_maestria] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; RESTORE DATABASE [app_maestria] FROM DISK = N'C:\ruta\completa\database\backups\app_maestria.bak' WITH REPLACE; ALTER DATABASE [app_maestria] SET MULTI_USER;"
```

---

## 8. Asuntos Pendientes de Validación Institucional (UIDE)

1. **Nota Mínima Institucional:** Actualmente configurada en 70/100 (editable por Coordinador). Requiere confirmación del Consejo de Posgrados.
2. **Entregas Tardías:** Se registran con marca temporal y se permite su revisión por el tutor. Debe validarse si existirá penalización porcentual fija.
3. **Plazo de Retención de Auditoría:** Propuesto en 5 años según la Ley Orgánica de Protección de Datos Personales (LOPDP) de Ecuador.
4. **Integración con Sistemas Centrales (Banner / SENESCYT):** Se incluye el módulo `integraciones_simuladas` con contratos mock hasta recibir los endpoints y credenciales oficiales de la universidad.
