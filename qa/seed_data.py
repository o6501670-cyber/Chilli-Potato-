#!/usr/bin/env python
"""Seed a realistic dataset into the test database for smoke + load testing.

Run with:
    DJANGO_SETTINGS_MODULE=pos_backend.settings_test python qa/seed_data.py
(from the backend/ directory)
"""
import os
import random
import sys
from datetime import date, datetime, timedelta

import django

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'backend'))
sys.path.insert(0, REPO_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings_test')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from salon_admin.models import Center, Role
from staff.models import Designation, StaffMember, ServiceLog
from services.models import ServiceMaster, CenterService
from clients.models import Client, ClientMembership, ClientValueCard
from inventory.models import Vendor, Product, ProductLot
from appointments.models import Appointment, AppointmentService
from billing.models import Invoice, InvoiceItem, Payment, AdvancePayment
from marketing.models import Promotion, ValueCard, Membership, Package
from finance.models import PettyCashEntry, DailyClosing, Shift

random.seed(42)

User = get_user_model()

SERVICES = [
    ('Haircut', 'Hair', 'Men', 350, 30),
    ('Haircut Women', 'Hair', 'Women', 900, 45),
    ('Hair Colour Global', 'Hair', 'Colour', 2500, 120),
    ('Facial Gold', 'Skin', 'Facial', 1500, 60),
    ('Cleanup', 'Skin', 'Facial', 600, 45),
    ('Manicure', 'Nails', 'Hands', 500, 40),
    ('Pedicure', 'Nails', 'Feet', 700, 45),
    ('Head Massage', 'Massage', 'Head', 400, 30),
    ('Full Body Massage', 'Massage', 'Body', 1800, 90),
    ('Bridal Makeup', 'Makeup', 'Bridal', 8000, 180),
    ('Party Makeup', 'Makeup', 'Party', 2500, 60),
    ('Keratin Treatment', 'Hair', 'Treatment', 3500, 150),
]

PRODUCTS = [
    ('Shampoo 250ml', 'Loreal', 'Hair Care', 450),
    ('Conditioner 200ml', 'Loreal', 'Hair Care', 520),
    ('Hair Serum', 'Streax', 'Hair Care', 380),
    ('Face Wash', 'Cetaphil', 'Skin Care', 640),
    ('Sunscreen SPF50', 'Neutrogena', 'Skin Care', 750),
    ('Nail Polish', 'Nykaa', 'Nails', 290),
    ('Beard Oil', 'Beardo', 'Men', 420),
    ('Hair Wax', 'Gatsby', 'Men', 350),
    ('Makeup Remover', 'Garnier', 'Skin Care', 330),
    ('Body Lotion', 'Vaseline', 'Skin Care', 480),
]


def seed(reset=True):
    if reset:
        print('Clearing existing data...')
        models_ordered = [
            InvoiceItem, Payment, AdvancePayment, Invoice, AppointmentService,
            Appointment, ProductLot, Product, Vendor, ServiceLog,
            CenterService, ServiceMaster, StaffMember, Designation,
            ClientValueCard, ClientMembership, Client, Promotion, ValueCard,
            Membership, Package, PettyCashEntry, DailyClosing, Shift,
        ]
        for m in models_ordered:
            m.objects.all().delete()
        Center.objects.all().delete()
        Role.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()

    print('Seeding roles & users...')
    owner_role = Role.objects.create(name='Owner', permissions={'all_centers': True})
    Role.objects.create(name='Manager', permissions={})
    if not User.objects.filter(email='admin@chilli.potato').exists():
        admin = User.objects.create_superuser(
            email='admin@chilli.potato',
            password='admin1234',
            full_name='Test Admin',
        )
    else:
        admin = User.objects.get(email='admin@chilli.potato')
    admin.role = owner_role
    admin.save()
    staff_user = User.objects.create_user(
        email='staff@chilli.potato', password='staff1234', full_name='Test Staff'
    )
    staff_user.role = Role.objects.get(name='Manager')
    staff_user.save()

    print('Seeding centers...')
    centers = []
    for i, city in enumerate(['Mumbai', 'Pune', 'Delhi']):
        c = Center.objects.create(
            center_name=f'Chilli Potato {city}',
            display_name=f'CP {city}',
            address=f'{i+1} Test Street, {city}',
            region=city,
            phone=f'98{i}000{i}00{i}',
            center_email=f'{city.lower()}@chilli.potato',
            gst_enabled=True,
            monthly_target=1_000_000,
        )
        centers.append(c)
    admin.centers.set(centers)

    print('Seeding designations & staff...')
    designations = [Designation.objects.create(name=n) for n in
                    ['Senior Stylist', 'Junior Stylist', 'Massage Therapist',
                     'Makeup Artist', 'Receptionist', 'Manager']]
    staff = []
    for i in range(60):
        s = StaffMember.objects.create(
            first_name=f'Staff{i}',
            last_name=f'Surname{i}',
            phone=f'99{i:08d}',
            email=f'staff{i}@example.com',
            gender=random.choice(['Male', 'Female', 'Other']),
            designation=random.choice(designations).name,
            designation_fk=random.choice(designations),
            center=random.choice(centers),
            salary=random.randint(15000, 50000),
            commission_percentage=random.choice([0, 10, 15, 20]),
            is_active=True,
        )
        staff.append(s)

    print('Seeding services...')
    service_masters = []
    for name, cat, sub, price, dur in SERVICES:
        sm = ServiceMaster.objects.create(
            name=name, category=cat, sub_category=sub,
            default_price=price, duration_mins=dur, tax_percentage=18,
        )
        service_masters.append(sm)
        for c in centers:
            CenterService.objects.create(center=c, service=sm, price=price,
                                         is_active=True)

    print('Seeding marketing...')
    for i in range(10):
        Promotion.objects.create(
            name=f'Promo {i}',
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=20),
            promo_type='Discount',
            level='Organisation',
            discount_type='Percentage',
            discount_value=10,
            is_active=True,
        )
    vip_card = ValueCard.objects.create(title='VIP Card', value=5000,
                                        pre_tax_price=5000, post_tax_price=5900,
                                        expiry_days=180)
    gold_membership = Membership.objects.create(name='Gold Annual',
                                                pre_tax_price=12000, post_tax_price=14160,
                                                expiry_days=365)
    Package.objects.create(name='Glow Package', price=5000, validity_days=90)

    print('Seeding clients...')
    clients = []
    with transaction.atomic():
        for i in range(300):
            cl = Client.objects.create(
                first_name=f'Client{i}',
                last_name=f'Last{i}',
                phone=f'97{i:08d}',
                email=f'client{i}@example.com',
                gender=random.choice(['female', 'male']),
                birthday=date(1980 + (i % 30), (i % 12) + 1, (i % 28) + 1),
                center=random.choice(centers),
            )
            clients.append(cl)
        Client.objects.bulk_update(clients, ['center'])
        # need ids for FKs, so re-fetch
        clients = list(Client.objects.all().order_by('id'))

    for c in clients[:50]:
        ClientMembership.objects.create(
            client=c, membership=gold_membership,
            expiry_date=date.today() + timedelta(days=335),
        )
        ClientValueCard.objects.create(
            client=c, value_card=vip_card, balance=2000,
            expiry_date=date.today() + timedelta(days=180),
        )

    print('Seeding inventory...')
    vendors = [Vendor.objects.create(name=f'Vendor {i}', phone=f'96{i:08d}',
                                     email=f'vendor{i}@example.com',
                                     center=random.choice(centers))
               for i in range(10)]
    products = []
    for name, brand, cat, price in PRODUCTS:
        p = Product.objects.create(name=name, brand=brand, category=cat,
                                   price=price, current_stock=random.randint(5, 200),
                                   center=random.choice(centers),
                                   vendor_name=random.choice(vendors).name)
        products.append(p)
        ProductLot.objects.create(product=p, lot_number=f'LOT-{p.id}-1',
                                  net_price=price * 0.7, mrp=price,
                                  expiry_date=date.today() + timedelta(days=365))

    print('Seeding appointments...')
    appts = []
    with transaction.atomic():
        now = datetime.now()
        for i in range(200):
            d = date.today() - timedelta(days=random.randint(0, 60))
            a = Appointment(
                client=random.choice(clients),
                client_phone=random.choice(clients).phone,
                client_name=f'Walkin {i}',
                date=d,
                start_time=f'{random.randint(9, 19):02d}:{random.choice(["00", "30"])}',
                status=random.choice(['Scheduled', 'Completed', 'Cancelled']),
                center=random.choice(centers),
                # bulk_create does not auto-populate auto_now(_add) fields
                created_at=now - timedelta(days=random.randint(0, 60)),
                updated_at=now - timedelta(days=random.randint(0, 30)),
            )
            appts.append(a)
        Appointment.objects.bulk_create(appts)
    appts = list(Appointment.objects.all().order_by('id'))
    with transaction.atomic():
        aps = []
        for a in appts:
            aps.append(AppointmentService(appointment=a,
                                          service_name=random.choice(SERVICES)[0],
                                          time=a.start_time,
                                          duration=random.choice([30, 45, 60]),
                                          price=random.choice([350, 600, 900])))
        AppointmentService.objects.bulk_create(aps)

    print('Seeding invoices + payments...')
    statuses = ['draft', 'paid', 'partial', 'cancelled', 'refunded']
    invoice_ids = []
    with transaction.atomic():
        for i in range(500):
            inv = Invoice(
                client=random.choice(clients),
                center=random.choice(centers),
                staff=random.choice(staff) if staff else None,
                subtotal=random.randint(200, 5000),
                discount=random.choice([0, 50, 100, 200]),
                cgst=0, sgst=0,
                total_amount=random.randint(200, 5000),
                status=random.choices(statuses, weights=[15, 60, 10, 10, 5])[0],
            )
            inv.save()
            invoice_ids.append((inv.id, date.today() - timedelta(days=random.randint(0, 120))))
            for _ in range(random.randint(1, 3)):
                InvoiceItem.objects.create(
                    invoice=inv,
                    description=random.choice([s[0] for s in SERVICES]),
                    unit_price=random.randint(200, 2000),
                    quantity=1,
                    tax_percentage=18,
                    total_price=random.randint(200, 2000),
                )
            if inv.status in ('paid', 'partial'):
                Payment.objects.create(invoice=inv,
                                       amount=inv.total_amount // 2 if inv.status == 'partial' else inv.total_amount,
                                       payment_method=random.choice(['Cash', 'UPI', 'Credit Card']))
    # Spread invoice dates over the last 120 days (auto_now_add overrides the
    # value at insert time, so patch afterwards via queryset.update).
    for inv_id, d in invoice_ids:
        Invoice.objects.filter(pk=inv_id).update(created_at=datetime.combine(d, datetime.min.time()),
                                                 updated_at=datetime.combine(d, datetime.min.time()))
    print('Seeding finance...')
    for c in centers:
        for i in range(30):
            d = date.today() - timedelta(days=i)
            DailyClosing.objects.get_or_create(center=c, date=d, defaults={
                'opening_balance': 1000,
                'system_cash': 4000,
                'cash_in_hand': 4200,
                'difference': 200,
                'closing_balance': 5000,
                'credit_card': 800,
                'upi': 600,
            })
            PettyCashEntry.objects.create(center=c, description=f'Expense {i}',
                                          amount=random.randint(50, 500),
                                          voucher_number=f'V{i:04d}',
                                          comments='auto-seeded')
    Shift.objects.create(center=centers[0], opened_by=admin,
                         starting_float=1000, status='Open')

    print('Seed complete:')
    print(f'  users={User.objects.count()} centers={Center.objects.count()} '
          f'staff={StaffMember.objects.count()} clients={Client.objects.count()} '
          f'invoices={Invoice.objects.count()} appointments={Appointment.objects.count()} '
          f'products={Product.objects.count()}')
    print('  login: admin@chilli.potato / admin1234')


if __name__ == '__main__':
    seed()
