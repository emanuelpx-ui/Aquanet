"""
config/settings.py
Configuración de AquaNet Puebla por entorno (desarrollo / producción).
Los valores se leen de variables de entorno definidas en .env
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuración base compartida por todos los entornos."""

    # ── Flask ──────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

    # ── Base de datos ──────────────────────────────────────────
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("DB_NAME", "aquanet_puebla")
    DB_USER     = os.getenv("DB_USER", "aquanet_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    @property
    def DATABASE_URL(self):
        return (
            os.getenv("DATABASE_URL")
            or f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
               f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Uploads ────────────────────────────────────────────────
    UPLOAD_FOLDER       = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
    MAX_CONTENT_LENGTH  = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    ALLOWED_EXTENSIONS  = {"jpg", "jpeg", "png", "webp"}

    # ── Sesiones ───────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=int(os.getenv("SESSION_LIFETIME_HOURS", 8))
    )
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    LOCKOUT_MINUTES    = int(os.getenv("LOCKOUT_MINUTES", 15))

    # ── Scheduler ─────────────────────────────────────────────
    SCHEDULER_ENABLED              = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    PRIORITY_RECALC_INTERVAL_MINUTES = int(
        os.getenv("PRIORITY_RECALC_INTERVAL_MINUTES", 60)
    )

    # ── WTF / CSRF ─────────────────────────────────────────────
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    DB_NAME = "aquanet_test"


# Mapa de entornos
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}

def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)()
