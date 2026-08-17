"""Production Gunicorn defaults; override every value with environment variables."""

import multiprocessing
import os

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', min(8, multiprocessing.cpu_count() * 2 + 1)))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(os.environ.get('GUNICORN_THREADS', '8'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '60'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '5000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '500'))
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'warning')
capture_output = True
