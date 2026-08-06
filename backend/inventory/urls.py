from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VendorViewSet, ProductViewSet, PurchaseOrderViewSet, ProductLotViewSet, StockTransactionViewSet, LowStockAlertView

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'lots', ProductLotViewSet, basename='lot')
router.register(r'stock-transactions', StockTransactionViewSet, basename='stock-transaction')

urlpatterns = [
    path('api/low_stock/', LowStockAlertView.as_view(), name='low_stock'),
    path('api/', include(router.urls)),
]
