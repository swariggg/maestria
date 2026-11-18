from datetime import datetime, date
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field

# --- AUTH & USERS ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    nombre_completo: str = Field(min_length=3)
    cedula: str = Field(min_length=10, max_length=20)
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    titulo_tercer_nivel: Optional[str] = None
    universidad_origen: Optional[str] = None
    acepta_datos: bool = False

class RolOut(BaseModel):
    id: int
    codigo: str
    nombre: str

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    id: int
    email: str
    nombre_completo: str
    cedula: str
    telefono: Optional[str] = None
    estado: str
    rol: RolOut
    debe_cambiar_password: bool = False

    class Config:
        from_attributes = True

class ProfileOut(BaseModel):
    id: int
    direccion: Optional[str]
    ciudad: Optional[str]
    pais: str
    titulo_tercer_nivel: Optional[str]
    universidad_origen: Optional[str]
    registrado_senescyt: bool
    contacto_emergencia: Optional[str]
    telefono_emergencia: Optional[str]

    class Config:
        from_attributes = True

class UserDetailOut(UserOut):
    perfil: Optional[ProfileOut] = None

# --- PROGRAMAS Y CONVOCATORIAS ---
class ProgramCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=3, max_length=250)
    descripcion: Optional[str] = None

class ProgramOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    estado: str
    creado_en: datetime

    class Config:
        from_attributes = True

class ConvocatoriaUpdate(BaseModel):
    nombre: str = Field(min_length=3, max_length=200)
    fecha_apertura: date
    fecha_cierre: date
    fecha_inicio_preparatorio: date
    fecha_fin_preparatorio: date
    cupo_maximo: int = Field(60, ge=1, le=2000)
    modalidad: str = "EN_LINEA"

class ConvocatoriaCreate(ConvocatoriaUpdate):
    programa_id: int
    codigo: str = Field(min_length=2, max_length=50)

class ConvocatoriaEstadoUpdate(BaseModel):
    estado: str
    motivo: Optional[str] = None

class ConvocatoriaOut(BaseModel):
    id: int
    programa_id: int
    codigo: str
    nombre: str
    fecha_apertura: date
    fecha_cierre: date
    fecha_inicio_preparatorio: date
    fecha_fin_preparatorio: date
    estado: str
    cupo_maximo: int = 60
    modalidad: str = "EN_LINEA"
    inscritos: int = 0

    class Config:
        from_attributes = True

# --- CURSOS Y ACTIVIDADES ---
class CourseCreate(BaseModel):
    convocatoria_id: int
    codigo: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: Optional[str] = None
    nota_minima: float = Field(70.0, ge=0, le=100)
    ponderacion_total: float = Field(100.0, gt=0, le=100)

class CourseUpdate(BaseModel):
    codigo: str = Field(min_length=2, max_length=50)
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: Optional[str] = None
    nota_minima: float = Field(ge=0, le=100)

class ActivityUpdate(BaseModel):
    titulo: str = Field(min_length=2, max_length=200)
    tipo: str = "INDIVIDUAL"
    instrucciones: Optional[str] = None
    fecha_apertura: datetime
    fecha_limite: datetime
    ponderacion: float = Field(gt=0, le=100)
    es_obligatorio: bool = True
    extensiones_permitidas: str = Field("pdf,zip,docx", min_length=2, max_length=100)
    tamano_max_mb: int = Field(25, ge=1, le=50)
    max_reenvios: int = Field(3, ge=1, le=10)

class ActivityCreate(ActivityUpdate):
    curso_id: int

class ActivityOut(BaseModel):
    id: int
    curso_id: int
    titulo: str
    tipo: str
    instrucciones: Optional[str]
    fecha_apertura: datetime
    fecha_limite: datetime
    ponderacion: float
    es_obligatorio: bool
    extensiones_permitidas: str
    tamano_max_mb: int
    max_reenvios: int
    estado: str

    class Config:
        from_attributes = True

class CourseOut(BaseModel):
    id: int
    convocatoria_id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    nota_minima: float
    ponderacion_total: float
    estado: str
    actividades: List[ActivityOut] = []

    class Config:
        from_attributes = True

