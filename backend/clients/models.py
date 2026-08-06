from django.db import models


class Client(models.Model):
    center = models.ForeignKey('salon_admin.Center', null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=20, unique=True)
    app_pin = models.CharField(max_length=10, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    dnd_status = models.CharField(max_length=50, default='NOT ON DND')
    gender = models.CharField(max_length=20, default='female', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_blacklisted = models.BooleanField(default=False)
    blacklist_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        """Safe concatenation that handles nullable last_name."""
        return f"{self.first_name} {self.last_name or ''}".strip()

    @property
    def advance_balance(self):
        """
        Advance balance = sum of all AdvancePayment rows for this client.
        Positive rows = advances received.
        Negative rows = advances redeemed (created in finalize_invoice).
        We do NOT also look at Payment rows because that would double-subtract.
        """
        try:
            from billing.models import AdvancePayment
            from django.db.models import Sum
            total = (
                AdvancePayment.objects
                .filter(client=self)
                .aggregate(total=Sum('amount'))['total']
            ) or 0
            return float(total)
        except Exception:
            return 0.0

    @property
    def cashback_balance(self):
        """
        Cashback balance = sum of all CashbackTransaction rows for this client.
        Positive rows = cashback earned.
        Negative rows = cashback redeemed.
        """
        try:
            from billing.models import CashbackTransaction
            from django.db.models import Sum
            total = (
                CashbackTransaction.objects
                .filter(client=self)
                .aggregate(total=Sum('amount'))['total']
            ) or 0
            return float(total)
        except Exception:
            return 0.0

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    class Meta:
        indexes = [
            models.Index(fields=['phone'], name='client_phone_idx'),
            models.Index(fields=['center'], name='client_center_idx'),
        ]


class ClientMembership(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='memberships')
    membership = models.ForeignKey('marketing.Membership', on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.first_name} - {self.membership.name}"


class ClientPackage(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='packages')
    # FIXED: null=True allows custom packages that have no pre-defined Package object
    package = models.ForeignKey('marketing.Package', on_delete=models.CASCADE, null=True, blank=True)
    services_remaining = models.JSONField(default=dict, help_text="Maps service_id to remaining quantity")
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        pkg_name = self.package.name if self.package else 'Custom Package'
        return f"{self.client.first_name} - {pkg_name}"


class ClientValueCard(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='value_cards')
    value_card = models.ForeignKey('marketing.ValueCard', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.first_name} - {self.value_card.title}"
