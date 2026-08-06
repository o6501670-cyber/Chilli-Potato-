"""
URL configuration for pos_backend project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('salon_admin/', include('salon_admin.urls')),
    path('inventory/', include('inventory.urls')),
    path('marketing/', include('marketing.urls')),
    path('staff/', include('staff.urls')),
    path('appointments/', include('appointments.urls')),
    path('clients/', include('clients.urls')),
    path('services/', include('services.urls')),
    path('billing/', include('billing.urls')),
    path('finance/', include('finance.urls')),
    path('audit_logs/', include('audit_logs.urls')),
]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
