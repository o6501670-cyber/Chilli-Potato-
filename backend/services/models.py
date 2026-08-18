from django.db import models

from salon_admin.models import Center


class ServiceMaster(models.Model):
    service_code = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    sac_code = models.CharField(max_length=50, blank=True, null=True)
    hsn_code = models.CharField(max_length=50, blank=True, null=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    duration_mins = models.IntegerField(default=0)
    level = models.CharField(max_length=20, choices=(('Organisation', 'Organisation'), ('Center', 'Center Specific')), default='Organisation')
    incentive = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Incentive %")
    centers = models.ManyToManyField(Center, related_name='assigned_services', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['category'], name='svc_category_idx'),
            models.Index(fields=['created_at'], name='svc_created_idx'),
        ]

class CenterService(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(ServiceMaster, on_delete=models.CASCADE, related_name='center_overrides')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Per-center incentive % override. If set, overrides ServiceMaster.incentive for this center.
    incentive = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                    verbose_name='Incentive % (Center Override)')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('center', 'service')
        indexes = [
            models.Index(fields=['center', 'is_active'], name='cs_center_active_idx'),
            models.Index(fields=['service'], name='cs_service_idx'),
            models.Index(fields=['created_at'], name='cs_created_idx'),
        ]

    def __str__(self):
        return f"{self.service.name} at {self.center.center_name}"
