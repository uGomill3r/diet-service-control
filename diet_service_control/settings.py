"""
Configuración principal del proyecto DietServiceControl.
Compatible con Django 5.2 + PostgreSQL 17 y despliegue con Docker Compose.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Seguridad
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-cambia-esto-en-produccion")
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Entorno de ejecución: 'local' en desarrollo, 'production' en Render
# True cuando el proceso corre en Render (inyecta RENDER=true automáticamente)
IS_RENDER = os.environ.get("RENDER") == "true"

# Aplicaciones
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps propias
    "apps.core",
    "apps.auth_app",
    "apps.dashboard",
    "apps.mes",
    "apps.semana",
    "apps.dia",
    "apps.pagos",
    "apps.reportes",
    "apps.log",
    "apps.importar",
]

# Messages backend para sesiones sin django.contrib.auth completo
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

_whitenoise_middleware = (
    ["whitenoise.middleware.WhiteNoiseMiddleware"]
    if IS_RENDER
    else []
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    *_whitenoise_middleware,  # solo en producción (Render)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "diet_service_control.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "environment": "diet_service_control.jinja2.environment",
            # Inyecta 'request', 'user', 'messages' en cada template
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "diet_service_control.wsgi.application"

# Base de datos PostgreSQL 17
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "diet_service_control"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Internacionalización
LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Compresión y cache via WhiteNoise en Render; en local usa el backend estándar de Django
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
    if IS_RENDER
    else "django.contrib.staticfiles.storage.StaticFilesStorage"
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sesiones almacenadas en la base de datos
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 horas

# Credencial de administrador desde variables de entorno
APP_USER = os.environ.get("APP_USER", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin123")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}