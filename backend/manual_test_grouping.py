import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import RequestFactory
from marketing.views import PromotionViewSet
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum

User = get_user_model()
user = User.objects.first()

req = RequestFactory().get('/marketing/api/promotions/usage_report/')
req.user = user

# Let's inspect the modified usage report with center breakdown
from marketing.models import PromotionUsage
usage_qs = PromotionUsage.objects.all()
report = usage_qs.values('promotion', 'center__center_name').annotate(
    usage_count=Count('id'),
    total_revenue=Sum('revenue_generated')
)
print("PROMOTION USAGE WITH CENTER:")
for row in report:
    print(row)

from billing.models import InvoiceItem
from django.contrib.contenttypes.models import ContentType
from marketing.models import ValueCard

card_ct = ContentType.objects.get_for_model(ValueCard)
items = InvoiceItem.objects.filter(invoice__status='paid', content_type=card_ct)
items_agg = items.values('content_type', 'object_id', 'invoice__center__center_name').annotate(
    usage_count=Count('id'),
    total_revenue=Sum('total_price')
)
print("INVOICE ITEMS WITH CENTER:")
for row in items_agg:
    print(row)
