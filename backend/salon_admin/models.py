from django.db import models

class Center(models.Model):
    center_name = models.CharField(max_length=255, verbose_name="Center / Legal Name")
    display_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    
    # Tax Details
    cst_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CST Number")
    gst_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="GST Number")
    pan_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pan Number")
    
    # Financial
    monthly_target = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    monthly_targets_history = models.JSONField(default=dict, blank=True)
    closing_sms_recipients = models.JSONField(default=list, blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    gst_enabled = models.BooleanField(default=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True, null=True)
    landline_1 = models.CharField(max_length=20, blank=True, null=True)
    landline_2 = models.CharField(max_length=20, blank=True, null=True)
    center_email = models.EmailField(blank=True, null=True)
    
    # Owner Details
    owner_name = models.CharField(max_length=255, blank=True, null=True)
    owner_phone = models.CharField(max_length=20, blank=True, null=True)
    owner_email_1 = models.EmailField(blank=True, null=True)
    
    owner_name_2 = models.CharField(max_length=255, blank=True, null=True)
    owner_phone_2 = models.CharField(max_length=20, blank=True, null=True)
    owner_email_2 = models.EmailField(blank=True, null=True)
    
    owner_name_3 = models.CharField(max_length=255, blank=True, null=True)
    owner_phone_3 = models.CharField(max_length=20, blank=True, null=True)
    owner_email_3 = models.EmailField(blank=True, null=True)
    
    # Accountant Details
    accountant_name_1 = models.CharField(max_length=255, blank=True, null=True)
    accountant_phone_1 = models.CharField(max_length=20, blank=True, null=True)
    accountant_email_1 = models.EmailField(blank=True, null=True)
    
    accountant_name_2 = models.CharField(max_length=255, blank=True, null=True)
    accountant_phone_2 = models.CharField(max_length=20, blank=True, null=True)
    accountant_email_2 = models.EmailField(blank=True, null=True)
    
    launched_on = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.center_name

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    permissions = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return self.name
