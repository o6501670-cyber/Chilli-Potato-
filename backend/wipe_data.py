import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from billing.models import Invoice, InvoiceItem, Payment, AdvancePayment, BillChangeLog, CashbackTransaction
from appointments.models import Appointment
from clients.models import Client, ClientMembership, ClientPackage, ClientValueCard
from staff.models import StaffMember, ServiceLog
from services.models import ServiceMaster
from inventory.models import Product

print("Deleting data...")
Invoice.objects.all().delete()
InvoiceItem.objects.all().delete()
Payment.objects.all().delete()
AdvancePayment.objects.all().delete()
BillChangeLog.objects.all().delete()
CashbackTransaction.objects.all().delete()
Appointment.objects.all().delete()
ClientMembership.objects.all().delete()
ClientPackage.objects.all().delete()
ClientValueCard.objects.all().delete()
Client.objects.all().delete()
ServiceLog.objects.all().delete()
StaffMember.objects.all().delete()
ServiceMaster.objects.all().delete()
Product.objects.all().delete()
print("Data wiped successfully!")
