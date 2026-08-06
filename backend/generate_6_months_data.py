import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from clients.models import Client, ClientValueCard, ClientMembership, ClientPackage
from staff.models import StaffMember
from salon_admin.models import Center
from inventory.models import Product
from services.models import ServiceMaster
from billing.models import Invoice, InvoiceItem, Payment
from marketing.models import ValueCard, Membership, Package, Promotion
from billing.services import finalize_invoice

# Constants
DAYS_TO_GENERATE = 180
END_DATE = datetime.now().date()
START_DATE = END_DATE - timedelta(days=DAYS_TO_GENERATE)

print(f"Starting mass generation from {START_DATE} to {END_DATE} ({DAYS_TO_GENERATE} days).")

centers = list(Center.objects.all())
if not centers:
    print("No centers found. Aborting.")
    exit()

all_staff = list(StaffMember.objects.filter(is_active=True))
all_clients = list(Client.objects.all())
all_services = list(ServiceMaster.objects.all())
all_products = list(Product.objects.filter(is_active=True, price__gt=0))
all_value_cards = list(ValueCard.objects.all())
all_memberships = list(Membership.objects.all())

svc_ct = ContentType.objects.get_for_model(ServiceMaster)
prod_ct = ContentType.objects.get_for_model(Product)
vc_ct = ContentType.objects.get_for_model(ValueCard)
mem_ct = ContentType.objects.get_for_model(Membership)

if not all_staff:
    print("Creating 2 dummy staff...")
    for i in range(2):
        s = StaffMember.objects.create(
            first_name=f"DummyStaff_{i}",
            phone=f"80000000{i:02d}",
            center=centers[0],
            is_active=True
        )
        all_staff.append(s)

if not all_services:
    print("Creating 3 dummy services...")
    for i in range(3):
        s = ServiceMaster.objects.create(
            name=f"DummyService_{i}",
            default_price=Decimal("500.00"),
            duration_mins=30
        )
        all_services.append(s)

if not all_clients:
    print("Creating 10 dummy clients...")
    for i in range(10):
        all_clients.append(Client.objects.create(
            first_name=f"GeneratedClient_{i}",
            phone=f"90000000{i:02d}",
            center=centers[0]
        ))

# Metrics
total_invoices = 0
total_revenue = 0

print(f"Loaded {len(centers)} centers, {len(all_staff)} staff, {len(all_services)} services, {len(all_products)} products.")

def get_random_items():
    items = []
    # Always at least 1 service
    svc = random.choice(all_services)
    items.append({
        'content_type': svc_ct,
        'object_id': svc.id,
        'obj': svc,
        'price': Decimal(str(svc.default_price or random.randint(300, 1500))),
        'desc': svc.name,
        'type': 'service'
    })
    
    # 30% chance for a product
    if all_products and random.random() < 0.3:
        prod = random.choice(all_products)
        items.append({
            'content_type': prod_ct,
            'object_id': prod.id,
            'obj': prod,
            'price': Decimal(str(prod.price or random.randint(100, 500))),
            'desc': prod.name,
            'type': 'product'
        })
        
    # 5% chance for value card
    if all_value_cards and random.random() < 0.05:
        vc = random.choice(all_value_cards)
        items.append({
            'content_type': vc_ct,
            'object_id': vc.id,
            'obj': vc,
            'price': Decimal(str(vc.price or 5000)),
            'desc': vc.name,
            'type': 'card'
        })
        
    # 5% chance for membership
    if all_memberships and random.random() < 0.05:
        mem = random.choice(all_memberships)
        items.append({
            'content_type': mem_ct,
            'object_id': mem.id,
            'obj': mem,
            'price': Decimal(str(mem.price or 1000)),
            'desc': mem.name,
            'type': 'membership'
        })
        
    return items

def make_invoice_for_day(date_obj, center):
    staff_for_center = [s for s in all_staff if s.center_id == center.id]
    if not staff_for_center:
        staff_for_center = all_staff
        
    staff = random.choice(staff_for_center)
    client = random.choice(all_clients)
    
    items = get_random_items()
    subtotal = sum(i['price'] for i in items)
    
    # Random discount 10% chance
    discount = Decimal('0')
    if random.random() < 0.1:
        discount = round(subtotal * Decimal('0.10'), 2)
        
    cgst = round((subtotal - discount) * Decimal('0.09'), 2)
    sgst = round((subtotal - discount) * Decimal('0.09'), 2)
    total = (subtotal - discount) + cgst + sgst
    
    # Create Invoice
    inv = Invoice(
        center=center,
        client=client,
        staff=staff,
        subtotal=subtotal,
        discount=discount,
        cgst=cgst,
        sgst=sgst,
        total_amount=total,
        paid_amount=total,
        status='paid'
    )
    inv.save()
    # Force backdate
    Invoice.objects.filter(id=inv.id).update(created_at=date_obj)
    
    for i in items:
        # Create InvoiceItem
        ii = InvoiceItem(
            invoice=inv,
            content_type=i['content_type'],
            object_id=i['object_id'],
            description=i['desc'],
            unit_price=i['price'],
            discount=0,
            quantity=1,
            tax_percentage=18.0,
            staff=staff
        )
        ii.save()
        ii.staff_members.add(staff)
        
    # Payment (Cash)
    pmt = Payment(
        invoice=inv,
        payment_method='Cash',
        amount=total
    )
    pmt.save()
    Payment.objects.filter(id=pmt.id).update(created_at=date_obj)
    
    # Finalize (creates logs, ledgers, wallets, stocks)
    try:
        finalize_invoice(inv)
        from staff.models import ServiceLog
        from inventory.models import StockTransaction
        from billing.models import AdvancePayment, CashbackTransaction
        from clients.models import ClientValueCard, ClientMembership
        ServiceLog.objects.filter(invoice=inv).update(created_at=date_obj)
        StockTransaction.objects.filter(notes__contains=f"#{inv.id}").update(created_at=date_obj)
        CashbackTransaction.objects.filter(invoice=inv).update(created_at=date_obj)
        AdvancePayment.objects.filter(invoice=inv).update(created_at=date_obj)
    except Exception as e:
        print(f"Error finalizing: {e}")
        
    return total

curr_date = START_DATE
while curr_date <= END_DATE:
    dt_obj = datetime.combine(curr_date, datetime.min.time()) + timedelta(hours=random.randint(10, 18))
    for center in centers:
        daily_count = random.randint(2, 6)
        for _ in range(daily_count):
            try:
                with transaction.atomic():
                    rev = make_invoice_for_day(dt_obj, center)
                    total_revenue += rev
                    total_invoices += 1
            except Exception as e:
                pass
    curr_date += timedelta(days=1)

print(f"\nGENERATION COMPLETE!")
print(f"Total Invoices Generated: {total_invoices}")
print(f"Total Revenue Generated: {total_revenue}")
