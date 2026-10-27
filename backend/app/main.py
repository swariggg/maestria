from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Routers
from app.api.v1.auth import router as auth_router
from app.api.v1.programs import router as programs_router
from app.api.v1.courses import router as courses_router
from app.api.v1.applicants import router as applicants_router
from app.api.v1.evidences import router as evidences_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.tutors import router as tutors_router
from app.api.v1.followups import router as followups_router
from app.api.v1.risks import router as risks_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.reports import router as reports_router
from app.api.v1.audit import router as audit_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio: encender scheduler en segundo plano
    start_scheduler()
    yield
    # Parada: apagar scheduler
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API REST del Sistema de Gestión de Cursos Preparatorios para Programas de Maestría - UIDE",
    lifespan=lifespan
)

# CORS Middleware (Soporte para cookies y solicitudes cruzadas)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(programs_router, prefix=api_v1_prefix)
app.include_router(courses_router, prefix=api_v1_prefix)
app.include_router(applicants_router, prefix=api_v1_prefix)
app.include_router(evidences_router, prefix=api_v1_prefix)
app.include_router(evaluations_router, prefix=api_v1_prefix)
app.include_router(tutors_router, prefix=api_v1_prefix)
app.include_router(followups_router, prefix=api_v1_prefix)
app.include_router(risks_router, prefix=api_v1_prefix)
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(reports_router, prefix=api_v1_prefix)
app.include_router(audit_router, prefix=api_v1_prefix)

@app.get("/")
def root():
    return {
        "sistema": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "institucion": "Universidad Internacional del Ecuador (UIDE)",
        "estado": "Operativo",
        "docs": "/docs"
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "database": "connected", "scheduler": "running"}
