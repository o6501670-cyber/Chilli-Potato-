import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from billing.models import Invoice

qs = Invoice.objects.filter(created_at__year=2026, created_at__month=2)
print("Feb count:", qs.count())
if qs.exists():
    print("Feb min:", qs.order_by("created_at").first().created_at)
    print("Feb max:", qs.order_by("-created_at").first().created_at)
