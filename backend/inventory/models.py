from django.db import models
from salon_admin.models import Center

class Vendor(models.Model):
    name = models.CharField(max_length=255, verbose_name="Vendor Name")
    short_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Short Name")
    email = models.EmailField(blank=True, null=True, verbose_name="Email Address")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Phone Number")
    cst_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="CST Number")
    pan_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="PAN Number")
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    vendor_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Vendor Code")
    mapped_products = models.ManyToManyField('Product', blank=True, related_name='mapped_vendors')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='vendors')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['center'], name='vendor_center_idx'),
            models.Index(fields=['created_at'], name='vendor_created_idx'),
        ]


class Product(models.Model):
    product_id_str = models.CharField(max_length=100, blank=True, null=True, verbose_name="Product ID")
    product_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Product Code")
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    sub_category = models.CharField(max_length=100, blank=True, null=True)
    vendor_name = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price (incl. tax)", null=True, blank=True)
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="GST %")
    barcode = models.CharField(max_length=100, blank=True, null=True)
    sac_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="SAC Code")
    is_active = models.BooleanField(default=True)
    reorder_level = models.IntegerField(default=0)
    reorder_quantity = models.IntegerField(default=0)
    current_stock = models.IntegerField(default=0, verbose_name="Current Stock")
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='products')
    incentive = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Incentive %")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['center', 'is_active'], name='product_center_active_idx'),
            models.Index(fields=['category'], name='product_category_idx'),
            models.Index(fields=['created_at'], name='product_created_idx'),
        ]


class ProductLot(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=100)
    net_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.lot_number}"

    class Meta:
        indexes = [
            models.Index(fields=['product'], name='lot_product_idx'),
            models.Index(fields=['created_at'], name='lot_created_idx'),
        ]


class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Finalized', 'Finalized'),
        ('Approved', 'Approved'),
        ('Ordered', 'Ordered'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='purchase_orders')
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Draft')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO-{self.id} ({self.vendor.name})"

    class Meta:
        indexes = [
            models.Index(fields=['center', 'status'], name='po_center_status_idx'),
            models.Index(fields=['status', 'created_at'], name='po_status_date_idx'),
            models.Index(fields=['created_at'], name='po_created_idx'),
        ]


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - PO-{self.purchase_order.id}"


class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('CHECKOUT', 'Checkout for salon use'),
        ('AUDIT', 'Stock Audit Adjustment'),
        ('PO_RECEIPT', 'Purchase Order Receipt'),
        ('SALE', 'Retail Sale'),
        ('REFUND', 'Refunded Sale')
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    quantity_change = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} ({self.quantity_change}) - {self.transaction_type}"

    class Meta:
        indexes = [
            models.Index(fields=['center', 'created_at'], name='stock_center_date_idx'),
            models.Index(fields=['product', 'created_at'], name='stock_product_date_idx'),
            models.Index(fields=['transaction_type'], name='stock_type_idx'),
        ]
