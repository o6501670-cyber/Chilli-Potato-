from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError
from django.db.models import F, Sum
from django.utils import timezone
from decimal import Decimal
from .models import Invoice, InvoiceItem, AdvancePayment, BillChangeLog, Payment, InvoiceRefund
from .serializers import InvoiceSerializer, InvoiceItemSerializer, AdvancePaymentSerializer, BillChangeLogSerializer, InvoiceRefundSerializer
from rest_framework import status
from staff.models import ServiceLog
import datetime
from datetime import timedelta
import logging
from .services import finalize_invoice
from accounts.permissions import RoleActionPermission

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [RoleActionPermission]

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
            'client', 'center', 'staff', 'promotion', 'membership'
        ).prefetch_related(
            'items__content_type',
            'items__content_object',
            'items__staff',
            'items__staff_members',
            'payments'
        ).order_by('-created_at')

        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        if not is_owner and not perms.get('all_centers', False):
            if user.centers.exists():
                qs = qs.filter(center__in=user.centers.all())
            elif hasattr(user, 'center') and user.center:
                qs = qs.filter(center=user.center)
            else:
                qs = qs.none()

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

        return qs

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Record one payment with balance and tender validation.

        The payment row, wallet debit, value-card debit, invoice status and
        paid amount must succeed or fail together. This endpoint is also the
        concurrency boundary for two registers trying to pay the same bill.
        """
        self.get_object()  # enforce the caller's centre scope before locking
        amount = request.data.get('amount')
        payment_method = str(request.data.get('payment_method', 'Cash')).strip()
        value_card_id = request.data.get('value_card_id')

        valid_methods = {choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES}
        if payment_method not in valid_methods:
            return Response({'detail': 'Unsupported payment method.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amt = Decimal(str(amount)).quantize(Decimal('0.01'))
        except Exception:
            return Response({'detail': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amt <= 0:
            return Response({'detail': 'Payment amount must be greater than zero.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().select_related('client').get(pk=pk)
            if invoice.status in ('cancelled', 'refunded'):
                return Response(
                    {'detail': f'Cannot pay an invoice that is already {invoice.status}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            outstanding = max(Decimal('0'), invoice.total_amount - invoice.paid_amount)
            if amt > outstanding + Decimal('0.01'):
                return Response(
                    {'detail': f'Payment exceeds the outstanding balance of ₹{outstanding:.2f}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            client = None
            if invoice.client_id:
                from clients.models import Client
                client = Client.objects.select_for_update().get(pk=invoice.client_id)

            pm = payment_method.lower()
            if ('advance' in pm or ("wallet" in pm and pm != 'cashback wallet')):
                if not client:
                    return Response({'detail': 'A client is required for advance payments.'}, status=400)
                balance = AdvancePayment.objects.filter(client_id=client.id).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                if balance < amt:
                    return Response(
                        {'detail': f'Insufficient advance balance. Available: ₹{balance:.2f}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif pm == 'cashback wallet':
                if not client:
                    return Response({'detail': 'A client is required for cashback payments.'}, status=400)
                from billing.models import CashbackTransaction
                balance = CashbackTransaction.objects.filter(client_id=client.id).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                if balance < amt:
                    return Response(
                        {'detail': f'Insufficient cashback balance. Available: ₹{balance:.2f}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif pm == 'value card':
                if not client or not value_card_id:
                    return Response({'detail': 'A client and value_card_id are required for value-card payments.'}, status=400)
                from clients.models import ClientValueCard
                try:
                    value_card = ClientValueCard.objects.select_for_update().get(
                        pk=int(value_card_id),
                        client_id=client.id,
                        is_active=True,
                        expiry_date__gte=timezone.now().date(),
                    )
                except (TypeError, ValueError, ClientValueCard.DoesNotExist):
                    return Response({'detail': 'Value card not found, expired, or not owned by this client.'}, status=400)
                if value_card.balance < amt:
                    return Response(
                        {'detail': f'Insufficient value-card balance. Available: ₹{value_card.balance:.2f}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                value_card = None

            Payment.objects.create(
                invoice=invoice,
                amount=amt,
                payment_method=payment_method,
                value_card_id=int(value_card_id) if value_card_id and pm == 'value card' else None,
            )

            if 'advance' in pm or ("wallet" in pm and pm != 'cashback wallet'):
                AdvancePayment.objects.create(
                    client=client,
                    invoice=invoice,
                    amount=-amt,
                    notes=f'Used for Invoice #{invoice.id}',
                )
            elif pm == 'cashback wallet':
                from billing.models import CashbackTransaction
                CashbackTransaction.objects.create(
                    client=client,
                    invoice=invoice,
                    amount=-amt,
                    notes=f'Used for Invoice #{invoice.id}',
                )
            elif pm == 'value card':
                value_card.balance -= amt
                if value_card.balance <= 0:
                    value_card.balance = Decimal('0')
                    value_card.is_active = False
                value_card.save(update_fields=['balance', 'is_active'])

            old_status = invoice.status
            invoice.paid_amount += amt
            invoice.status = 'paid' if invoice.paid_amount >= invoice.total_amount - Decimal('0.01') else 'partial'
            invoice.save(update_fields=['paid_amount', 'status', 'updated_at'])

            if old_status == 'draft' and invoice.status in ('paid', 'partial'):
                # The invoice already contains its line items. Wallet/card
                # debits were handled above, so finalization must not debit them again.
                finalize_invoice(
                    invoice,
                    None,
                    {
                        'promo_id': invoice.promotion_id,
                        'membership_id': invoice.membership_id,
                    },
                    skip_payment_deductions=True,
                )

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None, new_status='cancelled'):
        """Cancel an unfinalized draft. Paid bills must use the refund action."""
        self.get_object()
        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().select_related('center').get(pk=pk)
            if invoice.status in ('cancelled', 'refunded'):
                return Response({'detail': f'Already {invoice.status}'}, status=400)
            if invoice.status != 'draft':
                return Response(
                    {'detail': 'Paid or partial invoices cannot be cancelled; create a refund instead.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invoice.status = 'cancelled'
            invoice.save(update_fields=['status', 'updated_at'])
            BillChangeLog.objects.create(
                invoice=invoice,
                center=invoice.center,
                user=request.user if request.user.is_authenticated else None,
                action='Cancel Bill',
                notes='Draft invoice cancelled before finalization.',
            )
        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Issue one complete refund and reverse every finalized side effect."""
        self.get_object()
        refund_methods = {choice[0] for choice in InvoiceRefund.REFUND_METHOD_CHOICES}
        refund_method = str(request.data.get('refund_method', 'Original')).strip()
        if refund_method not in refund_methods:
            return Response({'detail': 'Unsupported refund method.'}, status=400)

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().select_related('client', 'center').get(pk=pk)
            if invoice.status not in ('paid', 'partial'):
                return Response({'detail': 'Only paid or partial invoices can be refunded.'}, status=400)
            refunded_total = invoice.refunds.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            remaining = invoice.paid_amount - refunded_total
            if remaining <= 0:
                return Response({'detail': 'Invoice has already been fully refunded.'}, status=400)

            requested = request.data.get('amount', remaining)
            try:
                amount = Decimal(str(requested)).quantize(Decimal('0.01'))
            except Exception:
                return Response({'detail': 'Invalid refund amount.'}, status=400)
            # Partial refunds need tender allocation and proportional perk
            # reversal. Refuse them rather than silently corrupting wallets.
            if amount != remaining:
                return Response(
                    {'detail': f'Only a full refund of ₹{remaining:.2f} is currently supported.'},
                    status=400,
                )

            InvoiceRefund.objects.create(
                invoice=invoice,
                amount=amount,
                refund_method=refund_method,
                reference=request.data.get('reference'),
                notes=request.data.get('notes'),
                created_by=request.user if request.user.is_authenticated else None,
            )

            from inventory.models import Product, StockTransaction
            inventory_items = invoice.items.select_related('content_type').all()
            for item in inventory_items:
                if not item.content_type or item.content_type.app_label != 'inventory':
                    continue
                product = Product.objects.select_for_update().filter(pk=item.object_id).first()
                if not product:
                    raise ValidationError(f'Product for invoice item {item.id} no longer exists.')
                product.current_stock += int(item.quantity)
                product.save(update_fields=['current_stock'])
                StockTransaction.objects.create(
                    product=product,
                    center=invoice.center or (invoice.client.center if invoice.client else None),
                    transaction_type='REFUND',
                    quantity_change=int(item.quantity),
                    notes=f'Refunded Invoice #{invoice.id}',
                    created_by=request.user if request.user.is_authenticated else None,
                )

            from clients.models import ClientMembership, ClientPackage, ClientValueCard, PackageRedemption
            # Restore package redemptions from the exact package rows allocated
            # during finalization, not an arbitrary matching package.
            for redemption in PackageRedemption.objects.select_for_update().filter(invoice=invoice).select_related('package'):
                package = redemption.package
                remaining_services = dict(package.services_remaining or {})
                key = str(redemption.service_id)
                remaining_services[key] = int(remaining_services.get(key, 0)) + redemption.quantity
                package.services_remaining = remaining_services
                package.is_active = True
                package.save(update_fields=['services_remaining', 'is_active'])
            PackageRedemption.objects.filter(invoice=invoice).delete()

            # Remove only entitlements created by this invoice.
            ClientMembership.objects.filter(source_invoice=invoice).delete()
            ClientPackage.objects.filter(source_invoice=invoice).delete()
            ClientValueCard.objects.filter(source_invoice=invoice).delete()

            # Reverse tender liabilities and promotion cashback tied to this bill.
            AdvancePayment.objects.filter(invoice=invoice).delete()
            from billing.models import CashbackTransaction
            CashbackTransaction.objects.filter(invoice=invoice).delete()
            for payment in invoice.payments.all():
                if payment.payment_method.lower() == 'value card' and payment.value_card_id and invoice.client_id:
                    value_card = ClientValueCard.objects.select_for_update().filter(
                        pk=payment.value_card_id, client_id=invoice.client_id
                    ).first()
                    if value_card:
                        value_card.balance += payment.amount
                        value_card.is_active = True
                        value_card.save(update_fields=['balance', 'is_active'])

            from marketing.models import PromotionUsage
            PromotionUsage.objects.filter(invoice=invoice).delete()
            invoice.status = 'refunded'
            invoice.save(update_fields=['status', 'updated_at'])
            BillChangeLog.objects.create(
                invoice=invoice,
                center=invoice.center,
                user=request.user if request.user.is_authenticated else None,
                action='Refund Bill',
                notes=f'Full refund ₹{amount:.2f} via {refund_method}.',
            )

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'])
    def change_payment(self, request, pk=None):
        invoice = self.get_object()
        new_method = str(request.data.get('payment_method', '')).strip()
        valid_methods = {choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES}
        if new_method not in valid_methods:
            return Response({'detail': 'Unsupported payment method.'}, status=400)
        if invoice.status in ('cancelled', 'refunded'):
            return Response({'detail': 'Cannot change payment method on a cancelled/refunded invoice.'}, status=400)
        existing_methods = list(invoice.payments.values_list('payment_method', flat=True))
        liability_methods = {'advance', 'cashback wallet', 'value card'}
        if invoice.finalized_at and any(
            method.lower() in liability_methods or new_method.lower() in liability_methods
            for method in existing_methods
        ):
            return Response(
                {'detail': 'Finalized wallet/value-card tenders cannot be changed. Refund and reissue the bill.'},
                status=400,
            )

        invoice.payments.all().update(payment_method=new_method)

        user = request.user if request.user and request.user.is_authenticated else None
        BillChangeLog.objects.create(
            invoice=invoice,
            center=invoice.center,
            user=user,
            action='Change Payment Type'
        )
        return Response(InvoiceSerializer(invoice).data)



    @action(detail=True, methods=['post'])
    def apply_promo(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status != 'draft' or invoice.finalized_at:
            return Response({'error': 'Promotions can only be applied to draft invoices.'}, status=400)
        promo_id = request.data.get('promo_id')
        from marketing.promotions import apply_promotion
        discount, error = apply_promotion(invoice, promo_id, record_usage=False)
        if error:
            return Response({'error': error}, status=400)
        invoice.promotion_id = int(promo_id)
        invoice.discount = (invoice.discount or 0) + Decimal(str(discount))
        invoice.total_amount = max(
            Decimal('0'),
            invoice.subtotal - invoice.discount + invoice.cgst + invoice.sgst
        )
        invoice.save(update_fields=['promotion', 'discount', 'total_amount', 'updated_at'])
        return Response({'discount_applied': discount, 'new_total': float(invoice.total_amount)})

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
                pass

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

        idempotency_key = request.headers.get('Idempotency-Key') or sanitized.get('idempotency_key')
        if idempotency_key:
            idempotency_key = str(idempotency_key).strip()
            if len(idempotency_key) > 100:
                return Response({'detail': 'Idempotency-Key is too long.'}, status=400)
            existing = self.get_queryset().filter(idempotency_key=idempotency_key).first()
            if existing:
                return Response(InvoiceSerializer(existing).data, status=status.HTTP_200_OK)
            sanitized['idempotency_key'] = idempotency_key

        client_id = sanitized.get('client')
        if client_id:
            try:
                from clients.models import Client
                client = Client.objects.get(pk=client_id)
                if client.is_blacklisted:
                    return Response({'error': 'Client is blacklisted and cannot be billed.'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                pass

        serializer = self.get_serializer(data=sanitized)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return Response({
                'detail': 'Invoice validation failed',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception('Unexpected invoice validation failure')
            return Response({
                'detail': 'Invoice validation failed due to an internal validation error.'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
        if not is_owner and not perms.get('all_centers', False):
            center = serializer.validated_data.get('center')
            if center:
                if user.centers.exists() and center not in user.centers.all():
                    return Response({"detail": "You cannot create invoices for this center."}, status=403)
                elif not user.centers.exists() and hasattr(user, 'center') and center != user.center:
                    return Response({"detail": "You cannot create invoices for this center."}, status=403)

        try:
            with transaction.atomic():
                invoice = serializer.save()
        except IntegrityError:
            if idempotency_key:
                existing = self.get_queryset().filter(idempotency_key=idempotency_key).first()
                if existing:
                    return Response(InvoiceSerializer(existing).data, status=status.HTTP_200_OK)
            raise

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

    def destroy(self, request, *args, **kwargs):
        invoice = self.get_object()
        if invoice.status != 'draft' or invoice.finalized_at:
            return Response(
                {'detail': 'Only unfinalized draft invoices can be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
    permission_classes = [RoleActionPermission]

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
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
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
        amount = serializer.validated_data.get('amount')
        if amount is None or amount <= 0:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'amount': 'Advance amount must be greater than zero.'})

        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
        
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
    permission_classes = [RoleActionPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        
        user = self.request.user
        perms = getattr(user.role, 'permissions', {}) or {}
        is_owner = getattr(user, 'is_superuser', False) or (user.role and user.role.name.lower() == 'owner')
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