# --- INSCRIPCIONES Y POSTULANTES ---
class ApplicantListItem(BaseModel):
    id: int # Inscripcion ID
    postulante_id: int # Usuario ID
    nombre_completo: str
    email: str
    cedula: str
    programa_codigo: str
    programa_nombre: str
    convocatoria_nombre: str
    estado_proceso: str
    nivel_riesgo: str
    motivo_riesgo: Optional[str] = None
    fecha_inscripcion: datetime
    tutor_nombre: Optional[str] = None
    tutor_id: Optional[int] = None
    programa_id: Optional[int] = None
    porcentaje_avance: float = 0.0
    requiere_adaptaciones: bool = False
    nota_adaptaciones: Optional[str] = None
    retiro_solicitado: bool = False
    motivo_retiro: Optional[str] = None

class EnrollmentCreate(BaseModel):
    convocatoria_id: int

class OpenCallOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    programa_codigo: str
    programa_nombre: str
    fecha_apertura: date
    fecha_cierre: date
    fecha_inicio_preparatorio: date
    fecha_fin_preparatorio: date
    cursos: List[str] = []
    inscrito: bool = False
    modalidad: str = "EN_LINEA"
    cupo_maximo: int = 60
    cupos_disponibles: int = 0
    puede_inscribirse: bool = True
    motivo_no_disponible: Optional[str] = None

class MyEnrollmentOut(BaseModel):
    id: int
    convocatoria_id: int
    convocatoria_nombre: str
    programa_nombre: str
    fecha_inscripcion: datetime
    estado_proceso: str
    cursos: List[str] = []
    retiro_solicitado: bool = False
    motivo_retiro: Optional[str] = None

class RequirementUploadResponse(BaseModel):
    id: int
    nombre_original: str
    estado_revision: str
    fecha_carga: datetime

# --- EVIDENCIAS Y EVALUACIONES ---
class PuntajeCriterioIn(BaseModel):
    criterio_id: int
    puntaje: float

class EvaluationCreate(BaseModel):
    version_id: int
    puntaje_obtenido: Optional[float] = None  # con rúbrica se calcula sumando los criterios
    puntajes: List[PuntajeCriterioIn] = []
    motivo_recalificacion: Optional[str] = None
    resultado: str # APROBADO, REQUIERE_CORRECCION, RECHAZADO
    observaciones: Optional[str] = None
    recomendaciones: Optional[str] = None

class EvaluationOut(BaseModel):
    id: int
    version_id: int
    evaluador_id: int
    evaluador_nombre: Optional[str] = None
    puntaje_obtenido: float
    resultado: str
    observaciones: Optional[str]
    recomendaciones: Optional[str]
    fecha_evaluacion: datetime
    puntajes: List[dict] = []

    class Config:
        from_attributes = True

class EvidenceVersionOut(BaseModel):
    id: int
    numero_version: int
    nombre_archivo_original: str
    tamano_bytes: int
    es_tardia: bool
    fecha_entrega: datetime
    evaluacion: Optional[EvaluationOut] = None

    class Config:
        from_attributes = True

class EvidenceOut(BaseModel):
    id: int
    actividad_id: int
    actividad_titulo: str
    estado_entrega: str
    numero_versiones: int
    versiones: List[EvidenceVersionOut] = []

# --- TUTORES Y SEGUIMIENTOS ---
class AssignTutorRequest(BaseModel):
    inscripcion_id: int
    tutor_id: int
    motivo: Optional[str] = None

class CompromisoIn(BaseModel):
    descripcion: str = Field(min_length=3, max_length=500)
    fecha_compromiso: date

class CompromisoOut(BaseModel):
    id: int
    descripcion: str
    fecha_compromiso: date
    cumplido: bool
    fecha_cumplimiento: Optional[datetime] = None

    class Config:
        from_attributes = True

class FollowupCreate(BaseModel):
    observaciones: Optional[str] = None
    recomendaciones: Optional[str] = None
    compromisos: List[CompromisoIn] = []
    inscripcion_id: int
    fecha_contacto: datetime
    tipo_contacto: str # TELEFONO, CORREO, WHATSAPP, VIDEOCONFERENCIA, PRESENCIAL
    motivo: str
    accion_realizada: str
    resultado: str
    respuesta_postulante: Optional[str] = None
    hubo_respuesta: bool = True
    proxima_accion: Optional[str] = None
    fecha_proxima_accion: Optional[datetime] = None
    estado_caso: str = "ABIERTO" # ABIERTO, EN_PROCESO, RESUELTO, ESCALADO

