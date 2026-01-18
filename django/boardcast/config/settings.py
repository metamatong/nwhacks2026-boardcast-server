from pathlib import Path
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",
    "channels",

    "rooms",
    "realtime",
    "media_ingest",
    "intelligence",
    "digitization",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://www.boardcast.tech",
    "https://boardcast.tech",
]
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)

ROOT_URLCONF = "config.urls"

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
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# ---- Database ----
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR/'db.sqlite3'}")
}

# ---- Static/Media ----
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "uploaded_media"

USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)
if USE_S3_STORAGE:
    INSTALLED_APPS += ["storages"]

    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default=None)
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=True)

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    else:
        MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"

# ---- DRF ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# ---- Channels ----
ASGI_APPLICATION = "config.asgi.application"
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# ---- Celery (optional) ----
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# ---- TURN config for ICE endpoint ----
TURN_HOST = env("TURN_HOST", default="localhost")
TURN_PORT = env("TURN_PORT", default="3478")
TURN_REALM = env("TURN_REALM", default="localhost")
TURN_STATIC_AUTH_SECRET = env("TURN_STATIC_AUTH_SECRET", default="change-me")

# ---- Janus SFU ----
JANUS_URL = env("JANUS_URL", default="")
JANUS_API_SECRET = env("JANUS_API_SECRET", default="")
JANUS_ADMIN_KEY = env("JANUS_ADMIN_KEY", default="")
JANUS_TIMEOUT_SECONDS = env.int("JANUS_TIMEOUT_SECONDS", default=5)
JANUS_PUBLIC_URL = env("JANUS_PUBLIC_URL", default=JANUS_URL)

# ---- Intelligence (STT + LLM) ----
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY", default="")
ELEVENLABS_STT_URL = env("ELEVENLABS_STT_URL", default="https://api.elevenlabs.io/v1/speech-to-text")
ELEVENLABS_STT_MODEL_ID = env("ELEVENLABS_STT_MODEL_ID", default="scribe_v2")
ELEVENLABS_STT_LANGUAGE_CODE = env("ELEVENLABS_STT_LANGUAGE_CODE", default="")
ELEVENLABS_STT_DIARIZE = env.bool("ELEVENLABS_STT_DIARIZE", default=False)
ELEVENLABS_STT_FILE_FIELD = env("ELEVENLABS_STT_FILE_FIELD", default="audio")

GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_BASE_URL = env("GEMINI_BASE_URL", default="https://generativelanguage.googleapis.com/v1beta")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-1.5-flash")
GEMINI_MIN_CONFIDENCE = env.float("GEMINI_MIN_CONFIDENCE", default=0.55)

TRANSCRIPT_CONTEXT_MAX_CHUNKS = env.int("TRANSCRIPT_CONTEXT_MAX_CHUNKS", default=20)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Digitization ----
DIGITIZATION_DEFAULT_EXPECTED_FRAMES = env.int("DIGITIZATION_DEFAULT_EXPECTED_FRAMES", default=9)
DIGITIZATION_MAX_FRAME_BYTES = env.int("DIGITIZATION_MAX_FRAME_BYTES", default=3_000_000)
DIGITIZATION_ALLOWED_MIME_TYPES = env.list(
    "DIGITIZATION_ALLOWED_MIME_TYPES",
    default=["image/jpeg", "image/png", "image/webp"],
)
DIGITIZATION_MODEL_PATH = env(
    "DIGITIZATION_MODEL_PATH",
    default=str(BASE_DIR / "legacy" / "yolov8n-seg.pt"),
)
DIGITIZATION_AUTO_TRIGGER = env.bool("DIGITIZATION_AUTO_TRIGGER", default=False)
