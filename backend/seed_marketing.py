import os
import django
import sys

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()

from marketing.models import ValueCard, Membership

def seed_marketing():
    print("Seeding Memberships...")
    memberships = [
        {
            "name": "Prive Membership",
            "pre_tax_price": 2857.14,
            "post_tax_price": 3000.00,
            "expiry_days": 365,
            "value": None,
            "discount_percent": 20.00,
            "incentive": None,
            "level": "Organisation"
        },
        {
            "name": "Complimentary Prive Membership",
            "pre_tax_price": None,
            "post_tax_price": None,
            "expiry_days": 365,
            "value": None,
            "discount_percent": 20.00,
            "incentive": None,
            "level": "Organisation"
        },
        {
            "name": "30% Membership",
            "pre_tax_price": None,
            "post_tax_price": None,
            "expiry_days": 365,
            "value": None,
            "discount_percent": 30.00,
            "incentive": None,
            "level": "Organisation"
        },
        {
            "name": "50% Membership",
            "pre_tax_price": None,
            "post_tax_price": None,
            "expiry_days": 365,
            "value": None,
            "discount_percent": 50.00,
            "incentive": None,
            "level": "Organisation"
        }
    ]

    for data in memberships:
        obj, created = Membership.objects.get_or_create(
            name=data["name"],
            level=data["level"],
            defaults=data
        )
        if not created:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            print(f"Updated {data['name']}")
        else:
            print(f"Created {data['name']}")

    print("Seeding Cards...")
    cards = [
        {
            "title": "Elite Card",
            "pre_tax_price": 10476.19,
            "post_tax_price": 11000.00,
            "expiry_days": 270,
            "value": 14000.00,
            "benefit_percent": 27.27,
            "incentive": 200.00,
            "level": "Organisation"
        },
        {
            "title": "Luxe Card",
            "pre_tax_price": 20000.00,
            "post_tax_price": 21000.00,
            "expiry_days": 365,
            "value": 30000.00,
            "benefit_percent": 42.86,
            "incentive": 400.00,
            "level": "Organisation"
        },
        {
            "title": "Prestige Card",
            "pre_tax_price": 48571.43,
            "post_tax_price": 51000.00,
            "expiry_days": 540,
            "value": 80000.00,
            "benefit_percent": 56.86,
            "incentive": 600.00,
            "level": "Organisation"
        },
        {
            "title": "Infinity Card",
            "pre_tax_price": 105714.29,
            "post_tax_price": 111000.00,
            "expiry_days": 730,
            "value": 180000.00,
            "benefit_percent": 62.16,
            "incentive": 800.00,
            "level": "Organisation"
        }
    ]

    for data in cards:
        obj, created = ValueCard.objects.get_or_create(
            title=data["title"],
            level=data["level"],
            defaults=data
        )
        if not created:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            print(f"Updated {data['title']}")
        else:
            print(f"Created {data['title']}")

if __name__ == '__main__':
    seed_marketing()
