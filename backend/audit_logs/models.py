from django.conf import settings
from django.db import models


class SystemLog(models.Model):
    # Who
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs'
    )
    user_name = models.CharField(max_length=255, blank=True)   # snapshot at log time
    user_email = models.CharField(max_length=255, blank=True)
    user_role = models.CharField(max_length=100, blank=True)
    user_id_snapshot = models.IntegerField(null=True, blank=True)

    # Where / Which Centre
    center_id = models.IntegerField(null=True, blank=True)
    center_name = models.CharField(max_length=255, blank=True)

    # What happened
    action = models.CharField(max_length=50)           # LOGIN, CREATE, UPDATE, DELETE, CANCEL, REFUND, LOGOUT
    module = models.CharField(max_length=100, blank=True)  # CLIENTS, STAFF, BILLING, USERS, etc.
    entity_type = models.CharField(max_length=100, blank=True)  # client, staff member, invoice, etc.
    entity_id = models.CharField(max_length=50, blank=True)     # ID of the object affected
    human_description = models.TextField(blank=True)   # "Admin created user John Doe"

    # Technical details
    path = models.CharField(max_length=255)
    description = models.TextField(blank=True)         # sanitised JSON payload
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True)   # raw User-Agent
    device_type = models.CharField(max_length=30, blank=True)   # Desktop / Laptop / Mobile / Tablet
    browser = models.CharField(max_length=100, blank=True)       # Chrome 120, Firefox 125 …
    os_info = models.CharField(max_length=100, blank=True)       # Windows 11, macOS 14, iOS 17 …
    geo_city = models.CharField(max_length=100, blank=True)
    geo_region = models.CharField(max_length=100, blank=True)
    geo_country = models.CharField(max_length=100, blank=True)
    geo_country_code = models.CharField(max_length=4, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['module']),
            models.Index(fields=['center_id']),
            models.Index(fields=['user_email']),
            # Composite index for the most common filter: module + timestamp for date-range queries
            models.Index(fields=['module', 'action'], name='syslog_module_action_idx'),
            # Composite for center + date filtering
            models.Index(fields=['center_id', 'timestamp'], name='syslog_center_ts_idx'),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {self.user_email or 'Anon'} | {self.action} | {self.module}"
