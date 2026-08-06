import os, django, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()

# We need a superuser to access all centers
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("No superuser found.")
    exit()

client = Client()
client.force_login(user)

endpoints = [
    '/salon_admin/api/dashboard/summary/',
    '/salon_admin/api/dashboard/revenues/',
    '/salon_admin/api/dashboard/clients/',
    '/salon_admin/api/dashboard/finance/',
    '/salon_admin/api/dashboard/services_products/',
    '/salon_admin/api/dashboard/staff/',
]

print("Measuring Admin Dashboard Endpoints (cold cache):")
for url in endpoints:
    start = time.time()
    res = client.get(url)
    duration = time.time() - start
    print(f"{url}: {res.status_code} - {duration:.3f} seconds")
    
print("\nMeasuring Admin Dashboard Endpoints (warm cache):")
for url in endpoints:
    start = time.time()
    res = client.get(url)
    duration = time.time() - start
    print(f"{url}: {res.status_code} - {duration:.3f} seconds")
