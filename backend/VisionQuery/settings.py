"""Settings for the VisionQuery development project."""
import os
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "pgvector.django",
    "uploads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "VisionQuery.urls"

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
    },
]

WSGI_APPLICATION = "VisionQuery.wsgi.application"
ASGI_APPLICATION = "VisionQuery.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "visionquery"),
        "USER": os.environ.get("POSTGRES_USER", "visionquery"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# This is a local demo project with no auth/login flow: the API is intentionally open,
# and session-based CSRF enforcement is disabled so the bundled demo UI's fetch() calls work.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True

# Frames are selected for future AI processing at this rate; the source video is unchanged.
VIDEO_SAMPLING_TARGET_FPS = float(os.environ.get("VIDEO_SAMPLING_TARGET_FPS", "5"))

# Lightweight adaptive-sampling settings. These never modify the original video.
VIDEO_MOTION_CHECK_FPS = float(os.environ.get("VIDEO_MOTION_CHECK_FPS", "2"))
VIDEO_MOTION_THRESHOLD = float(os.environ.get("VIDEO_MOTION_THRESHOLD", "2"))
VIDEO_ACTIVE_SAMPLING_FPS = float(
    os.environ.get("VIDEO_ACTIVE_SAMPLING_FPS", "10")
)
VIDEO_ACTIVE_WINDOW_SECONDS = float(
    os.environ.get("VIDEO_ACTIVE_WINDOW_SECONDS", "3")
)
VIDEO_PRE_ROLL_SECONDS = float(os.environ.get("VIDEO_PRE_ROLL_SECONDS", "1"))
VIDEO_MOTION_RESIZE_WIDTH = int(os.environ.get("VIDEO_MOTION_RESIZE_WIDTH", "320"))
VIDEO_ADAPTIVE_SAMPLING_DEBUG = (
    os.environ.get("VIDEO_ADAPTIVE_SAMPLING_DEBUG", "false").lower() == "true"
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
