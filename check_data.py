import os, sys, django
sys.path.append('c:\\Users\\Dell\\OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED\\Desktop\\latest chowmein\\chowmein\\chowmein\\chowmein\\chowmein\\properback\\FINAL_POS_CODE_two\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from clients.models import Client
from salon_admin.models import Invoice

print(f"Total Clients: {Client.objects.count()}")
print(f"Total Invoices: {Invoice.objects.count()}")

invoices = Invoice.objects.filter(status__in=['paid', 'partial'])
print(f"Paid Invoices: {invoices.count()}")

if invoices.exists():
    print(f"First invoice date: {invoices.order_by('created_at').first().created_at}")
    print(f"Last invoice date: {invoices.order_by('-created_at').first().created_at}")
