from django.db import models


class Client(models.Model):
    center = models.ForeignKey('salon_admin.Center', null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=20)
    app_pin = models.CharField(max_length=128, blank=True, null=True)
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
            from decimal import Decimal
            return Decimal(str(total or 0)).quantize(Decimal('0.01'))
        except Exception:
            from decimal import Decimal
            return Decimal('0.00')

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
            from decimal import Decimal
            return Decimal(str(total or 0)).quantize(Decimal('0.01'))
        except Exception:
            from decimal import Decimal
            return Decimal('0.00')

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        raw_pin = None
        if is_new and not self.app_pin:
            # Use secrets module (CSPRNG) instead of random — PINs are used for app login
            import secrets
            from django.contrib.auth.hashers import make_password
            raw_pin = f"{secrets.randbelow(9000) + 1000}"
            self.app_pin = make_password(raw_pin)
        
        super().save(*args, **kwargs)
        
        if is_new and self.email and raw_pin:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                import threading
                
                subject = "Welcome to Chilli Potato - Your Account PIN"
                message = (
                    f"Hello {self.first_name},\n\n"
                    f"Your client profile has been created successfully.\n"
                    f"Your 4-digit mobile app access PIN is: {raw_pin}\n\n"
                    f"Thank you,\n"
                    f"Chilli Potato Team"
                )
                
                def _send_email_async():
                    from django.db import close_old_connections
                    try:
                        close_old_connections()
                        send_mail(
                            subject,
                            message,
                            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@chillipotato.com'),
                            [self.email],
                            fail_silently=False,
                        )
                    except Exception as email_err:
                        import logging
                        logger = logging.getLogger('django')
                        logger.error(f"[Welcome Email] Failed to send welcome email to {self.email}: {email_err}", exc_info=True)
                    finally:
                        close_old_connections()
                
                # Use a global thread pool instead of unbounded threads to prevent M2 explosion
                from concurrent.futures import ThreadPoolExecutor
                if not hasattr(settings, '_email_executor'):
                    settings._email_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='email_sender')
                settings._email_executor.submit(_send_email_async)
            except Exception as thread_err:
                import logging
                logger = logging.getLogger('django')
                logger.error(f"[Welcome Email] Thread start error for {self.email}: {thread_err}", exc_info=True)

    class Meta:
        indexes = [
            models.Index(fields=['phone'], name='client_phone_idx'),
            models.Index(fields=['center'], name='client_center_idx'),
            models.Index(fields=['created_at'], name='client_created_idx'),
            models.Index(fields=['center', 'created_at'], name='client_center_date_idx'),
            models.Index(fields=['gender'], name='client_gender_idx'),
        ]


class ClientMembership(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='memberships')
    membership = models.ForeignKey('marketing.Membership', on_delete=models.CASCADE)
    source_invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.first_name} - {self.membership.name}"

    class Meta:
        indexes = [
            models.Index(fields=['client'], name='cm_client_idx'),
            models.Index(fields=['is_active'], name='cm_active_idx'),
            models.Index(fields=['created_at'], name='cm_created_idx'),
        ]


class ClientPackage(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='packages')
    # FIXED: null=True allows custom packages that have no pre-defined Package object
    package = models.ForeignKey('marketing.Package', on_delete=models.CASCADE, null=True, blank=True)
    source_invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    services_remaining = models.JSONField(default=dict, help_text="Maps service_id to remaining quantity")
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        pkg_name = self.package.name if self.package else 'Custom Package'
        return f"{self.client.first_name} - {pkg_name}"

    class Meta:
        indexes = [
            models.Index(fields=['client'], name='cpkg_client_idx'),
            models.Index(fields=['is_active'], name='cpkg_active_idx'),
            models.Index(fields=['created_at'], name='cpkg_created_idx'),
        ]


class ClientValueCard(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='value_cards')
    value_card = models.ForeignKey('marketing.ValueCard', on_delete=models.CASCADE)
    source_invoice = models.ForeignKey('billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.first_name} - {self.value_card.title}"

    class Meta:
        indexes = [
            models.Index(fields=['client'], name='cvc_client_idx'),
            models.Index(fields=['is_active'], name='cvc_active_idx'),
            models.Index(fields=['created_at'], name='cvc_created_idx'),
        ]
