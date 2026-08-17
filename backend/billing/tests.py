from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from clients.models import Client, ClientValueCard
from marketing.models import ValueCard
from salon_admin.models import Center, Role
from staff.models import PayrollRecord, ServiceLog, StaffMember
from billing.serializers import InvoiceSerializer
from billing.models import CashbackTransaction, Invoice, InvoiceItem, InvoiceRefund, Payment
from inventory.models import Product


class InvoiceSerializerTest(TestCase):
    def test_partial_update_no_items_preserves_total(self):
        """A scalar partial update must not replace invoice items/totals."""
        client = Client.objects.create(first_name="Test", last_name="Client", phone="1234567890")
        invoice = Invoice.objects.create(
            client=client,
            total_amount=150.00,
            subtotal=150.00,
            rounding=0.00
        )

        serializer = InvoiceSerializer(invoice, data={'notes': 'Updated note'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_invoice = serializer.save()

        self.assertEqual(updated_invoice.total_amount, 150.00)
        self.assertEqual(updated_invoice.rounding, 0.00)


@override_settings(AUDIT_LOG_ENABLED=False)
class InvoicePaymentIntegrityTests(APITestCase):
    def setUp(self):
        self.center = Center.objects.create(center_name='Main')
        role = Role.objects.create(name='Owner')
        self.user = CustomUser.objects.create_user(
            email='billing-owner@example.com', full_name='Billing Owner',
            password='Strong-Test-Pass-847!', role=role, center=self.center,
        )
        self.client.force_authenticate(self.user)
        self.customer = Client.objects.create(
            center=self.center, first_name='Customer', phone='9000000001'
        )

    def make_invoice(self, total='100.00', status='draft'):
        return Invoice.objects.create(
            center=self.center, client=self.customer, subtotal=total,
            total_amount=total, status=status,
        )

    def test_overpayment_is_rejected_without_creating_payment(self):
        invoice = self.make_invoice(total='100.00')
        response = self.client.post(
            f'/billing/invoices/{invoice.id}/pay/',
            {'amount': '101.00', 'payment_method': 'Cash'}, format='json',
        )

        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('0.00'))
        self.assertFalse(Payment.objects.filter(invoice=invoice).exists())

    def test_value_card_must_belong_to_invoice_client(self):
        invoice = self.make_invoice(total='100.00')
        other = Client.objects.create(center=self.center, first_name='Other', phone='9000000002')
        card = ValueCard.objects.create(title='Card', expiry_days=30)
        foreign_card = ClientValueCard.objects.create(
            client=other, value_card=card, balance='100.00', expiry_date=date(2027, 1, 1),
        )

        response = self.client.post(
            f'/billing/invoices/{invoice.id}/pay/',
            {'amount': '20.00', 'payment_method': 'Value Card', 'value_card_id': foreign_card.id},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.filter(invoice=invoice).exists())
        foreign_card.refresh_from_db()
        self.assertEqual(foreign_card.balance, Decimal('100.00'))

    def test_cashback_payment_uses_cashback_not_advance_balance(self):
        invoice = self.make_invoice(total='50.00')
        CashbackTransaction.objects.create(client=self.customer, amount='100.00', notes='earned')

        response = self.client.post(
            f'/billing/invoices/{invoice.id}/pay/',
            {'amount': '30.00', 'payment_method': 'Cashback Wallet'}, format='json',
        )

        self.assertEqual(response.status_code, 200, response.data)
        balance = CashbackTransaction.objects.filter(client=self.customer).aggregate(
            total=Sum('amount')
        )['total']
        self.assertEqual(balance, Decimal('70.00'))

    def test_finalization_failure_rolls_back_payment(self):
        invoice = self.make_invoice(total='50.00')
        self.client.raise_request_exception = False

        with patch('billing.views.finalize_invoice', side_effect=RuntimeError('finalize failed')):
            response = self.client.post(
                f'/billing/invoices/{invoice.id}/pay/',
                {'amount': '20.00', 'payment_method': 'Cash'}, format='json',
            )

        self.assertEqual(response.status_code, 500)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('0.00'))
        self.assertEqual(invoice.status, 'draft')
        self.assertFalse(Payment.objects.filter(invoice=invoice).exists())

    def test_cancelling_draft_does_not_add_inventory(self):
        invoice = self.make_invoice(total='50.00', status='draft')
        product = Product.objects.create(
            center=self.center, name='Retail Product', current_stock=10, price='50.00'
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            content_type=ContentType.objects.get_for_model(Product),
            object_id=product.id,
            description='Retail Product', unit_price='50.00', quantity=1,
        )

        response = self.client.post(f'/billing/invoices/{invoice.id}/cancel/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.current_stock, 10)

    def test_partial_invoice_refund_records_only_amount_paid(self):
        invoice = self.make_invoice(total='100.00', status='partial')
        invoice.paid_amount = Decimal('20.00')
        invoice.save(update_fields=['paid_amount'])

        response = self.client.post(f'/billing/invoices/{invoice.id}/refund/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(InvoiceRefund.objects.get(invoice=invoice).amount, Decimal('20.00'))

    def test_locked_payroll_blocks_invoice_cancellation_without_attribute_error(self):
        invoice = self.make_invoice(total='50.00', status='paid')
        staff = StaffMember.objects.create(
            center=self.center, first_name='Stylist', designation='Stylist'
        )
        ServiceLog.objects.create(
            staff=staff, center=self.center, client_name='Customer', service_name='Cut',
            price='50.00', date=invoice.created_at.date(), time='10:00', invoice=invoice,
        )
        PayrollRecord.objects.create(
            staff=staff, center=self.center, month=invoice.created_at.month,
            year=invoice.created_at.year, status='Locked',
        )

        response = self.client.post(f'/billing/invoices/{invoice.id}/cancel/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'paid')
