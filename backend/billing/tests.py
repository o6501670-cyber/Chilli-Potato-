from django.test import TestCase
from rest_framework.test import APIRequestFactory
from billing.serializers import InvoiceSerializer
from billing.models import Invoice
from clients.models import Client

class InvoiceSerializerTest(TestCase):
    def test_partial_update_no_items_preserves_total(self):
        """
        Verify that a partial update to an invoice without 'items' in the data
        does not override 'total_amount' and 'rounding' to 0.
        """
        client = Client.objects.create(first_name="Test", last_name="Client", phone="1234567890")
        invoice = Invoice.objects.create(
            client=client,
            total_amount=150.00,
            subtotal=150.00,
            rounding=0.00
        )
        
        # Perform a partial update (e.g., just updating notes or status)
        serializer = InvoiceSerializer(invoice, data={'notes': 'Updated note'}, partial=True)
        self.assertTrue(serializer.is_valid())
        
        updated_invoice = serializer.save()
        
        # total_amount should not be zeroed out
        self.assertEqual(updated_invoice.total_amount, 150.00)
        self.assertEqual(updated_invoice.rounding, 0.00)
