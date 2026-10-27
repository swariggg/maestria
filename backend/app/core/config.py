import os
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "APP - Maestría UIDE"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = (
        "mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3B"
        "Server%3Dlocalhost%3BDatabase%3Dapp_maestria%3B"
        "Trusted_Connection%3Dyes%3BTrustServerCertificate%3Dyes%3B"
    )

    # JWT Security
    SECRET_KEY: str = "uide_super_secret_jwt_key_preparatorios_posgrados_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Storage
    STORAGE_DIR: str = str(BASE_DIR.parent / "storage" / "private")
    MAX_UPLOAD_SIZE_MB: int = 50

    # SMTP Notifications
    SMTP_TEST_MODE: bool = True
    SMTP_SERVER: str = "smtp.uide.edu.ec"
    SMTP_PORT: int = 587
    SMTP_USER: str = "notificaciones@uide.edu.ec"
    SMTP_PASSWORD: str = "test_password"
    SMTP_FROM: str = "maestrias.admision@uide.edu.ec"

    # Business Rules
    DIAS_INACTIVIDAD_RIESGO: int = 7
    INTENTOS_SIN_RESPUESTA_ALERTA: int = 2
    TIMEZONE: str = "America/Guayaquil"

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()

# Garantizar directorios privados
os.makedirs(os.path.join(settings.STORAGE_DIR, "evidencias"), exist_ok=True)
os.makedirs(os.path.join(settings.STORAGE_DIR, "documentos"), exist_ok=True)
