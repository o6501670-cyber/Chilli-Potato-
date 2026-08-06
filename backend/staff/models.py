from django.db import models
from salon_admin.models import Center

class StaffMember(models.Model):
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='staff_members')
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=(('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')), default='Female')
    designation = models.CharField(max_length=255)
    # FK link to Designation master (nullable so existing data is unaffected)
    designation_fk = models.ForeignKey(
        'Designation',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='staff_members',
        verbose_name='Designation (Master)'
    )
    joining_date = models.DateField(blank=True, null=True)
    staff_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Staff Code")
    email = models.EmailField(blank=True, null=True)
    aadhar_number = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    app_password = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to='staff_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    product_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    allocated_points = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="Perk Points")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.first_name
        if self.last_name:
            name += f" {self.last_name}"
        return name

    class Meta:
        indexes = [
            models.Index(fields=['center'], name='staff_center_idx'),
            models.Index(fields=['is_active'], name='staff_active_idx'),
        ]

class Designation(models.Model):
    name = models.CharField(max_length=255, unique=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    product_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ServiceLog(models.Model):
    TYPE_CHOICES = (
        ('Service', 'Service'),
        ('Package', 'Package'),
        ('Membership', 'Membership'),
        ('Product', 'Product'),
    )

    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='service_logs')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='service_logs')
    client_name = models.CharField(max_length=255)
    service_name = models.CharField(max_length=255)
    service_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='Service')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    time = models.TimeField()
    invoice = models.ForeignKey('billing.Invoice', null=True, blank=True, on_delete=models.SET_NULL, related_name='service_logs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service_name} by {self.staff.first_name}"

    class Meta:
        indexes = [
            models.Index(fields=['staff', 'date'], name='slog_staff_date_idx'),
            models.Index(fields=['center', 'date'], name='slog_center_date_idx'),
            models.Index(fields=['center'], name='slog_center_idx'),
            models.Index(fields=['invoice'], name='slog_invoice_idx'),
            models.Index(fields=['date'], name='slog_date_idx'),
        ]

class StaffConsumptionLog(models.Model):
    PAYMENT_CHOICES = (
        ('Points', 'Allocated Points'),
        ('Money', 'Own Money'),
    )

    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='consumption_logs')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='staff_consumptions')
    service_name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Points')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.first_name} consumed {self.service_name}"

class StaffTransfer(models.Model):
    TRANSFER_CHOICES = (
        ('Temporary', 'Temporary'),
        ('Permanent', 'Permanent'),
    )
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='transfers')
    from_center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='transfers_out')
    to_center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='transfers_in')
    transfer_type = models.CharField(max_length=50, choices=TRANSFER_CHOICES, default='Permanent')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Active')
    reason = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.first_name} -> {self.to_center.center_name}"

class PayrollRecord(models.Model):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Locked', 'Locked'),
        ('Paid', 'Paid'),
    )
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='payrolls')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='payrolls')
    month = models.IntegerField()
    year = models.IntegerField()
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    product_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('staff', 'month', 'year')
        indexes = [
            models.Index(fields=['center', 'month', 'year']),
        ]

    def __str__(self):
        return f"{self.staff.first_name} - {self.month}/{self.year} ({self.status})"

class StaffToolTracker(models.Model):
    STATUS_CHOICES = (
        ('Taken', 'Taken'),
        ('Returned', 'Returned')
    )
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='tool_trackers')
    tool_name = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True, verbose_name="Item Details")
    amount = models.IntegerField(default=1, verbose_name="Quantity/Amount")
    date_taken = models.DateField()
    expected_return_date = models.DateField(blank=True, null=True)
    actual_return_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Taken')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tool_name} - {self.staff.first_name}"

