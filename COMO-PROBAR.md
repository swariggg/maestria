# Cambios según tus respuestas: qué cambió y cómo probarlo

Son 51 archivos y ninguno está en un commit todavía. Lo que todavía hay que preguntar a la universidad está en el documento "Preguntas para la UIDE - APP Maestría".

## 1. Preparar la base de datos (una sola vez)

Desde la raíz del proyecto:

```
sqlcmd -S "." -C -E -f 65001 -i "database\01_create_schema.sql"
sqlcmd -S "." -C -E -f 65001 -i "database\02_seed_data.sql"
```

El primer script agrega las columnas y las tablas nuevas (tutores por programa, materiales y puntajes de rúbrica) sin borrar datos. El segundo deja los recordatorios en 5, 3 y 1 días y asigna cada tutor demo a su programa.

## 2. Arrancar

```
cd backend
fastapi dev app/main.py
```

```
cd frontend
npm run dev
```

## 3. Qué probar

| Tema | Dónde | Qué revisar |
|---|---|---|
| Registro | Crear cuenta | La cédula se valida de verdad (10 dígitos y dígito verificador). La contraseña necesita letras y números. Hay que aceptar el tratamiento de datos. |
| Bloqueo | Login | Después de 5 contraseñas equivocadas la cuenta se bloquea 15 minutos. Antes del bloqueo te dice cuántos intentos quedan. |
| Contraseña inicial | Admin: **Usuarios** | Si creas un usuario o le restableces la contraseña, al entrar le aparece la pantalla "Cambie su contraseña" y no puede hacer nada más hasta cambiarla. |
| Tutores por programa | Admin: **Usuarios** | Los tutores ahora también tienen programas. Solo se les puede asignar un postulante de esos programas. Cambiar de tutor pide motivo. |
| Inscripción | Postulante: **Inscripción** | Cada convocatoria muestra modalidad y cupos libres (60 por defecto). Antes de inscribirse hay que completar el perfil. Se puede estar en dos maestrías si las fechas no se cruzan; si se cruzan, aparece el motivo. |
| Retiro | Postulante: **Mi Perfil**. Coordinador: **Postulantes** (botón de la libreta) | El postulante pide el retiro con motivo. El coordinador lo aprueba o rechaza, o lo retira directamente indicando el motivo. Ahí mismo están pago, beca y adaptaciones. |
| Documentos | **Mi Perfil** y **Postulantes → Documentos** | 3 intentos por documento. Rechazado es definitivo para el postulante. Solo el coordinador revisa (el tutor solo descarga). El coordinador puede reabrir un documento aprobado o rechazado, con motivo. Los requisitos solo se editan mientras la convocatoria está Planificada. |
| Evidencias | **Evidencias** | No se puede subir antes de que abra la actividad ni después de que cierre, salvo para corregir lo que el tutor devolvió. Se ve cuántos intentos van y cuántos quedan. |
| Calificar | **Evidencias** | Califica el tutor asignado. El coordinador solo si el postulante no tiene tutor. Para cambiar una nota hay que escribir el motivo, y solo puede hacerlo quien calificó. Si se agotan los intentos de una actividad obligatoria sin aprobarla, el proceso queda no aprobado y se le avisa por correo. |
| Rúbrica | **Programas y Cursos** (botón de lista en cada actividad) | Tutor o coordinador ponen criterios con puntaje. Deben sumar la ponderación. Con rúbrica, la nota es la suma de los criterios. |
| Materiales y sesiones | **Programas y Cursos**, debajo de las actividades | Subir archivos, enlaces y sesiones de Teams o Zoom con fecha. El postulante los ve en el mismo lugar. |
| Convocatorias | **Programas y Cursos** | Cupo y modalidad. Una convocatoria en curso se puede reabrir si la fecha de cierre no pasó. Una finalizada se puede reabrir con motivo y los postulantes vuelven a su estado anterior. Aviso cuando el preparatorio ya terminó y falta finalizar. Las inscripciones se cierran solas al pasar la fecha de cierre. |
| Alertas | **Alertas** | El tutor puede derivar una alerta a un coordinador con una nota. Una alerta resuelta a mano no vuelve a aparecer mientras siga igual. Nueva alerta: compromiso vencido. |
| Seguimiento | **Postulantes → Seguimiento** | Videoconferencia o presencial piden evidencia adjunta. |
| Dashboard del postulante | **Dashboard** | Suma todas sus inscripciones. Tiene un calendario con entregas y sesiones, y sus avisos. |
| Reportes | **Reportes y Matrices** | El tutor descarga la matriz solo con sus postulantes. Quien aprobó descarga su certificado en PDF con logo y código de verificación. |
| Resumen diario | Tabla `notificaciones_cola` | A las 7:00 el tutor y el coordinador reciben un correo con lo que tienen pendiente (solo si hay algo). |

## 4. Commit sugerido

```
git add .
git commit -m "feat: reglas del proceso según respuestas (intentos, retiro, rúbrica, materiales, certificado, seguridad)"
git push
```
