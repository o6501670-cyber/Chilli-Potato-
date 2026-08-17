"""
Django settings for pos_backend project.
Split into dev/prod via DJANGO_ENV environment variable.
"""

from pathlib import Path
import os
import logging.handlers
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(os.path.join(BASE_DIR, '.env'))

# ─── Core ──────────────────────────────────────────────────────────────────────
_INSECURE_KEY = 'django-insecure-9k^bakokugv8=6u^h4&e0br9#aj2yf^oo3#anie*o6v(v_!0g3'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', _INSECURE_KEY)

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').strip().lower() == 'true'

# Guard: refuse to start in production with the insecure fallback key
if not DEBUG and SECRET_KEY == _INSECURE_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable must be set to a strong random value "
        "when DEBUG=False. Do not use the default insecure key in production."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        '38.45.94.56,localhost,127.0.0.1,testserver',
    ).split(',')
    if host.strip()
]

# ─── Installed Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    # Local apps
    'accounts',
    'salon_admin',
    'inventory',
    'marketing',
    'staff',
    'appointments',
    'clients',
    'services',
    'billing',
    'finance',
    'audit_logs',
]

# ─── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.ExpiringTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'pos_backend.pagination.OptionalPagination',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '200/hour',       # bumped from 100/day — more realistic for walk-in usage
        'user': '10000/hour',     # 10K/hour per user (handles staff with many API calls)
    },
    # Return proper 401 instead of 403 for unauthenticated requests
    'UNAUTHENTICATED_USER': None,
}

# ─── Cache (Redis for production, in-memory fallback for dev) ──────────────────
# Install for production: pip install django-redis redis
_redis_url = os.environ.get('REDIS_URL', '')
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': _redis_url,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
                'MAX_CONNECTIONS': 1000,
            },
        }
    }
    # Use Redis for DRF throttling so counters persist across Gunicorn workers/restarts
    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ]
else:
    # Dev fallback: in-memory cache (NOT shared across workers)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'pos-backend-cache',
        }
    }

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',      # must be first
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files efficiently
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit_logs.middleware.AuditLogMiddleware',
]

# ─── CORS ──────────────────────────────────────────────────────────────────────
# In production: lock down to explicit origins via CORS_ALLOWED_ORIGINS env var.
# In development: allow all for convenience.
_cors_origins_env = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if not DEBUG:
    if _cors_origins_env:
        CORS_ALLOW_ALL_ORIGINS = False
        CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_env.split(',') if o.strip()]
    else:
        # Fallback: still restrict but log a warning
        CORS_ALLOW_ALL_ORIGINS = False
        CORS_ALLOWED_ORIGINS = [
            'http://38.45.94.56:4092',
            'http://38.45.94.56:8092',
            'http://38.45.94.56:3093',
            'http://38.45.94.56:4093',
        ]
else:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'dnt', 'origin', 'user-agent', 'x-csrftoken', 'x-requested-with',
    'cache-control', 'pragma', 'expires', 'x-staff-token', 'x-client-token',
    'x-background-request',
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'http://38.45.94.56:4092,http://38.45.94.56:8092,http://38.45.94.56:3093,http://38.45.94.56:4093,http://localhost:4200,http://localhost:8000',
    ).split(',')
    if origin.strip()
]

# ─── Security Headers (only enforce in production) ────────────────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

API_TOKEN_MAX_AGE_DAYS = int(os.environ.get('API_TOKEN_MAX_AGE_DAYS', '7'))
APP_TOKEN_MAX_AGE_DAYS = int(os.environ.get('APP_TOKEN_MAX_AGE_DAYS', '30'))

# Bound parser memory use; individual bulk-upload endpoints also reject files
# above this limit before pandas/openpyxl processes them.
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DATA_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_MEMORY_SIZE', str(5 * 1024 * 1024)))

# Forwarded client IPs are trusted only when deployment explicitly guarantees
# that its reverse proxy strips client-supplied X-Forwarded-For headers.
AUDIT_LOG_ENABLED = os.environ.get('AUDIT_LOG_ENABLED', 'True').lower() == 'true'
AUDIT_TRUST_X_FORWARDED_FOR = os.environ.get('AUDIT_TRUST_X_FORWARDED_FOR', 'False').lower() == 'true'
# External IP geolocation is opt-in to avoid request metadata leakage and an
# outbound network dependency under load.
AUDIT_GEO_LOOKUP_ENABLED = os.environ.get('AUDIT_GEO_LOOKUP_ENABLED', 'False').lower() == 'true'

# ─── URL / Templates / WSGI ───────────────────────────────────────────────────
ROOT_URLCONF = 'pos_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'pos_backend.wsgi.application'

# ─── Database ─────────────────────────────────────────────────────────────────
# DATABASE_URL makes local/CI SQLite testing possible without changing the
# production MySQL default. Examples:
#   sqlite:////tmp/pos.sqlite3
#   mysql://user:password@db:3306/pos
_database_url = os.environ.get('DATABASE_URL', '').strip()
if _database_url:
    import dj_database_url

    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'pos'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'root'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            'CONN_HEALTH_CHECKS': True,
        }
    }

# ─── Password Validation ──────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'    # IST — important for Indian salon timestamps
USE_I18N = True
USE_TZ = False

# ─── Static & Media Files ─────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')   # collectstatic output dir

# FIXED: STATICFILES_STORAGE was deprecated in Django 4.2 — use STORAGES dict
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ─── Logging ──────────────────────────────────────────────────────────────────
# FIXED: Use RotatingFileHandler so django.log never grows unbounded (was 517 KB already)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5 MB per file
            'backupCount': 5,              # keep up to 5 rotated files
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'billing': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ─── Misc ─────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.CustomUser'

# ─── Email Configuration ──────────────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Chilli Potato <noreply@chillipotato.com>')