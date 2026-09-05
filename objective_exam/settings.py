# objective_exam/settings.py
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ============================================================
# BASE DIRECTORY
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Load the project-root .env explicitly for local/dev. This avoids relying on
# the process working directory when Django is started from an IDE or another
# directory. Production deployments should provide environment variables.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


# ============================================================
# MISC
# ============================================================
SITE_NAME = os.environ.get("SITE_NAME", "nptor.com")
SITE_URL = "https://nptor.com"
SITE_ID = 1

# ============================================================
# SECURITY
# ============================================================
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in the environment.")

if DEBUG:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
else:
    ALLOWED_HOSTS = ["nptor.com", "www.nptor.com"]

CSRF_TRUSTED_ORIGINS = [
    "https://nptor.com",
    "https://www.nptor.com",
]


# ============================================================
# APPLICATION DEFINITION
# ============================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "rest_framework",
    "widget_tweaks",
    "phone_field",
    "django_countries",
    "ckeditor",
    "ckeditor_uploader",
    "django_ratelimit",

    # Apps
    "quiz.apps.QuizConfig",
    "courses",
    "accounts",
    "pages",
    "organizations",
    "subscriptions",
    "payments",
    "cv.apps.CVConfig",
]


# ============================================================
# MIDDLEWARE
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "organizations.middleware.ActiveOrganizationMiddleware",
]


# ============================================================
# URL / WSGI
# ============================================================
ROOT_URLCONF = "objective_exam.urls"
WSGI_APPLICATION = "objective_exam.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "quiz.context_processors.unread_notifications_count",
                "pages.context_processors.site_globals,
            ],
        },
    },
]


# ============================================================
# DATABASE (safe for Passenger)
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "nptor_local"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": "3306",
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ============================================================
# SESSIONS (PRODUCTION SAFE + OTP SAFE)
# ============================================================
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 2   # 2 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"


# ============================================================
# SECURITY HEADERS
# ============================================================
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"


# ============================================================
# STATIC & MEDIA FILES
# ============================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

if DEBUG:
    MEDIA_ROOT = BASE_DIR / "media"
else:
    MEDIA_ROOT = Path("/home/nptorcom/public_html/media")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

CKEDITOR_UPLOAD_PATH = "uploads/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CKEDITOR_ALLOW_NONIMAGE_FILES = True

# ============================================================
# AUTHENTICATION
# ============================================================
LOGIN_URL = "accounts:request-login-otp"
LOGIN_REDIRECT_URL = "quiz:dashboard"
LOGOUT_REDIRECT_URL = "accounts:request-login-otp"

AUTHENTICATION_BACKENDS = [
    "quiz.auth_backends.EmailOrUsernameModelBackend",
    "django.contrib.auth.backends.ModelBackend",
]


# ============================================================
# EMAIL (OTP)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "contact.nptor@gmail.com").strip()

# Prefer EMAIL_HOST_PASSWORD. GMAIL_APP_PASSWORD is supported as an explicit
# local/dev alias. Gmail App Passwords are often copied with spaces, so strip
# whitespace before handing the credential to smtplib.
EMAIL_HOST_PASSWORD = (
    os.environ.get("EMAIL_HOST_PASSWORD")
    or os.environ.get("GMAIL_APP_PASSWORD")
    or ""
).strip().replace(" ", "")

if not EMAIL_HOST_PASSWORD:
    raise RuntimeError(
        "EMAIL_HOST_PASSWORD (or GMAIL_APP_PASSWORD) must be set for Gmail SMTP. "
        "Use a Gmail App Password, not the normal Gmail account password."
    )

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    f"NPTOR <{EMAIL_HOST_USER}>",
).strip()


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}


# ============================================================
# CACHE (cPanel-safe, OTP-safe)
# ============================================================
if DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "dev-cache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "prod-cache",
        }
    }

RATELIMIT_USE_CACHE = "default"


# ============================================================
# LOGGING (AUTO-ROTATING, NO TERMINAL FREEZE)
# ============================================================
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
        },
    },

    "handlers": {
        "app_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "standard",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "errors.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "standard",
        },
    },

    "loggers": {
        "django": {
            "handlers": ["app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


# ============================================================
# BUSINESS CONSTANTS
# ============================================================
BASICS_ANON_LIMIT = 10
EXPRESS_ANON_LIMIT = 10
RETAKE_COOLDOWN_MINUTES = 240
QUESTION_AUTO_DISABLE_THRESHOLD = 3

SILENCED_SYSTEM_CHECKS = [
    "django_ratelimit.E003",
    "django_ratelimit.W001",
]


# ============================================================
# CKEDITOR
# ============================================================
CKEDITOR_ALLOW_NONIMAGE_FILES = True
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_UPLOAD_PATH = "lesson_uploads/"

CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "height": 400,
        "width": "auto",
        "extraPlugins": ",".join([
            "uploadimage",
            "image2",
            "codesnippet",
            "autogrow",
        ]),
        "removePlugins": "stylesheetparser",
        "toolbar_Custom": [
            ["Format", "Font", "FontSize"],
            ["Bold", "Italic", "Underline", "Strike"],
            ["TextColor", "BGColor"],
            ["NumberedList", "BulletedList"],
            ["Outdent", "Indent"],
            ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            ["Link", "Unlink"],
            ["Image", "UploadImage", "Table"],
            ["HorizontalRule", "Smiley", "SpecialChar"],
            ["CodeSnippet"],
            ["RemoveFormat"],
            ["Undo", "Redo"],
        ],
        "codeSnippet_theme": "monokai_sublime",
    }
}
