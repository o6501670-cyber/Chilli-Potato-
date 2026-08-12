from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from decimal import Decimal
from .models import Invoice, InvoiceItem, AdvancePayment, BillChangeLog, Payment
from .serializers import InvoiceSerializer, InvoiceItemSerializer, AdvancePaymentSerializer, BillChangeLogSerializer
from rest_framework import status
from staff.models import ServiceLog
import datetime
from datetime import timedelta
import logging
from .services import finalize_invoice
from pos_backend.permissions import IsOwner

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response
        queryset = self.filter_queryset(self.get_queryset())
        if 'client_id' in request.query_params and 'page' not in request.query_params:
            queryset = queryset[:50]
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = Invoice.objects.select_related(
            'client', 'center', 'staff'
        ).prefetch_related(
            'items__content_type',
            'items__staff',
            'items__staff_members',
            'payments'
        ).order_by('-created_at')

        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                qs = qs.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                qs = qs.filter(center=user.center)

        client_id = self.request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(client_id=client_id)

        center_id = self.request.query_params.get('center_id')
        if center_id:
            try:
                qs = qs.filter(center_id=int(center_id))
            except (ValueError, TypeError):
                pass

        start_date = self.request.query_params.get('start_date')
        if start_date:
            try:
                sd = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                qs = qs.filter(created_at__gte=sd)
            except ValueError:
                pass

        end_date = self.request.query_params.get('end_date')
        if end_date:
            try:
                ed = datetime.datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                qs = qs.filter(created_at__lte=ed)
            except ValueError:
                pass

        invoice_number = self.request.query_params.get('invoice_number')
        if invoice_number:
            try:
                if invoice_number.isdigit():
                    qs = qs.filter(id=int(invoice_number))
                else:
                    parts = invoice_number.split('-')
                    last_part = parts[-1]
                    if last_part.isdigit():
                        qs = qs.filter(id=int(last_part))
            except (ValueError, TypeError):
                pass

        exclude_drafts = self.request.query_params.get('exclude_drafts')
        if exclude_drafts and exclude_drafts.lower() == 'true':
            qs = qs.exclude(status='draft')

        manager_discount = self.request.query_params.get('manager_discount')
        if manager_discount and manager_discount.lower() == 'true':
            from django.db.models import Q
            qs = qs.filter(Q(discount__gt=0) | Q(items__discount__gt=0)).distinct()

        # Default: if no date range or client filter provided, limit to last 30 days
        # to prevent unbounded full-table scans on the billing list endpoint
        has_explicit_filter = client_id or start_date or end_date or invoice_number
        if not has_explicit_filter:
            from django.utils import timezone
            qs = qs.filter(created_at__gte=timezone.now() - datetime.timedelta(days=30))

        return qs

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Record a payment against an invoice atomically."""
        invoice = self.get_object()
        old_status_for_pay = invoice.status
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'Cash')
        value_card_id = request.data.get('value_card_id')  # optional

        try:
            amt = Decimal(str(amount))
            if amt <= 0:
                raise ValueError('Must be positive')
        except Exception:
            return Response({'detail': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Lock the row to prevent race condition
            invoice = Invoice.objects.select_for_update().get(pk=pk)

            # Advance balance check INSIDE the lock to prevent over-drawing under concurrent requests
            if payment_method and ('advance' in payment_method.lower() or 'wallet' in payment_method.lower()):
                if invoice.client:
                    # advance_balance is a @property (not a DB field) — refresh_from_db() with
                    # no args reloads the actual row so we read the live balance inside the lock.
                    invoice.client.refresh_from_db()
                    advance_balance = invoice.client.advance_balance
                    if advance_balance < Decimal(str(amt)):
                        amt = Decimal(str(min(Decimal(str(amt)), max(0, advance_balance))))
                        if amt <= 0:
                            return Response(
                                {'detail': f'Insufficient advance balance. Available: ₹{advance_balance:.2f}'},
                                status=status.HTTP_400_BAD_REQUEST
                            )

            # Create Payment record
            Payment.objects.create(
                invoice=invoice,
                amount=amt,
                payment_method=payment_method,
                value_card_id=value_card_id
            )

            # Atomic increment — use F() to avoid read-modify-write race
            Invoice.objects.filter(pk=invoice.pk).update(paid_amount=F('paid_amount') + amt)
            invoice.refresh_from_db()

            # Determine new status — total_amount already includes rounding
            if invoice.paid_amount >= invoice.total_amount - Decimal('0.01'):
                Invoice.objects.filter(pk=invoice.pk).update(status='paid')
            else:
                Invoice.objects.filter(pk=invoice.pk).update(status='partial')

            invoice.refresh_from_db()

            # Handle advance deduction / value card deduction for this payment
            try:
                pm = payment_method.lower()
                if 'advance' in pm or 'wallet' in pm:
                    AdvancePayment.objects.create(
                        client=invoice.client,
                        invoice=invoice,
                        amount=-amt,
                        notes=f"Used for Invoice #{invoice.id}"
                    )
                if 'value card' in pm and value_card_id:
                    from clients.models import ClientValueCard
                    client_vc = ClientValueCard.objects.select_for_update().get(id=value_card_id)
                    client_vc.balance = max(Decimal('0'), client_vc.balance - amt)
                    if client_vc.balance <= 0:
                        client_vc.is_active = False
                    client_vc.save()
            except Exception as ex:
                logger.error(f"[Billing pay] Error handling deduction: {ex}", exc_info=True)

            # If this is the first payment that pushes a draft invoice to paid/partial,
            # run finalize_invoice with skip_payment_deductions=True since we just handled
            # the deductions above. This triggers stock, perks, and service logs.
            if old_status_for_pay == 'draft' and invoice.status in ('paid', 'partial'):
                try:
                    finalize_invoice(invoice, None, {}, skip_payment_deductions=True)
                except Exception as fe:
                    logger.error(f"[Billing pay] finalize_invoice error: {fe}", exc_info=True)

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None, new_status='cancelled'):
        invoice = self.get_object()
        if invoice.status in ('cancelled', 'refunded'):
            return Response({'detail': f'Already {invoice.status}'}, status=400)

        with transaction.atomic():
            old_status = invoice.status
            invoice.status = new_status
            invoice.save()

            user = request.user if request.user and request.user.is_authenticated else None
            BillChangeLog.objects.create(
                invoice=invoice,
                center=invoice.center,
                user=user,
                action='Cancel Bill' if new_status == 'cancelled' else 'Refund Bill'
            )

            # Create InvoiceRefund if invoice was already paid
            if old_status in ('paid', 'partial') and new_status in ('cancelled', 'refunded'):
                from billing.models import InvoiceRefund
                InvoiceRefund.objects.create(
                    invoice=invoice,
                    amount=invoice.total_amount,
                    reason='Invoice cancelled/refunded'
                )

            # Revert inventory stock — batch by content_type to avoid N+1 on content_object
            inventory_items = [
                item for item in invoice.items.select_related('content_type').all()
                if item.content_type and item.content_type.app_label == 'inventory'
            ]
            if inventory_items:
                from inventory.models import Product, StockTransaction
                product_ids = [item.object_id for item in inventory_items]
                products_map = {p.pk: p for p in Product.objects.filter(pk__in=product_ids)}
                for item in inventory_items:
                    product = products_map.get(item.object_id)
                    if product and hasattr(product, 'current_stock'):
                        try:
                            type(product).objects.filter(pk=product.pk).update(
                                current_stock=F('current_stock') + int(item.quantity)
                            )
                            StockTransaction.objects.create(
                                product=product,
                                center=invoice.center or (invoice.client.center if invoice.client else None),
                                transaction_type='REFUND',
                                quantity_change=int(item.quantity),
                                notes=f"Refunded from Invoice #{invoice.id}",
                            )
                        except Exception as e:
                            logger.error(f"[Billing Cancel] Error reverting stock: {e}", exc_info=True)

            # FIXED: Do not delete ServiceLogs — they are business/payroll records.
            # Mark them as cancelled instead by updating the invoice status (already done above).
            # The invoice FK on ServiceLog will show status='cancelled' via the related invoice.

            # Delete negative AdvancePayment rows (redemptions) tied to this invoice
            AdvancePayment.objects.filter(invoice=invoice, amount__lt=0).delete()

            # Delete negative CashbackTransaction rows (redemptions) tied to this invoice
            from billing.models import CashbackTransaction
            CashbackTransaction.objects.filter(invoice=invoice, amount__lt=0).delete()

            # Restore Package Redemptions and De-Provision Purchased Perks
            if invoice.client:
                from clients.models import ClientPackage, ClientMembership, ClientValueCard
                for item in invoice.items.all():
                    # 1. Restore Redeemed Package Services
                    if Decimal(str(item.unit_price)) == 0 and item.description and '🎁 [Redeem]' in item.description:
                        if item.content_type and item.content_type.app_label == 'services':
                            svc_id_str = str(item.object_id)
                            cps = ClientPackage.objects.filter(client=invoice.client).order_by('-expiry_date')
                            qty_to_restore = int(item.quantity)
                            
                            # Add back to the first package that contains the service ID
                            for cp in cps:
                                if svc_id_str in cp.services_remaining:
                                    cp.services_remaining[svc_id_str] += qty_to_restore
                                    cp.is_active = True # Re-activate in case it was marked exhausted
                                    cp.save()
                                    break
                    
                    # 2. De-provision Purchased Perks
                    if item.content_type and item.content_type.app_label == 'marketing':
                        try:
                            from datetime import timedelta
                            window_start = invoice.created_at - timedelta(minutes=5)
                            window_end = invoice.created_at + timedelta(minutes=5)
                            m_model = item.content_type.model
                            if m_model == 'membership' and item.content_object:
                                ClientMembership.objects.filter(
                                    source_invoice=invoice, membership_id=item.content_object.id
                                ).delete()
                            elif m_model == 'package':
                                ClientPackage.objects.filter(
                                    source_invoice=invoice, package_id=item.content_object.id if item.content_object else None
                                ).delete()
                            elif m_model == 'valuecard' and item.content_object:
                                ClientValueCard.objects.filter(
                                    source_invoice=invoice, value_card_id=item.content_object.id
                                ).delete()
                        except Exception as ex:
                            logger.error(f"[Billing Cancel] Error de-provisioning perk: {ex}", exc_info=True)

            # Reverse Value Card deductions
            for payment in invoice.payments.all():
                pm = payment.payment_method.lower()
                if 'value card' in pm and payment.value_card_id:
                    try:
                        from clients.models import ClientValueCard
                        client_vc = ClientValueCard.objects.select_for_update().get(id=payment.value_card_id)
                        client_vc.balance += payment.amount
                        client_vc.is_active = True
                        client_vc.save()
                    except Exception as e:
                        logger.error(f"[Billing Cancel] Error reverting Value Card: {e}", exc_info=True)

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Delegate to cancel action which handles all reversals atomically."""
        return self.cancel(request, pk=pk, new_status='refunded')

    @action(detail=True, methods=['post'])
    def change_payment(self, request, pk=None):
        invoice = self.get_object()
        new_method = request.data.get('payment_method')
        payment_id = request.data.get('payment_id')
        
        if not new_method:
            return Response({'detail': 'payment_method required'}, status=400)
            
        if payment_id:
            payment = invoice.payments.filter(id=payment_id).first()
            if not payment:
                return Response({'detail': 'payment_id not found for this invoice'}, status=404)
            payment.payment_method = new_method
            payment.save(update_fields=['payment_method'])
        else:
            if invoice.payments.count() > 1:
                return Response({'detail': 'Multiple payments exist. Provide a payment_id.'}, status=400)
            invoice.payments.all().update(payment_method=new_method)

        user = request.user if request.user and request.user.is_authenticated else None
        BillChangeLog.objects.create(
            invoice=invoice,
            center=invoice.center,
            user=user,
            action=f"Change Payment Type {'(Partial)' if payment_id else '(All)'}"
        )
        return Response(InvoiceSerializer(invoice).data)



    @action(detail=True, methods=['post'])
    def apply_promo(self, request, pk=None):
        invoice = self.get_object()
        promo_id = request.data.get('promo_id')
        from marketing.promotions import apply_promotion
        discount, error = apply_promotion(invoice, promo_id)
        if error:
            return Response({'error': error}, status=400)
        invoice.discount = (invoice.discount or 0) + Decimal(str(discount))
        invoice.total_amount = max(
            Decimal('0'),
            invoice.subtotal - invoice.discount + invoice.cgst + invoice.sgst
        )
        invoice.save()
        return Response({'discount_applied': discount, 'new_total': Decimal(str(invoice.total_amount))})

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Make a mutable copy safely, handling both QueryDict and dict
        if hasattr(request.data, 'dict'):
            sanitized = request.data.dict()
        else:
            sanitized = dict(request.data)

        # Handle form-data where 'items' might be a JSON string
        if isinstance(sanitized.get('items'), str):
            import json
            try:
                sanitized['items'] = json.loads(sanitized['items'])
            except Exception:
                import logging; logging.getLogger(__name__).error('Handled exception', exc_info=True)

        try:
            if isinstance(sanitized, dict) and 'staff' in sanitized:
                sv = sanitized.get('staff')
                if isinstance(sv, dict) and 'id' in sv:
                    sanitized['staff'] = sv['id']
                if isinstance(sanitized.get('staff'), str) and sanitized['staff'].isdigit():
                    sanitized['staff'] = int(sanitized['staff'])

            items = sanitized.get('items')
            if isinstance(items, list):
                mutable_items = []
                for it in items:
                    if isinstance(it, dict):
                        mut_it = dict(it)
                        if 'staff' in mut_it:
                            sv = mut_it.get('staff')
                            if isinstance(sv, dict) and 'id' in sv:
                                mut_it['staff'] = sv['id']
                            if isinstance(mut_it.get('staff'), str) and mut_it['staff'].isdigit():
                                mut_it['staff'] = int(mut_it['staff'])
                        mutable_items.append(mut_it)
                    else:
                        mutable_items.append(it)
                sanitized['items'] = mutable_items
        except Exception as e:
            logger.warning('[Billing] failed to prepare sanitized payload: %s', e)
            sanitized = request.data

        client_id = sanitized.get('client')
        if client_id:
            try:
                from clients.models import Client
                client = Client.objects.get(pk=client_id)
                if client.is_blacklisted:
                    return Response({'error': 'Client is blacklisted and cannot be billed.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                import logging; logging.getLogger(__name__).error('Handled exception', exc_info=True)

        serializer = self.get_serializer(data=sanitized)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({
                'detail': 'Invoice validation failed',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    return Response({"detail": "You cannot create invoices for this center."}, status=403)
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    return Response({"detail": "You cannot create invoices for this center."}, status=403)

        invoice = serializer.save()

        # PREFETCH related items to fix N+1 queries during serialization
        invoice = Invoice.objects.prefetch_related(
            'items__content_type', 'items__staff', 'items__staff_members', 'payments'
        ).get(pk=invoice.pk)

        if invoice.status in ('paid', 'partial'):
            appointment_id = request.data.get('appointment_id')
            # Payments embedded in create are handled by finalize_invoice (skip_payment_deductions=False)
            finalize_invoice(invoice, appointment_id, request.data, skip_payment_deductions=False)

            # Audit trail: log bill creation for manager discount tracking
            user = request.user if request.user and request.user.is_authenticated else None
            BillChangeLog.objects.create(
                invoice=invoice,
                center=invoice.center,
                user=user,
                action='Create Bill',
                notes=f"Total: ₹{invoice.total_amount} | Discount: ₹{invoice.discount}"
            )

        headers = self.get_success_headers(serializer.data)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Lock the invoice row first to prevent concurrent double-finalization
        invoice_id = self.kwargs.get('pk')
        Invoice.objects.select_for_update().get(pk=invoice_id)

        invoice = self.get_object()
        old_status = invoice.status
        super().update(request, *args, **kwargs)
        invoice.refresh_from_db()

        # PREFETCH related items to fix N+1 queries during serialization
        invoice = Invoice.objects.prefetch_related(
            'items__content_type', 'items__staff', 'items__staff_members', 'payments'
        ).get(pk=invoice.pk)

        # Only run finalization if transitioning FROM draft to paid/partial — guarded by row lock above
        if old_status == 'draft' and invoice.status in ('paid', 'partial'):
            appointment_id = request.data.get('appointment_id')
            finalize_invoice(invoice, appointment_id, request.data, skip_payment_deductions=False)

            # Audit trail: log when a draft is finalized to paid
            user = request.user if request.user and request.user.is_authenticated else None
            BillChangeLog.objects.create(
                invoice=invoice,
                center=invoice.center,
                user=user,
                action='Finalize Bill',
                notes=f"Total: ₹{invoice.total_amount} | Discount: ₹{invoice.discount}"
            )

        # Return re-serialized response with prefetched relations (not the super() response which has N+1)
        return Response(InvoiceSerializer(invoice).data)


class AdvancePaymentViewSet(viewsets.ModelViewSet):
    queryset = AdvancePayment.objects.all().select_related('client', 'invoice', 'client__center').order_by('-created_at')
    serializer_class = AdvancePaymentSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from rest_framework.response import Response
        queryset = self.filter_queryset(self.get_queryset())
        if 'client_id' in request.query_params and 'page' not in request.query_params:
            queryset = queryset[:50]
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                qs = qs.filter(client__center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                qs = qs.filter(client__center=user.center)
                
        client_id = self.request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(client_id=client_id)
        center_id = self.request.query_params.get('center_id')
        if center_id:
            try:
                qs = qs.filter(client__center_id=int(center_id))
            except (ValueError, TypeError):
                pass
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        
        if not is_owner and not perms.get('all_centers', False):
            client = serializer.validated_data.get('client')
            if client and client.center:
                if user.centers.exists() and client.center not in user.centers.all():
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create advance payments for clients of this center.")
                elif not user.centers.exists() and hasattr(user, 'center') and client.center != user.center:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You cannot create advance payments for clients of this center.")
        serializer.save()


class BillChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BillChangeLog.objects.select_related('invoice', 'center', 'user').order_by('-created_at')
    serializer_class = BillChangeLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = IsOwner.check_is_owner(user)
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                qs = qs.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                qs = qs.filter(center=user.center)
                
        center_id = self.request.query_params.get('center_id')
        if center_id:
            try:
                qs = qs.filter(center_id=int(center_id))
            except (ValueError, TypeError):
                pass
                
        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
            
        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
            
        return qs
