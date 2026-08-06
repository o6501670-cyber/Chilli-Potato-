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
    '/services/api/services/',
]

# warm up
for url in endpoints:
    client.get(url)

print('Measuring Services Endpoints (warm cache):')
for url in endpoints:
    start = time.time()
    res = client.get(url)
    duration = time.time() - start
    print(f'{url}: {res.status_code} - {duration:.3f} seconds')
