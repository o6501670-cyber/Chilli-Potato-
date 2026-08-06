
import re
with open('backend/billing/serializers.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix create()
old_create = '''        total = 0
        for item_data in items_data:
            item_data['invoice'] = invoice
            serializer = InvoiceItemSerializer()
            item = serializer.create(validated_data=item_data)
            total += item.total_price
        invoice.total_amount = total
        
        paid = 0
        for pay_data in payments_data:
            pay_data['invoice'] = invoice
            Payment.objects.create(**pay_data)
            paid += pay_data['amount']
        
        if payments_data:
            invoice.paid_amount = paid
            if paid >= total:
                invoice.status = 'paid'
            else:
                invoice.status = 'partial'
                
        invoice.save()'''
new_create = '''        for item_data in items_data:
            item_data['invoice'] = invoice
            serializer = InvoiceItemSerializer()
            serializer.create(validated_data=item_data)
        
        # total_amount is already set correctly via **validated_data from the frontend
        
        paid = 0
        for pay_data in payments_data:
            pay_data['invoice'] = invoice
            Payment.objects.create(**pay_data)
            paid += pay_data['amount']
        
        if payments_data:
            invoice.paid_amount = paid
            if paid >= float(invoice.total_amount):
                invoice.status = 'paid'
            else:
                invoice.status = 'partial'
                
        invoice.save()'''
text = text.replace(old_create, new_create)

# Fix update()
old_update = '''        # If items are provided, delete existing and recreate
        if items_data is not None:
            instance.items.all().delete()
            total = 0
            for item_data in items_data:
                item_data['invoice'] = instance
                serializer = InvoiceItemSerializer()
                item = serializer.create(validated_data=item_data)
                total += item.total_price
            instance.total_amount = total

        # Handle payments when finalizing a draft invoice
        if payments_data is not None:
            paid = 0
            for pay_data in payments_data:
                from .models import Payment
                Payment.objects.create(invoice=instance, **pay_data)
                paid += float(pay_data.get('amount', 0))
            instance.paid_amount = paid
            if paid >= float(instance.total_amount):
                instance.status = 'paid'
            elif paid > 0:
                instance.status = 'partial'
            
        instance.save()'''
new_update = '''        # If items are provided, delete existing and recreate
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                item_data['invoice'] = instance
                serializer = InvoiceItemSerializer()
                serializer.create(validated_data=item_data)
            # instance.total_amount is already set by setattr loop above

        # Handle payments when finalizing a draft invoice
        if payments_data is not None:
            paid = 0
            for pay_data in payments_data:
                from .models import Payment
                Payment.objects.create(invoice=instance, **pay_data)
                paid += float(pay_data.get('amount', 0))
            instance.paid_amount = paid
            if paid >= float(instance.total_amount):
                instance.status = 'paid'
            elif paid > 0:
                instance.status = 'partial'
            
        instance.save()'''
text = text.replace(old_update, new_update)

with open('backend/billing/serializers.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Serializers patched successfully.')

