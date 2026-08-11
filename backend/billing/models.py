from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    # PROTECTED: client FK must not cascade-delete invoices (invoices are financial records)
    # Use PROTECT so Django raises an error if someone tries to delete a client with invoices.
    # To deactivate/anonymise a client, set is_blacklisted=True instead of deleting.
    client = models.ForeignKey('clients.Client', on_delete=models.PROTECT, null=True, blank=True, related_name='invoices')
    center = models.ForeignKey('salon_admin.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    staff = models.ForeignKey('staff.StaffMember', null=True, blank=True, on_delete=models.SET_NULL)
    appointment = models.ForeignKey('appointments.Appointment', null=True, blank=True, on_delete=models.SET_NULL, related_name='invoices')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rounding = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.total_amount < 0:
            raise ValidationError({'total_amount': 'Invoice total amount cannot be negative.'})
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice {self.id} - {self.client} ({self.total_amount})"

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at'], name='inv_status_date_idx'),
            models.Index(fields=['center', 'created_at'], name='inv_center_date_idx'),
            models.Index(fields=['center', 'status', 'created_at'], name='inv_center_status_date_idx'),
            models.Index(fields=['client'], name='inv_client_idx'),
            models.Index(fields=['client', 'status'], name='inv_client_status_idx'),
        ]


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('Cash', 'Cash'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('UPI', 'UPI'),
        ('Google Pay', 'Google Pay'),
        ('PhonePe', 'PhonePe'),
        ('Paytm', 'Paytm'),
        ('BharatPe', 'BharatPe'),
        ('Cheque', 'Cheque'),
        ('Net Banking', 'Net Banking'),
        ('NearBuy', 'NearBuy'),
        ('Advance', 'Advance'),
        ('Value Card', 'Value Card'),
        ('Cashback Wallet', 'Cashback Wallet'),
        ('Other', 'Other'),
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    # Store value card ID directly when method involves a card, avoids fragile string parsing
    value_card_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_method} - {self.amount}"

    class Meta:
        indexes = [
            models.Index(fields=['invoice'], name='pay_invoice_idx'),
            models.Index(fields=['created_at'], name='pay_created_idx'),
            models.Index(fields=['payment_method', 'created_at'], name='pay_method_date_idx'),
        ]


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')

    # Generic relation to Service/Product/Membership/Package/Card
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    description = models.CharField(max_length=255, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # From service/product master
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # Pre-tax amount × tax_percentage / 100
    # total_price is stored as sent from frontend; save() guards against negative values
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_complimentary = models.BooleanField(default=False, help_text='Flags 0-value items intentionally given for free or redeemed')
    staff = models.ForeignKey('staff.StaffMember', null=True, blank=True, on_delete=models.SET_NULL)
    staff_members = models.ManyToManyField('staff.StaffMember', related_name='invoice_items_multi', blank=True)

    def save(self, *args, **kwargs):
        if not self.is_complimentary:
            calculated = ((self.unit_price or 0) * (self.quantity or 1)) - (self.discount or 0)
            if self.total_price == 0 and calculated != 0:
                self.total_price = calculated
        if self.total_price < 0:
            self.total_price = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} x {self.quantity} ({self.total_price})"


class AdvancePayment(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='advances')
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='advance_payments'
    )
    staff = models.ForeignKey('staff.StaffMember', null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Advance {self.id} - {self.client} ({self.amount})"

    class Meta:
        indexes = [
            models.Index(fields=['client', 'created_at'], name='adv_client_date_idx'),
        ]


class BillChangeLog(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='change_logs')
    center = models.ForeignKey('salon_admin.Center', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.action} on Invoice {self.invoice.id}'

    class Meta:
        indexes = [
            models.Index(fields=['center', 'created_at'], name='changelog_center_date_idx'),
            models.Index(fields=['invoice'], name='changelog_invoice_idx'),
        ]


class CashbackTransaction(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='cashback_transactions')
    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cashback_transactions'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cashback {self.id} - {self.client} ({self.amount})"

    class Meta:
        indexes = [
            models.Index(fields=['client', 'created_at'], name='cb_client_date_idx'),
        ]
