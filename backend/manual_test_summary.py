import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from salon_admin.dashboard_endpoints import dashboard_summary

User = get_user_model()
user = User.objects.filter(role__name__iexact='owner').first()

rf = RequestFactory()
req = rf.get('/api/dashboard/summary/', {'start_date': '2026-07-01', 'end_date': '2026-07-19'})
req.user = user

try:
    res = dashboard_summary(req)
    print("STATUS:", res.status_code)
    print("DATA:", res.data)
except Exception as e:
    import traceback
    traceback.print_exc()
