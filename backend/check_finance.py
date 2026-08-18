import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

import time

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from finance.views import MonthlySalesView, RegisterSummaryView

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()

if not user:
    print("No superuser found.")
    exit()

factory = RequestFactory()

# 1. Test RegisterSummaryView with wide range
print("Testing RegisterSummaryView with 2020-01-01 to 2026-12-31...")
request = factory.get('/?start_date=2020-01-01&end_date=2026-12-31')
request.user = user

view = RegisterSummaryView.as_view()

start_time = time.time()
try:
    response = view(request)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.data
        print(f"Revenue Services: {data['revenues']['services']['amount']}")
        print(f"Total Collections: {data['revenues']['including_tax']}")
    else:
        print("Response:", response.data)
except Exception:
    import traceback
    print("Exception occurred!")
    traceback.print_exc()

print(f"Time taken: {time.time() - start_time:.2f} seconds\n")

# 2. Test MonthlySalesView
print("Testing MonthlySalesView with 2020-01-01 to 2026-12-31...")
request = factory.get('/?start_date=2020-01-01&end_date=2026-12-31')
request.user = user

view = MonthlySalesView.as_view()

start_time = time.time()
try:
    response = view(request)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        print(f"Months returned: {len(response.data)}")
    else:
        print("Response:", response.data)
except Exception:
    import traceback
    print("Exception occurred!")
    traceback.print_exc()

print(f"Time taken: {time.time() - start_time:.2f} seconds\n")
