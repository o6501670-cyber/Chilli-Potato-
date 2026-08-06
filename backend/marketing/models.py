from django.db import models
from django.core.validators import MinValueValidator
from salon_admin.models import Center

LEVEL_CHOICES = (
    ('Organisation', 'Organisation Level'),
    ('Center', 'Center Specific'),
)

class WhatsAppMessage(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='whatsapp_messages')
    date = models.DateField()
    time = models.TimeField()
    client_name = models.CharField(max_length=255)
    client_phone = models.CharField(max_length=50)
    message = models.TextField()
    status = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} - {self.status}"

class Promotion(models.Model):
    PROMO_TYPES = (
        ('Discount', 'Discount on Bill/items'),
        ('FlatPrice', 'Flat Price on items'),
        ('Trigger', 'Trigger Deals'),
        ('Cashback', 'Cashback Cards'),
    )
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Organisation')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, null=True, blank=True, related_name='promotions')
    promo_type = models.CharField(max_length=50, choices=PROMO_TYPES, default='Discount')
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    members_only = models.BooleanField(default=False)
    max_usage_per_client = models.IntegerField(null=True, blank=True, help_text="Limit per client. Leave blank for unlimited.")
    discount_type = models.CharField(max_length=50, choices=(('Percentage', 'Percentage'), ('Flat', 'Flat Amount')), default='Percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class PromotionUsage(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='usages')
    center = models.ForeignKey(Center, on_delete=models.CASCADE)
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, null=True, blank=True, related_name='promo_usages')
    date = models.DateField(auto_now_add=True)
    bill_amount_before = models.DecimalField(max_digits=10, decimal_places=2)
    bill_amount_after = models.DecimalField(max_digits=10, decimal_places=2)
    revenue_generated = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.promotion.name} at {self.center}"

class ValueCard(models.Model):
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Organisation')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, null=True, blank=True, related_name='value_cards')
    title = models.CharField(max_length=255)
    pre_tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    post_tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    benefit_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    incentive = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expiry_days = models.IntegerField(validators=[MinValueValidator(1)], help_text="Must be at least 1 day.")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Membership(models.Model):
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Organisation')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, null=True, blank=True, related_name='memberships')
    name = models.CharField(max_length=255)
    pre_tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    post_tax_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    incentive = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expiry_days = models.IntegerField(validators=[MinValueValidator(1)], help_text="Must be at least 1 day.")
    description = models.TextField(blank=True, null=True)
    is_vip = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Package(models.Model):
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default='Organisation')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, null=True, blank=True, related_name='packages')
    name = models.CharField(max_length=255)
    service_name = models.CharField(max_length=255, blank=True, null=True) # Legacy placeholder
    services_json = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    validity_days = models.IntegerField(validators=[MinValueValidator(1)], help_text="Must be at least 1 day.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
