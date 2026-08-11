from rest_framework import serializers
from .models import Invoice, InvoiceItem, AdvancePayment, Payment, BillChangeLog
from django.contrib.contenttypes.models import ContentType
from staff.models import StaffMember
from decimal import Decimal


class InvoiceItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    content_type = serializers.CharField(required=False, allow_null=True)
    staff = serializers.PrimaryKeyRelatedField(queryset=StaffMember.objects.all(), required=False, allow_null=True)
    staff_members = serializers.PrimaryKeyRelatedField(queryset=StaffMember.objects.all(), required=False, many=True, allow_empty=True)

    class Meta:
        model = InvoiceItem
        fields = ('id', 'content_type', 'object_id', 'description', 'unit_price', 'discount', 'quantity',
                  'tax_percentage', 'tax_amount', 'total_price', 'staff', 'staff_members')

    def to_internal_value(self, data):
        if isinstance(data, dict):
            # Normalise nested staff objects → IDs
            if 'staff' in data:
                staff_value = data.get('staff')
                if isinstance(staff_value, dict) and 'id' in staff_value:
                    data['staff'] = staff_value['id']
            if 'staff_members' in data and isinstance(data.get('staff_members'), list):
                new_members = []
                for s in data['staff_members']:
                    if isinstance(s, dict) and 'id' in s:
                        new_members.append(s['id'])
                    else:
                        new_members.append(s)
                data['staff_members'] = new_members
        return super().to_internal_value(data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Return content_type as "app_label.model" (e.g. "services.servicemaster")
        # The default CharField serialization calls str(ContentType) which gives "app | model",
        # but the frontend splits on "." so we must use dot notation.
        if instance.content_type:
            ret['content_type'] = f"{instance.content_type.app_label}.{instance.content_type.model}"
        else:
            ret['content_type'] = None

        # Auto-populate tax_percentage from master if not stored on item yet (backward compat)
        if not instance.tax_percentage and instance.content_object:
            try:
                if hasattr(instance.content_object, 'tax_percentage'):
                    ret['tax_percentage'] = float(instance.content_object.tax_percentage)
                elif hasattr(instance.content_object, 'gst_percent'):
                    ret['tax_percentage'] = float(instance.content_object.gst_percent)
            except Exception:
                pass

        # Compute tax_amount from stored tax_percentage if not stored
        tax_pct = float(ret.get('tax_percentage') or 0)
        if not instance.tax_amount and tax_pct:
            # tax is computed on the pre-tax base: base = total_price / (1 + tax_pct/100)
            total = float(instance.total_price or 0)
            base = total / (1 + tax_pct / 100) if (1 + tax_pct / 100) > 0 else total
            ret['tax_amount'] = round(total - base, 2)
        return ret

    def create(self, validated_data):
        ct_label = validated_data.pop('content_type', None)
        if ct_label:
            try:
                app_label, model = ct_label.split('.')
                validated_data['content_type'] = ContentType.objects.get(app_label=app_label, model=model)
            except Exception:
                validated_data['content_type'] = None
        staff_members_data = validated_data.pop('staff_members', [])
        item = InvoiceItem.objects.create(**validated_data)
        if staff_members_data:
            item.staff_members.set(staff_members_data)
        return item


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = Payment
        fields = ('id', 'amount', 'payment_method', 'value_card_id', 'created_at')
        read_only_fields = ('created_at',)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    payments = PaymentSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = (
            'id', 'client', 'center', 'staff', 'appointment',
            'subtotal', 'discount', 'cgst', 'sgst', 'rounding',
            'total_amount', 'paid_amount', 'tip_amount', 'status', 'notes',
            'created_at', 'items', 'payments'
        )
        read_only_fields = ('created_at',)

    def validate(self, data):
        center = data.get('center')
        if not center and self.instance:
            center = self.instance.center
        
        # Cross-check: if client is being set, they should belong to this center
        client = data.get('client')
        if client and center and client.center and client.center != center:
            import logging
            logging.getLogger(__name__).warning(
                f'[Billing] Client {client.id} center ({client.center_id}) does not match '
                f'invoice center ({center.id}). Allowing but flagging.'
            )

        for item in data.get('items', []):
            staff = item.get('staff')
            if staff and hasattr(staff, 'center') and staff.center != center:
                raise serializers.ValidationError("Staff member does not belong to this center.")
                
            for sm in item.get('staff_members', []):
                if sm and hasattr(sm, 'center') and sm.center != center:
                    raise serializers.ValidationError("One or more staff members do not belong to this center.")
                    
            ct_label = item.get('content_type')
            if ct_label and isinstance(ct_label, str) and ct_label.startswith('inventory'):
                obj_id = item.get('object_id')
                if obj_id:
                    try:
                        from inventory.models import Product
                        prod = Product.objects.get(pk=obj_id)
                        if prod.center != center:
                            raise serializers.ValidationError("Product does not belong to this center.")
                    except Exception:
                        pass
        
        # Validate advance and value card payments against actual balances
        payments = data.get('payments', [])
        from decimal import Decimal
        for p in payments:
            if Decimal(str(p.get('amount', 0))) <= 0:
                raise serializers.ValidationError("Payment amounts must be greater than zero.")
        
        if payments and client:
            from decimal import Decimal
            
            # Advance Payment validation
            advance_requested = sum(
                Decimal(str(p.get('amount', 0))) for p in payments 
                if p.get('payment_method') and ('advance' in p.get('payment_method').lower() or ('wallet' in p.get('payment_method').lower() and 'cashback wallet' not in p.get('payment_method').lower()))
            )
            if advance_requested > 0:
                advance_bal = getattr(client, 'advance_balance', Decimal('0'))
                if advance_bal < advance_requested:
                    raise serializers.ValidationError(
                        f"Insufficient advance balance. Requested: ₹{advance_requested}, Available: ₹{advance_bal}"
                    )
            
            # Cashback Wallet validation
            cashback_requested = sum(
                Decimal(str(p.get('amount', 0))) for p in payments 
                if p.get('payment_method') and 'cashback wallet' in p.get('payment_method').lower()
            )
            if cashback_requested > 0:
                cashback_bal = getattr(client, 'cashback_balance', Decimal('0'))
                if cashback_bal < cashback_requested:
                    raise serializers.ValidationError(
                        f"Insufficient cashback balance. Requested: ₹{cashback_requested}, Available: ₹{cashback_bal}"
                    )
            
            # Value Card validation
            for p in payments:
                pm = p.get('payment_method', '')
                if pm and 'value card' in pm.lower() and p.get('value_card_id'):
                    vc_id = p.get('value_card_id')
                    from clients.models import ClientValueCard
                    try:
                        vc = ClientValueCard.objects.select_for_update().get(id=vc_id, client=client)
                    except ClientValueCard.DoesNotExist:
                        raise serializers.ValidationError("Value card not found or does not belong to client.")
                    # Check balance separately so the correct error message reaches the user
                    req_amt = Decimal(str(p.get('amount', 0)))
                    if vc.balance < req_amt:
                        raise serializers.ValidationError(
                            f"Insufficient value card balance. Requested: ₹{req_amt}, Available: ₹{vc.balance}"
                        )

            # Package Redemption Validation
            redeemed_counts = {}
            for item in data.get('items', []):
                desc = item.get('description', '')
                if desc and '🎁 [Redeem]' in desc:
                    obj_id = item.get('object_id')
                    if obj_id:
                        svc_id = str(obj_id)
                        qty = int(item.get('quantity', 1))
                        redeemed_counts[svc_id] = redeemed_counts.get(svc_id, 0) + qty
            
            if redeemed_counts:
                import datetime
                from clients.models import ClientPackage
                active_packages = ClientPackage.objects.filter(
                    client=client, 
                    is_active=True, 
                    expiry_date__gte=datetime.date.today()
                )
                available_counts = {}
                for ap in active_packages:
                    for svc_id, rem in ap.services_remaining.items():
                        available_counts[svc_id] = available_counts.get(svc_id, 0) + rem
                
                for svc_id, req_qty in redeemed_counts.items():
                    avail = available_counts.get(svc_id, 0)
                    if req_qty > avail:
                        raise serializers.ValidationError(
                            f"Cannot redeem {req_qty} services. Only {avail} left in package."
                        )

        # Mathematical Validation to prevent invoice forgery
        from decimal import Decimal
        expected_subtotal = Decimal('0')
        for item in data.get('items', []):
            qty = Decimal(str(item.get('quantity', 1)))
            unit_price = Decimal(str(item.get('unit_price', 0)))
            item_discount = Decimal(str(item.get('discount', 0)))
            
            if qty <= 0:
                raise serializers.ValidationError("Item quantity must be greater than zero.")
            if unit_price < 0:
                raise serializers.ValidationError("Item unit price cannot be negative.")
            if item_discount < 0:
                raise serializers.ValidationError("Item discount cannot be negative.")
            if item_discount > (unit_price * qty):
                raise serializers.ValidationError("Item discount cannot exceed its total value.")
            
            is_redemption = bool(item.get('description') and '🎁 [Redeem]' in item.get('description'))
            if not is_redemption:
                expected_item_total = max(Decimal('0'), (unit_price * qty) - item_discount)
            else:
                expected_item_total = Decimal('0')
                
            expected_subtotal += expected_item_total
            
        client_subtotal = Decimal(str(data.get('subtotal', 0)))
        if abs(client_subtotal - expected_subtotal) > Decimal('0.1'):
            raise serializers.ValidationError(f"Invoice subtotal {client_subtotal} does not match sum of items {expected_subtotal}.")
            
        discount = Decimal(str(data.get('discount', 0)))
        if discount < 0:
            raise serializers.ValidationError("Global discount cannot be negative.")
        if discount > expected_subtotal:
            raise serializers.ValidationError("Global discount cannot exceed the subtotal.")

        cgst = Decimal(str(data.get('cgst', 0)))
        sgst = Decimal(str(data.get('sgst', 0)))
        if cgst < 0 or sgst < 0:
            raise serializers.ValidationError("Taxes cannot be negative.")

        rounding = Decimal(str(data.get('rounding', 0)))
        
        expected_total = max(Decimal('0'), expected_subtotal - discount + cgst + sgst) + rounding
        client_total = Decimal(str(data.get('total_amount', 0)))
        
        if abs(client_total - expected_total) > Decimal('0.1'):
            raise serializers.ValidationError(
                f"Invoice total amount {client_total} does not match mathematical calculation {expected_total}."
            )

        promo_id = self.initial_data.get('promo_id') if hasattr(self, 'initial_data') else None
        if promo_id:
            try:
                from marketing.models import Promotion, PromotionUsage
                promo = Promotion.objects.get(id=promo_id, is_active=True)
                if promo.max_usage_per_client and client:
                    usage_count = PromotionUsage.objects.filter(
                        promotion=promo, client=client
                    ).count()
                    if usage_count >= promo.max_usage_per_client:
                        raise serializers.ValidationError(f"Usage limit reached for promotion: {promo.name}")
            except serializers.ValidationError:
                raise
            except Exception:
                pass # invalid promo_id handled silently or elsewhere

        return data

    def to_internal_value(self, data):
        """Normalise nested staff objects at invoice and item level."""
        try:
            if isinstance(data, dict):
                if 'staff' in data and isinstance(data.get('staff'), dict) and 'id' in data.get('staff'):
                    data['staff'] = data['staff']['id']
                items = data.get('items')
                if isinstance(items, list):
                    for it in items:
                        if isinstance(it, dict) and 'staff' in it and isinstance(it.get('staff'), dict) and 'id' in it.get('staff'):
                            it['staff'] = it['staff']['id']
        except Exception:
            pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        payments_data = validated_data.pop('payments', [])

        invoice = Invoice.objects.create(**validated_data)

        # Pass 1: Build InvoiceItem instances and extract M2M data separately.
        # bulk_create cannot handle M2M, so we save staff_members for a second pass.
        item_instances = []
        m2m_map = []  # list of (item_index, staff_members list)
        for idx, item_data in enumerate(items_data):
            item_data = dict(item_data)
            staff_members = item_data.pop('staff_members', [])
            item_data['invoice'] = invoice

            # Resolve content_type label → ContentType object (same as InvoiceItemSerializer.create)
            ct_label = item_data.pop('content_type', None)
            if ct_label and isinstance(ct_label, str):
                try:
                    from django.contrib.contenttypes.models import ContentType as CT
                    app_label, model = ct_label.split('.')
                    item_data['content_type'] = CT.objects.get(app_label=app_label, model=model)
                except Exception:
                    item_data['content_type'] = None

            item_instances.append(InvoiceItem(**item_data))
            if staff_members:
                m2m_map.append((idx, staff_members))

        # We cannot reliably use bulk_create here because depending on the DB backend, 
        # it may not assign the generated PKs to the instances, breaking the M2M assignment below.
        # Since an invoice typically has a small number of items, looping save() is safe and robust.
        created_items = []
        for item in item_instances:
            item.save()
            created_items.append(item)

        # Pass 2: Set M2M staff_members only for items that need it
        for idx, staff_members in m2m_map:
            created_items[idx].staff_members.set(staff_members)

        paid = Decimal('0')
        for pay_data in payments_data:
            pay_data['invoice'] = invoice
            Payment.objects.create(**pay_data)
            paid += Decimal(str(pay_data.get('amount', 0)))

        if payments_data:
            invoice.paid_amount = paid
            # Use Decimal comparison to avoid floating-point drift
            if paid >= invoice.total_amount:
                invoice.status = 'paid'
            else:
                invoice.status = 'partial'

        invoice.save()
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        payments_data = validated_data.pop('payments', None)

        # Update invoice scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Replace items if provided
        if items_data is not None:
            existing_items = {item.id: item for item in instance.items.all()}
            incoming_ids = [item.get('id') for item in items_data if item.get('id')]
            
            # Delete removed items
            for item_id, item in existing_items.items():
                if item_id not in incoming_ids:
                    item.delete()
                    
            for item_data in items_data:
                item_id = item_data.get('id')
                # Need to resolve content_type like the create method does
                ct_label = item_data.pop('content_type', None)
                if ct_label and isinstance(ct_label, str):
                    try:
                        app_label, model = ct_label.split('.')
                        item_data['content_type'] = ContentType.objects.get(app_label=app_label, model=model)
                    except Exception:
                        item_data['content_type'] = None
                
                staff_members = item_data.pop('staff_members', None)
                
                if item_id and item_id in existing_items:
                    # Update existing
                    item_instance = existing_items[item_id]
                    for attr, val in item_data.items():
                        setattr(item_instance, attr, val)
                    item_instance.save()
                    if staff_members is not None:
                        item_instance.staff_members.set(staff_members)
                else:
                    # Create new item — pop 'id' to avoid write conflict
                    item_data.pop('id', None)
                    item_data['invoice'] = instance
                    item_instance = InvoiceItem.objects.create(**item_data)
                    if staff_members is not None:
                        item_instance.staff_members.set(staff_members)

        # Sync payments
        if payments_data is not None:
            existing_payments = {p.id: p for p in instance.payments.all()}
            incoming_pay_ids = [p.get('id') for p in payments_data if p.get('id')]
            
            for p_id, p in existing_payments.items():
                if p_id not in incoming_pay_ids:
                    p.delete()
                    
            paid = Decimal('0')
            for pay_data in payments_data:
                p_id = pay_data.get('id')
                if p_id and p_id in existing_payments:
                    pay_instance = existing_payments[p_id]
                    for attr, val in pay_data.items():
                        setattr(pay_instance, attr, val)
                    pay_instance.save()
                    paid += Decimal(str(pay_instance.amount))
                else:
                    new_pay = Payment.objects.create(invoice=instance, **pay_data)
                    paid += Decimal(str(new_pay.amount))
                    
            instance.paid_amount = paid
            if paid >= instance.total_amount:
                instance.status = 'paid'
            elif paid > 0:
                instance.status = 'partial'

        instance.save()
        return instance

    def to_representation(self, instance):
        repr_data = super().to_representation(instance)

        if instance.client:
            repr_data['client'] = {
                'id': instance.client.id,
                'first_name': instance.client.first_name,
                'last_name': instance.client.last_name or '',
                'phone': instance.client.phone,
            }

        if instance.center:
            repr_data['center_detail'] = {
                'id': instance.center.id,
                'name': instance.center.display_name or instance.center.center_name or '',
                'address': instance.center.address or '',
                'phone': getattr(instance.center, 'phone', '') or '',
            }

        # Enrich items with full staff_members objects, using prefetch_related to eliminate N+1 queries
        for item_repr, item_instance in zip(repr_data.get('items', []), instance.items.prefetch_related('staff_members').all()):
            item_repr['staff_members'] = [
                {'id': s.id, 'name': f"{s.first_name} {s.last_name or ''}".strip()}
                for s in item_instance.staff_members.all()
            ]

        return repr_data


class AdvancePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvancePayment
        fields = ('id', 'client', 'invoice', 'staff', 'amount', 'notes', 'created_at')
        read_only_fields = ('created_at',)


class BillChangeLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    center_name = serializers.SerializerMethodField()
    bill_amount = serializers.SerializerMethodField()
    bill_date = serializers.SerializerMethodField()

    class Meta:
        model = BillChangeLog
        fields = ('id', 'invoice', 'center', 'center_name', 'user', 'user_name', 'action', 'notes', 'created_at', 'bill_amount', 'bill_date')

    def get_user_name(self, obj):
        if not obj.user:
            return ""
        return obj.user.full_name or getattr(obj.user, 'email', '') or str(obj.user)

    def get_center_name(self, obj):
        if obj.center:
            return obj.center.display_name or obj.center.center_name
        return None

    def get_bill_amount(self, obj):
        if obj.invoice:
            return str(obj.invoice.total_amount)
        return ''

    def get_bill_date(self, obj):
        if obj.invoice and obj.invoice.created_at:
            return obj.invoice.created_at.isoformat()
        return ''
