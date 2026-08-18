from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard_endpoints import (
    dashboard_clients,
    dashboard_finance,
    dashboard_revenues,
    dashboard_services_products,
    dashboard_staff,
    dashboard_summary,
)
from .views import (
    CenterViewSet,
    RoleViewSet,
    bulk_import_centers,
    bulk_import_template,
    dashboard_view,
)

router = DefaultRouter()
router.register(r'centers', CenterViewSet, basename='centers')
router.register(r'roles', RoleViewSet)

urlpatterns = [
    path('api/dashboard/', dashboard_view, name='admin-dashboard'),
    path('api/dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('api/dashboard/revenues/', dashboard_revenues, name='dashboard-revenues'),
    path('api/dashboard/clients/', dashboard_clients, name='dashboard-clients'),
    path('api/dashboard/finance/', dashboard_finance, name='dashboard-finance'),
    path('api/dashboard/staff/', dashboard_staff, name='dashboard-staff'),
    path('api/dashboard/services_products/', dashboard_services_products, name='dashboard-services-products'),
    path('api/centers/bulk-import/', bulk_import_centers, name='centers-bulk-import'),
    path('api/centers/bulk-import-template/', bulk_import_template, name='centers-bulk-import-template'),
    path('api/', include(router.urls)),
]
