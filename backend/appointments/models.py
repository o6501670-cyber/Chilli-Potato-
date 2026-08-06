from django.db import models
from salon_admin.models import Center
from staff.models import StaffMember

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='appointments')
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments'
    )
    client_phone = models.CharField(max_length=20)
    client_name = models.CharField(max_length=100)
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client_name} - {self.date} {self.start_time}"

    class Meta:
        indexes = [
            models.Index(fields=['center', 'date'], name='appt_center_date_idx'),
            models.Index(fields=['status'], name='appt_status_idx'),
        ]

class AppointmentService(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=100)
    time = models.TimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    staff = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.service_name} for {self.appointment.client_name}"
