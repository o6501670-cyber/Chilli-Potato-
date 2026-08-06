import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json
import datetime
from decimal import Decimal

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
if not user:
    exit("No superuser found")

client = Client(HTTP_HOST='localhost')
client.force_login(user)

print("Starting End-to-End Billing, Marketing, and Finance Test...")

# 1. Fetch required master data
centers = client.get('/salon_admin/api/centers/')
center_id = centers.json()[0]['id']

staff_res = client.get(f'/staff/api/members/?center_id={center_id}')
staff_id = staff_res.json()[0]['id']

clients_res = client.get('/clients/api/clients/')
client_data = clients_res.json()[0]
client_id = client_data['id']

print(f"Using Center {center_id}, Staff {staff_id}, Client {client_id}")

# 2. Create a Promotion
promo_payload = {
    "name": "E2E Test Cashback",
    "promo_type": "Cashback",
    "level": "Organisation",
    "start_date": str(datetime.date.today()),
    "end_date": str(datetime.date.today() + datetime.timedelta(days=30)),
    "config": {"cashback_min_bill": 1000, "cashback_discount": 10},
    "is_active": True
}
promo_res = client.post('/marketing/api/promotions/', json.dumps(promo_payload), content_type='application/json')
promo_id = promo_res.json()['id']
print(f"Created Promotion {promo_id}")

# 3. Create a Value Card
vc_payload = {
    "title": "E2E Value Card",
    "level": "Organisation",
    "pre_tax_price": 5000,
    "post_tax_price": 5000,
    "value": 6000,
    "expiry_days": 90,
    "is_active": True
}
vc_res = client.post('/marketing/api/cards/', json.dumps(vc_payload), content_type='application/json')
vc_id = vc_res.json()['id']
print(f"Created Value Card {vc_id}")

# 4. Generate an Invoice with Value Card
inv_payload = {
    "client": client_id,
    "center": center_id,
    "status": "paid",
    "subtotal": 5000,
    "total_amount": 5000,
    "paid_amount": 5000,
    "items": [
        {
            "content_type": "marketing.valuecard",
            "object_id": vc_id,
            "description": "E2E Value Card",
            "unit_price": 5000,
            "quantity": 1,
            "total_price": 5000,
            "staff": staff_id,
            "staff_members": [staff_id]
        }
    ],
    "payments": [
        {"amount": 5000, "payment_method": "Cash"}
    ]
}
inv_res = client.post('/billing/invoices/', json.dumps(inv_payload), content_type='application/json', HTTP_CENTER_ID=str(center_id))
inv_id = inv_res.json().get('id')
if not inv_id:
    print("Failed to create Invoice 1:", inv_res.json())
else:
    print(f"Created Invoice 1 (Purchased Value Card): {inv_id}")

# 5. Generate an Invoice redeeming the Value Card and using the Promotion
inv2_payload = {
    "client": client_id,
    "center": center_id,
    "status": "paid",
    "subtotal": 2000,
    "total_amount": 2000,
    "paid_amount": 2000,
    "items": [
        {
            "content_type": "services.servicemaster",
            "object_id": 1, # Just a placeholder, assuming ID 1 exists, or we skip content_type
            "description": "Premium Haircut",
            "unit_price": 2000,
            "quantity": 1,
            "total_price": 2000,
            "staff": staff_id,
            "staff_members": [staff_id]
        }
    ],
    "payments": [
        # Paying entirely with Value Card!
        {"amount": 2000, "payment_method": "Value Card"}
    ],
    "promo_id": promo_id # Use the cashback promo
}

# Find the client's value card ID
from clients.models import ClientValueCard
cvc = ClientValueCard.objects.filter(client_id=client_id, is_active=True).first()
if cvc:
    inv2_payload["payments"][0]["value_card_id"] = cvc.id

inv2_res = client.post('/billing/invoices/', json.dumps(inv2_payload), content_type='application/json', HTTP_CENTER_ID=str(center_id))
inv2_id = inv2_res.json().get('id')
if not inv2_id:
    print("Failed to create Invoice 2:", inv2_res.json())
else:
    print(f"Created Invoice 2 (Redeemed VC + Promo): {inv2_id}")

# 6. Verify Outputs
print("\n--- Verification Phase ---")

# Check Wallet / Cashback
from clients.models import Client
c = Client.objects.get(id=client_id)
print(f"Client Cashback Balance (should be 200 from 10% of 2000): {c.cashback_balance}")

# Check Value Card Balance
cvc.refresh_from_db()
print(f"Client Value Card Balance (should be 6000 - 2000 = 4000): {cvc.balance}")

# Check Promotion Usage
promo_usage = client.get('/marketing/api/promotions/usage_report/')
usages = promo_usage.json()
print("Promotion Usage API returned items:", len(usages))

# Check Staff Incentive Calculation
today = str(datetime.date.today())
incentive_url = f'/finance/api/reports/incentive-calculation/?center_id={center_id}&start_date={today}&end_date={today}&frequency=daily'
inc_res = client.get(incentive_url)
staff_data = inc_res.json()
for st in staff_data:
    if st['staff_id'] == staff_id:
        print(f"Staff Revenue: {st.get('revenue', 0)}")
        print(f"Staff Card Incentive: {st.get('card_incentive', 0)}")

print("Test complete. If values match expectations, the core logic is 100% sound.")
