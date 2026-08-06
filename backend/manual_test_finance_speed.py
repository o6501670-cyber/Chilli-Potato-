import os, django, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.filter(is_superuser=True).first()
if not user:
    exit()

client = Client(HTTP_HOST='localhost')
client.force_login(user)

endpoints = [
    '/finance/api/petty-cash/',
    '/finance/api/daily-closings/',
    '/finance/api/shifts/',
    '/finance/api/incentive-rules/',
    '/finance/api/incentive-configs/',
    '/finance/api/reports/detailed-revenues/',
    '/finance/api/reports/refunds/',
    '/finance/api/reports/procurement/',
    '/finance/api/reports/tax/',
    '/finance/api/reports/staff-performance/',
]

# warm up
for url in endpoints:
    client.get(url)

print('Measuring Finance Endpoints (warm cache):')
for url in endpoints:
    start = time.time()
    res = client.get(url)
    duration = time.time() - start
    print(f'{url}: {res.status_code} - {duration:.3f} seconds')
