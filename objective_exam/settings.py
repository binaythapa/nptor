# objective_exam/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# SECURITY
# ============================================================
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-please')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

#ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
#ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS.split(',') if h.strip()]

DEBUG = False

ALLOWED_HOSTS = ['nptor.com', 'www.nptor.com']

# ============================================================
# Application definition
# ============================================================
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',                     # Required by allauth

    # Third-party
    'rest_framework',
    'widget_tweaks',
    #'allauth',                                  # ← NEW: django-allauth
    #'allauth.account',                          # ← NEW
    #'allauth.socialaccount',                    # ← NEW (optional, but safe to include)

    # Local
    'quiz',
    'phone_field', 
   
]

SITE_ID = 1  # Required by allauth

# ============================================================
# Middleware
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'allauth.account.middleware.AccountMiddleware',   # ← Required by allauth ≥0.57
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'objective_exam.urls'

# ============================================================
# Templates
# ============================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'quiz.context_processors.unread_notifications_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'objective_exam.wsgi.application'

# ============================================================
# Database
# ============================================================
'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'sales',          # database
        'USER': 'root',           # user
        'PASSWORD': 'root',       # password
        'HOST': 'localhost',      # host
        'PORT': '3306',           # default MySQL port
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}





# ============================================================
# Password validation
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# ============================================================
# Internationalization
# ============================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================
# Static & Media
# ============================================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Authentication & URLs
# ============================================================
LOGIN_URL = 'quiz:login'
LOGIN_REDIRECT_URL = 'quiz:dashboard'
LOGOUT_REDIRECT_URL = 'quiz:login'




# ============================================================
# Custom Authentication Backend (username OR email login)
# ============================================================
AUTHENTICATION_BACKENDS = [
    'quiz.auth_backends.EmailOrUsernameModelBackend',   # ← Your custom one first
    'django.contrib.auth.backends.ModelBackend',
]

# ============================================================
# django-allauth Configuration (CRITICAL)
# ============================================================
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'   # Login with username OR email
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'           # Change to 'mandatory' later if needed
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_SESSION_REMEMBER = True                   # "Remember me" default = True
ACCOUNT_LOGOUT_ON_GET = True                      # Instant logout without confirmation
ACCOUNT_FORMS = {}                                # You can override forms here later

# Optional: nicer URLs (remove /accounts/ prefix)
ACCOUNT_URLS_PREFIX = ''  # Makes /login/, /signup/, /logout/ work directly

# ============================================================
# Email Backend (console for dev)
# ============================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@objectiveexam.com'

# ============================================================
# REST Framework
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
}

# ============================================================
# Misc
# ============================================================
SITE_NAME = os.environ.get('SITE_NAME', 'Objective Exam')

# ============================================================
# Logging
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}



EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tbinay5@gmail.com'
EMAIL_HOST_PASSWORD = 'ykex bzxs lesd zwke'  # ← no quotes if spaces
DEFAULT_FROM_EMAIL = 'Gharchaiyo <tbinay5@gmail.com>'