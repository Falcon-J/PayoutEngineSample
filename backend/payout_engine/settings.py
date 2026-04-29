import os
from pathlib import Path

from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

def env_flag(*names: str, default: bool = False) -> bool:
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-secret")
DEBUG = env_flag("DJANGO_DEBUG", "DEBUG", default=True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["*"] if DEBUG else [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "payout_engine.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "payout_engine.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "payout"),
        "USER": os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST") or os.getenv("PGHOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT") or os.getenv("PGPORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])
CORS_ALLOW_HEADERS = list(dict.fromkeys([*default_headers, *env_list("CORS_ALLOW_HEADERS", [])]))

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# Celery prefork pool is unstable/unsupported on Windows. Force solo mode for local dev.
if os.name == "nt":
    CELERY_WORKER_POOL = "solo"
    CELERY_WORKER_CONCURRENCY = 1

CELERY_BEAT_SCHEDULE = {
    "process-pending-payouts": {
        "task": "core.tasks.process_pending_payouts_task",
        "schedule": 5.0,
    },
    "retry-stuck-payouts": {
        "task": "core.tasks.retry_stuck_payouts_task",
        "schedule": 10.0,
    },
}
