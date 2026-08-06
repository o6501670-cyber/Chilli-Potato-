import os
import django
from rest_framework.exceptions import ValidationError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from billing.serializers import InvoiceSerializer

def run_tests():
    print("Running Security Tests on InvoiceSerializer...")
    serializer = InvoiceSerializer()
    
    # Test 1: Negative Payment
    data_1 = {
        'items': [{'quantity': 1, 'unit_price': 100, 'discount': 0}],
        'payments': [{'amount': -50, 'payment_method': 'Cash'}],
        'subtotal': 100, 'discount': 0, 'cgst': 0, 'sgst': 0, 'rounding': 0, 'total_amount': 100
    }
    try:
        serializer.validate(data_1)
        print("FAIL: Negative payment slipped through!")
    except ValidationError as e:
        if 'Payment amounts must be greater than zero' in str(e):
            print("PASS: Negative payment blocked.")
        else:
            print("FAIL: Caught error but wrong message:", e)

    # Test 2: Negative Quantity
    data_2 = {
        'items': [{'quantity': -1, 'unit_price': 100, 'discount': 0}],
        'payments': [],
        'subtotal': 0, 'discount': 0, 'cgst': 0, 'sgst': 0, 'rounding': 0, 'total_amount': 0
    }
    try:
        serializer.validate(data_2)
        print("FAIL: Negative quantity slipped through!")
    except ValidationError as e:
        if 'Item quantity must be greater than zero' in str(e):
            print("PASS: Negative quantity blocked.")
        else:
            print("FAIL: Caught error but wrong message:", e)

    # Test 3: Excessive Discount
    data_3 = {
        'items': [{'quantity': 1, 'unit_price': 100, 'discount': 0}],
        'payments': [],
        'subtotal': 100, 'discount': 500, 'cgst': 0, 'sgst': 0, 'rounding': 0, 'total_amount': 0
    }
    try:
        serializer.validate(data_3)
        print("FAIL: Excessive discount slipped through!")
    except ValidationError as e:
        if 'Global discount cannot exceed the subtotal' in str(e):
            print("PASS: Excessive discount blocked.")
        else:
            print("FAIL: Caught error but wrong message:", e)

if __name__ == '__main__':
    run_tests()
