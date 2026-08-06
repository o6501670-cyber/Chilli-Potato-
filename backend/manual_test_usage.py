import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import RequestFactory
from marketing.views import PromotionViewSet
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

req = RequestFactory().get('/marketing/api/promotions/usage_report/', HTTP_CENTER_ID='null')
req.user = user

view = PromotionViewSet.as_view({'get': 'usage_report'})

try:
    res = view(req)
    print("STATUS", res.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
