"""Test/CI settings: SQLite database (no MySQL server needed) + in-memory caches.

Usage:
    DJANGO_SETTINGS_MODULE=pos_backend.settings_test python manage.py <command>

Keep this file in sync with settings.py when adding apps/middleware.
"""
import os

os.environ.setdefault('DJANGO_DEBUG', 'True')  # must be set before settings import (guard raises otherwise)
os.environ.setdefault('DB_NAME', 'pos_test')

from .settings import *

DEBUG = True

# Raise throttles in the test environment: the load test fires 15k+ requests
# in minutes, far above the production anon=200/hour, user=10000/hour rates.
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000000/hour',
    'user': '1000000/hour',
    'login': '1000000/hour',
}

# ─── SQLite for local testing (MySQL is the production engine) ────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'test_db.sqlite3'),
        'OPTIONS': {
            # WAL + long busy timeout: lets multiple gunicorn workers read/write
            # concurrently without "database is locked" errors under load.
            'init_command': 'PRAGMA journal_mode=WAL; PRAGMA busy_timeout=30000; PRAGMA synchronous=NORMAL;',
            'transaction_mode': 'IMMEDIATE',
        },
    }
}

# LocMemCache works fine in tests (single process)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pos-backend-test-cache',
    }
}

# In-memory channel layer (already the default; make it explicit for ASGI tests)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    },
}

# The async audit-log middleware writes to the DB from background threads, which
# conflicts with Django TestCase's wrapping transaction on SQLite ("database
# table is locked"). It is exercised separately by the live smoke/load tests.
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'audit_logs.middleware.AuditLogMiddleware']

# Don't write rotated log files during tests
LOGGING['handlers']['file']['filename'] = os.path.join(BASE_DIR, 'django_test.log')

# Email: discard in tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# PASSWORD_HASHERS: fast hasher keeps tests quick
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Allow localhost for the load-test server
ALLOWED_HOSTS = ['*']
