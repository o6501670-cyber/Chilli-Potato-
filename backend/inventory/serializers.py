from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from .models import Vendor, Product, PurchaseOrder, PurchaseOrderItem, ProductLot, StockTransaction

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'

class ProductLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductLot
        fields = '__all__'
        read_only_fields = ('product',)

class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    lots = ProductLotSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    product_sac = serializers.CharField(source='product.sac_code', read_only=True)
    
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'
        read_only_fields = ('purchase_order', 'total_price')

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, required=False)
    vendor_details = VendorSerializer(source='vendor', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'

    @staticmethod
    def _line_total(item_data):
        try:
            qty = Decimal(str(item_data.get('quantity', 1)))
            rate = Decimal(str(item_data.get('rate', 0)))
            discount = Decimal(str(item_data.get('discount_percent', 0)))
            tax = Decimal(str(item_data.get('tax_percent', 0)))
        except Exception:
            raise serializers.ValidationError({'items': 'Quantity, rate, discount and tax must be numeric.'})
        if qty <= 0:
            raise serializers.ValidationError({'items': 'Purchase order quantity must be greater than zero.'})
        if rate < 0 or discount < 0 or tax < 0 or discount > 100 or tax > 100:
            raise serializers.ValidationError({'items': 'Rate must be non-negative and discount/tax must be between 0 and 100.'})
        base = qty * rate
        subtotal = base * (Decimal('1') - discount / Decimal('100'))
        return (subtotal * (Decimal('1') + tax / Decimal('100'))).quantize(Decimal('0.01'))

    @staticmethod
    def _validate_scope(purchase_order, item_data):
        product = item_data.get('product')
        if not product:
            raise serializers.ValidationError({'items': 'Every purchase order line needs a product.'})
        if product.center_id != purchase_order.center_id:
            raise serializers.ValidationError({
                'items': f"Product {product.name} does not belong to the purchase order's center."
            })

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        vendor = validated_data.get('vendor')
        center = validated_data.get('center')
        if vendor and center and vendor.center_id != center.id:
            raise serializers.ValidationError({'vendor': 'Vendor does not belong to the purchase order center.'})
        purchase_order = PurchaseOrder.objects.create(**validated_data)

        total_amount = Decimal('0')
        for item_data in items_data:
            self._validate_scope(purchase_order, item_data)
            total_price = self._line_total(item_data)
            item_data['total_price'] = total_price
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
            total_amount += total_price
        purchase_order.total_amount = total_amount.quantize(Decimal('0.01'))
        purchase_order.save(update_fields=['total_amount', 'updated_at'])
        return purchase_order

    @transaction.atomic
    def update(self, instance, validated_data):
        # Lock the PO so two simultaneous "Delivered" updates cannot receive
        # the same stock twice.
        instance = PurchaseOrder.objects.select_for_update().get(pk=instance.pk)
        items_data = validated_data.pop('items', None)
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        status_order = ['Draft', 'Finalized', 'Approved', 'Ordered', 'Shipped', 'Delivered']
        if old_status in status_order and new_status in status_order:
            if status_order.index(new_status) < status_order.index(old_status):
                raise serializers.ValidationError({'status': 'Cannot revert a purchase order to a previous status.'})

        vendor = validated_data.get('vendor', instance.vendor)
        center = validated_data.get('center', instance.center)
        if vendor and center and vendor.center_id != center.id:
            raise serializers.ValidationError({'vendor': 'Vendor does not belong to the purchase order center.'})
        if old_status == 'Delivered' and items_data is not None:
            raise serializers.ValidationError({'items': 'Cannot modify a delivered purchase order.'})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            total_amount = Decimal('0')
            for item_data in items_data:
                self._validate_scope(instance, item_data)
                total_price = self._line_total(item_data)
                item_data['total_price'] = total_price
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
                total_amount += total_price
            instance.total_amount = total_amount.quantize(Decimal('0.01'))
            instance.save(update_fields=['total_amount', 'updated_at'])

        if old_status != 'Delivered' and new_status == 'Delivered':
            for item in instance.items.select_related('product').all():
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.current_stock += item.quantity
                product.save(update_fields=['current_stock', 'updated_at'])
                StockTransaction.objects.create(
                    product=product,
                    center=instance.center,
                    transaction_type='PO_RECEIPT',
                    quantity_change=item.quantity,
                    notes=f'Receipt from PO-{instance.id}',
                )

        return instance
