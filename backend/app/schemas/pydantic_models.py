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
    codigo: str
    nombre: str
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

class ConvocatoriaCreate(BaseModel):
    programa_id: int
    codigo: str
    nombre: str
    fecha_apertura: date
    fecha_cierre: date
    fecha_inicio_preparatorio: date
    fecha_fin_preparatorio: date

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

    class Config:
        from_attributes = True

# --- CURSOS Y ACTIVIDADES ---
class CourseCreate(BaseModel):
    convocatoria_id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    nota_minima: float = 70.0
    ponderacion_total: float = 100.0

class ActivityCreate(BaseModel):
    curso_id: int
    titulo: str
    tipo: str = "INDIVIDUAL"
    instrucciones: Optional[str] = None
    fecha_apertura: datetime
    fecha_limite: datetime
    ponderacion: float
    es_obligatorio: bool = True
    extensiones_permitidas: str = "pdf,zip,docx"
    tamano_max_mb: int = 25
    max_reenvios: int = 3

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
    porcentaje_avance: float = 0.0

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

class MyEnrollmentOut(BaseModel):
    id: int
    convocatoria_id: int
    convocatoria_nombre: str
    programa_nombre: str
    fecha_inscripcion: datetime
    estado_proceso: str
    cursos: List[str] = []

class RequirementUploadResponse(BaseModel):
    id: int
    nombre_original: str
    estado_revision: str
    fecha_carga: datetime

# --- EVIDENCIAS Y EVALUACIONES ---
class EvaluationCreate(BaseModel):
    version_id: int
    puntaje_obtenido: float
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

class FollowupCreate(BaseModel):
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

    class Config:
        from_attributes = True

# --- RIESGOS Y ALERTAS ---
class RiskAlertOut(BaseModel):
    id: int
    inscripcion_id: int
    postulante_nombre: str
    tipo_alerta: str
    nivel_riesgo: str
    motivo_detallado: str
    fecha_deteccion: datetime
    resuelta: bool
    fecha_resolucion: Optional[datetime] = None

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
