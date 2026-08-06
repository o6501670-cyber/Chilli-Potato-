import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

c = Client()
c.force_login(user)

res = c.get('/marketing/api/promotions/usage_report/')
print(res.status_code)
if res.status_code == 500:
    print(res.content)
