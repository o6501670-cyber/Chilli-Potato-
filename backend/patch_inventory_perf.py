import os

views_path = r'backend\inventory\views.py'
with open(views_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. PurchaseOrderViewSet
target_po = "queryset = PurchaseOrder.objects.all().order_by('-created_at')"
replacement_po = "queryset = PurchaseOrder.objects.all().select_related('vendor').prefetch_related('items__product').order_by('-created_at')"
content = content.replace(target_po, replacement_po)

# 2. StockTransactionViewSet
target_st = "queryset = StockTransaction.objects.all().order_by('-created_at')"
replacement_st = "queryset = StockTransaction.objects.all().select_related('product').order_by('-created_at')"
content = content.replace(target_st, replacement_st)

# 3. LowStockAlertView
target_low = "qs = Product.objects.filter(current_stock__lte=F('reorder_level'))"
replacement_low = "qs = Product.objects.filter(current_stock__lte=F('reorder_level')).select_related('center')"
content = content.replace(target_low, replacement_low)

with open(views_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Optimized views for Inventory module!')
