import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from staff.models import StaffMember
from django.db.models import Count
stats = StaffMember.objects.values('center__center_name').annotate(cnt=Count('id')).order_by('-cnt')
for stat in stats:
    print(f"{stat['center__center_name']}: {stat['cnt']} staff")
