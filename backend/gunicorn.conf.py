"""Gunicorn production defaults; environment variables may override these."""

import os

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('WEB_CONCURRENCY', '4'))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
graceful_timeout = 30
keepalive = 5
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '2000'))
max_requests_jitter = 200
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
preload_app = False
