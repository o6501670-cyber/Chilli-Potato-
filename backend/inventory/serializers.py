from rest_framework import serializers
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
        read_only_fields = ('purchase_order',)

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, required=False)
    vendor_details = VendorSerializer(source='vendor', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        total_amount = 0
        for item_data in items_data:
            product = item_data.get('product')
            if product and product.center != purchase_order.center:
                raise serializers.ValidationError({"items": f"Product {product.name} does not belong to the purchase order's center."})
                
            qty = item_data.get('quantity', 1)
            rate = item_data.get('rate', 0)
            discount = item_data.get('discount_percent', 0)
            tax = item_data.get('tax_percent', 0)
            
            base = qty * rate
            discount_amount = base * (discount / 100)
            subtotal = base - discount_amount
            tax_amount = subtotal * (tax / 100)
            total_price = subtotal + tax_amount
            
            item_data['total_price'] = total_price
            PurchaseOrderItem.objects.create(purchase_order=purchase_order, **item_data)
            total_amount += total_price
            
        purchase_order.total_amount = total_amount
        purchase_order.save()
            
        return purchase_order
        
    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Prevent backwards status progression
        STATUS_ORDER = ['Draft', 'Finalized', 'Approved', 'Ordered', 'Shipped', 'Delivered']
        try:
            old_idx = STATUS_ORDER.index(old_status)
            new_idx = STATUS_ORDER.index(new_status)
            if new_idx < old_idx:
                raise serializers.ValidationError({"status": "Cannot revert Purchase Order to a previous status."})
        except ValueError:
            pass
        
        # Block modifying items if PO is already delivered
        if old_status == 'Delivered' and items_data is not None:
            raise serializers.ValidationError({"items": "Cannot modify items of a Delivered Purchase Order."})
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if items_data is not None:
            instance.items.all().delete()
            total_amount = 0
            for item_data in items_data:
                product = item_data.get('product')
                if product and product.center != instance.center:
                    raise serializers.ValidationError({"items": f"Product {product.name} does not belong to the purchase order's center."})
                    
                qty = item_data.get('quantity', 1)
                rate = item_data.get('rate', 0)
                discount = item_data.get('discount_percent', 0)
                tax = item_data.get('tax_percent', 0)
                
                base = qty * rate
                discount_amount = base * (discount / 100)
                subtotal = base - discount_amount
                tax_amount = subtotal * (tax / 100)
                total_price = subtotal + tax_amount
                
                item_data['total_price'] = total_price
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
                total_amount += total_price
            
            instance.total_amount = total_amount
            instance.save()
                
        # Handle stock updates on status change
        if old_status != 'Delivered' and new_status == 'Delivered':
            # Add stock
            for item in instance.items.all():
                if hasattr(item.product, 'current_stock'):
                    item.product.current_stock += item.quantity
                    item.product.save()
                    StockTransaction.objects.create(
                        product=item.product,
                        center=instance.center,
                        transaction_type='PO_RECEIPT',
                        quantity_change=item.quantity,
                        notes=f"Receipt from PO-{instance.id}"
                    )
        elif old_status == 'Delivered' and new_status != 'Delivered':
            # Reverse stock if status changed back from Delivered
            for item in instance.items.all():
                if hasattr(item.product, 'current_stock'):
                    item.product.current_stock -= item.quantity
                    item.product.save()
                    StockTransaction.objects.create(
                        product=item.product,
                        center=instance.center,
                        transaction_type='PO_RECEIPT',
                        quantity_change=-item.quantity,
                        notes=f"Reversed Receipt from PO-{instance.id}"
                    )
                
        return instance
