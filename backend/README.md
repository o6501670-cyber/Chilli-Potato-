# POS backend

## Local development

The backend defaults to SQLite while `DJANGO_DEBUG=True`, so it can be started without a local MySQL server:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

Set `DB_ENGINE=django.db.backends.mysql` and the `DB_*` variables in `.env` when using MySQL.

## Production requirements

- Set `DJANGO_DEBUG=False`, a new `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`.
- Set `DB_ENGINE=django.db.backends.mysql` and use a least-privilege database user; do not use the example `root/root` values.
- Configure Redis with `REDIS_URL` so throttling and cache state are shared by Gunicorn workers.
- Run `collectstatic`, serve the Angular build and Django API behind one HTTPS origin, and terminate TLS at the reverse proxy.
- Run migrations during deployment and take a database backup before each migration.
- Schedule `sync_staff_transfers_and_tools` and `expire_perks`; monitor 5xx responses, database locks, failed payment/refund attempts, and stock adjustments.

The API uses expiring DRF tokens (30 days by default), server-side role/action permissions, transaction-protected checkout/refund flows, and immutable invoice/stock audit records.
