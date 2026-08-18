from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DesignationViewSet,
    PayrollRecordViewSet,
    ServiceLogViewSet,
    StaffConsumptionLogViewSet,
    StaffMemberViewSet,
    StaffToolTrackerViewSet,
    StaffTransferViewSet,
    consumption_report,
    revenue_report,
    staff_app_appointments,
    staff_app_login,
    staff_app_logs,
    staff_app_tools,
    staff_app_transfers,
    staff_app_update_profile,
    usage_report,
)

router = DefaultRouter()
router.register(r'designations', DesignationViewSet, basename='designation')
router.register(r'members', StaffMemberViewSet, basename='staffmember')
router.register(r'logs', ServiceLogViewSet, basename='servicelog')
router.register(r'consumptions', StaffConsumptionLogViewSet, basename='staffconsumption')
router.register(r'transfers', StaffTransferViewSet, basename='stafftransfer')
router.register(r'tools', StaffToolTrackerViewSet, basename='stafftooltracker')
router.register(r'payrolls', PayrollRecordViewSet, basename='payroll')

urlpatterns = [
    path('api/app/login/', staff_app_login, name='staff-app-login'),
    path('api/app/logs/', staff_app_logs, name='staff-app-logs'),
    path('api/app/appointments/', staff_app_appointments, name='staff-app-appointments'),
    path('api/app/tools/', staff_app_tools, name='staff-app-tools'),
    path('api/app/transfers/', staff_app_transfers, name='staff-app-transfers'),
    path('api/app/update_profile/', staff_app_update_profile, name='staff-app-update-profile'),

    path('api/', include(router.urls)),
    path('api/reports/revenue/', revenue_report, name='revenue-report'),
    path('api/reports/usage/', usage_report, name='usage-report'),
    path('api/reports/consumption/', consumption_report, name='consumption-report'),
]