class FollowupOut(BaseModel):
    id: int
    inscripcion_id: int
    tutor_id: int
    tutor_nombre: str
    fecha_contacto: datetime
    tipo_contacto: str
    motivo: str
    accion_realizada: str
    resultado: str
    respuesta_postulante: Optional[str]
    hubo_respuesta: bool
    proxima_accion: Optional[str]
    fecha_proxima_accion: Optional[datetime]
    estado_caso: str
    creado_en: datetime
    numero_seguimiento: Optional[int] = None
    observaciones: Optional[str] = None
    recomendaciones: Optional[str] = None
    evidencia_nombre: Optional[str] = None
    compromisos: List[CompromisoOut] = []

    class Config:
        from_attributes = True

# --- RIESGOS Y ALERTAS ---
class RiskAlertOut(BaseModel):
    id: int
    inscripcion_id: int
    postulante_nombre: str
    programa_codigo: Optional[str] = None
    tipo_alerta: str
    nivel_riesgo: str
    motivo_detallado: str
    fecha_deteccion: datetime
    resuelta: bool
    fecha_resolucion: Optional[datetime] = None
    accion_tomada: Optional[str] = None
    resuelta_por_nombre: Optional[str] = None
    derivada_a_nombre: Optional[str] = None
    nota_derivacion: Optional[str] = None

# --- AUDITORIA ---
class AuditLogOut(BaseModel):
    id: int
    usuario_nombre: Optional[str]
    accion: str
    entidad: str
    entidad_id: Optional[str]
    ip_origen: Optional[str]
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# --- DASHBOARD STATS ---
class DashboardStats(BaseModel):
    rol: str
    total_postulantes: int = 0
    cursos_activos: int = 0
    postulantes_aprobados: int = 0
    postulantes_riesgo_alto: int = 0
    postulantes_riesgo_medio: int = 0
    postulantes_riesgo_bajo: int = 0
    porcentaje_cumplimiento_promedio: float = 0.0
    actividades_pendientes: int = 0
    seguimientos_totales: int = 0
    seguimientos_sin_respuesta: int = 0
    casos_criticos: List[dict] = []
    proximos_vencimientos: List[dict] = []
    calendario: List[dict] = []
    inscripciones: List[dict] = []

# --- PERFIL Y DOCUMENTOS DEL POSTULANTE ---
class ProfileUpdate(BaseModel):
    telefono: Optional[str] = Field(None, max_length=30)
    direccion: Optional[str] = Field(None, max_length=255)
    ciudad: Optional[str] = Field(None, max_length=100)
    pais: Optional[str] = Field("Ecuador", max_length=100)
    titulo_tercer_nivel: Optional[str] = Field(None, max_length=200)
    universidad_origen: Optional[str] = Field(None, max_length=200)
    registrado_senescyt: bool = True
    contacto_emergencia: Optional[str] = Field(None, max_length=150)
    telefono_emergencia: Optional[str] = Field(None, max_length=30)

class RequisitoCreate(BaseModel):
    convocatoria_id: int
    nombre: str = Field(min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=500)
    es_obligatorio: bool = True
    formato_permitido: str = Field("pdf", min_length=2, max_length=100)
    tamano_max_mb: int = Field(10, ge=1, le=50)

class RequisitoUpdate(BaseModel):
    nombre: str = Field(min_length=3, max_length=150)
    descripcion: Optional[str] = Field(None, max_length=500)
    es_obligatorio: bool = True
    formato_permitido: str = Field("pdf", min_length=2, max_length=100)
    tamano_max_mb: int = Field(10, ge=1, le=50)

class RequisitoOut(BaseModel):
    id: int
    convocatoria_id: int
    nombre: str
    descripcion: Optional[str]
    es_obligatorio: bool
    formato_permitido: str
    tamano_max_mb: int

    class Config:
        from_attributes = True

class DocumentReview(BaseModel):
    estado_revision: str  # APROBADO, REQUIERE_CORRECCION, RECHAZADO
    observaciones: Optional[str] = Field(None, max_length=1000)
