import logging
import datetime
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


def _provision_marketing_perks(invoice, item, request_data=None):
    """Auto-provision Memberships, Packages, and Value Cards when purchased via billing."""
    if not invoice.client:
        return
    if not item.content_type or item.content_type.app_label != 'marketing':
        return
    try:
        from clients.models import ClientMembership, ClientPackage, ClientValueCard
        m_model = item.content_type.model

        if m_model == 'membership':
            membership = item.content_object
            if not membership:
                raise ValidationError('Membership for invoice item no longer exists.')
            # Keep one immutable entitlement per purchase so a refund can
            # reverse exactly the entitlement created by this invoice.
            for _ in range(int(item.quantity)):
                ClientMembership.objects.create(
                    client=invoice.client,
                    membership=membership,
                    source_invoice=invoice,
                    expiry_date=datetime.date.today() + timedelta(days=membership.expiry_days)
                )

        elif m_model == 'package':
            package = item.content_object
            services_rem = {}
            validity_days = 90  # default for custom packages

            if package:
                validity_days = package.validity_days
                for svc in (package.services_json or []):
                    svc_id = str(svc.get('id', ''))
                    if svc_id:
                        services_rem[svc_id] = int(svc.get('pkgQty', 1)) * int(item.quantity)
            else:
                # Custom package: extract services from request_data
                if request_data:
                    items_data = request_data.get('items', [])
                    for idata in items_data:
                        if idata.get('description') == item.description and idata.get('custom_package_services'):
                            # Aggregate correctly for duplicate custom package services
                            for svc in idata.get('custom_package_services', []):
                                svc_id = str(svc.get('id', ''))
                                if svc_id:
                                    services_rem[svc_id] = services_rem.get(svc_id, 0) + (int(svc.get('pkgQty', 1)) * int(item.quantity))
                            break
            
            if services_rem:
                expiry = invoice.created_at.date() + timedelta(days=validity_days)
                ClientPackage.objects.create(
                    client=invoice.client,
                    package=package,
                    source_invoice=invoice,
                    services_remaining=services_rem,
                    expiry_date=expiry
                )

        elif m_model == 'valuecard':
            vcard = item.content_object
            if not vcard:
                return
            for _ in range(int(item.quantity)):
                ClientValueCard.objects.create(
                    client=invoice.client,
                    value_card=vcard,
                    source_invoice=invoice,
                    balance=vcard.value,
                    expiry_date=datetime.date.today() + timedelta(days=vcard.expiry_days)
                )

    except Exception:
        logger.exception('[Billing] Error provisioning perk')
        raise


def _deduct_package_service(invoice, item, active_packages_map):
    """When a package service is redeemed at Rs 0, decrement the client's remaining count."""
    if not invoice.client:
        return
    if not item.content_type or item.content_type.app_label != 'services':
        return
    if float(item.unit_price) != 0:
        return
    if not item.description or '🎁 [Redeem]' not in item.description:
        return
    
    try:
        from clients.models import PackageRedemption
        svc_id_str = str(item.content_object.id) if item.content_object else ''
        if not svc_id_str:
            return
            
        client_id = invoice.client.id
        if client_id not in active_packages_map:
            return
            
        active_packages = active_packages_map[client_id]
        
        qty_to_deduct = int(item.quantity)
        for cp in active_packages:
            if svc_id_str in cp.services_remaining:
                rem = cp.services_remaining[svc_id_str]
                if rem > 0:
                    deduct = min(rem, qty_to_deduct)
                    cp.services_remaining[svc_id_str] -= deduct
                    qty_to_deduct -= deduct
                    
                    if all(v <= 0 for v in cp.services_remaining.values()):
                        cp.is_active = False
                    cp.save()
                    PackageRedemption.objects.create(
                        invoice=invoice,
                        package=cp,
                        service_id=int(svc_id_str),
                        quantity=deduct,
                    )
                    
                    if qty_to_deduct <= 0:
                        break
        if qty_to_deduct > 0:
            raise ValidationError(
                f'Insufficient package balance for service {svc_id_str}; '
                f'{qty_to_deduct} redemption(s) could not be allocated.'
            )
    except Exception:
        logger.exception('[Billing] Error deducting package service')
        raise


@transaction.atomic
def finalize_invoice(invoice, appointment_id=None, request_data=None, skip_payment_deductions=False):
    """Run all post-save finalization tasks exactly once.

    The caller may safely retry a payment request: the invoice row is locked
    and ``finalized_at`` makes an already-completed transition a no-op. Any
    failure bubbles out so the surrounding transaction rolls back the invoice,
    stock, wallets, perks and audit rows together.

    ``skip_payment_deductions`` is used by the payment endpoint because it
    debits the selected tender while holding the invoice lock.
    """
    invoice = type(invoice).objects.select_for_update().get(pk=invoice.pk)
    if invoice.finalized_at:
        return invoice
    if invoice.status not in ('paid', 'partial'):
        raise ValidationError('Only paid or partial invoices can be finalized.')
    from staff.models import ServiceLog
    from billing.models import AdvancePayment
    from inventory.models import Product, StockTransaction

    # Preflight inventory before creating any logs/perks. The old code floored
    # stock at zero, allowing a sale to succeed while silently selling more than
    # was available.
    inventory_items = invoice.items.select_related('content_type').all()
    for inventory_item in inventory_items:
        if not inventory_item.content_type or inventory_item.content_type.app_label != 'inventory':
            continue
        product = Product.objects.select_for_update().filter(pk=inventory_item.object_id).first()
        if not product:
            raise ValidationError(f'Product for invoice item {inventory_item.id} no longer exists.')
        if int(inventory_item.quantity) > product.current_stock:
            raise ValidationError(
                f'Insufficient stock for {product.name}. Available: {product.current_stock}, '
                f'requested: {inventory_item.quantity}.'
            )

    # Pre-fetch active packages ONCE to avoid N+1 inside the loop
    active_packages_map = {}
    if invoice.client:
        from clients.models import ClientPackage
        # Use select_for_update to lock rows and prevent concurrent double-redemptions
        active_packages = ClientPackage.objects.select_for_update().filter(
            client=invoice.client, is_active=True, expiry_date__gte=datetime.date.today()
        )
        active_packages_map[invoice.client.id] = list(active_packages)

    for item in invoice.items.select_related('content_type', 'staff').prefetch_related('staff_members').all():

        # 1. Deduct Inventory Stock and create the immutable stock audit row.
        if item.content_type and item.content_type.app_label == 'inventory':
            product = item.content_object
            if not product:
                raise ValidationError(f'Product for invoice item {item.id} no longer exists.')
            Product.objects.filter(pk=product.pk).update(
                current_stock=F('current_stock') - int(item.quantity)
            )
            StockTransaction.objects.create(
                product=product,
                center=invoice.center or (invoice.client.center if invoice.client else None),
                transaction_type='SALE',
                quantity_change=-int(item.quantity),
                notes=f"Sold via Invoice #{invoice.id}",
            )

        # 2. Deduct Package Redeemed Services
        _deduct_package_service(invoice, item, active_packages_map)

        # 3. Auto-Provision Marketing Perks
        _provision_marketing_perks(invoice, item, request_data)

        # 4. Create Staff Service Logs
        staff_list = list(item.staff_members.all())
        if item.staff and item.staff not in staff_list:
            staff_list.append(item.staff)

        if not staff_list:
            continue

        # ---- VALUE CARD INCENTIVE DEDUCTION ----
        # Staff earn commission only on the real-money proportion of the invoice.
        # If a customer paid ₹10,000 cash + ₹5,000 value card on a ₹15,000 bill:
        #   real_paid_ratio = 10,000 / 15,000 = 0.6667
        #   effective_price = item_price × 0.6667
        #
        # Compute the ratio once per invoice (cached per call).
        if not hasattr(invoice, '_vc_incentive_ratio'):
            total_amt = float(invoice.total_amount or 0)
            if total_amt > 0:
                # Sum all value-card payments for this invoice
                vc_paid = float(
                    invoice.payments.filter(
                        payment_method__icontains='value card'
                    ).aggregate(s=Sum('amount'))['s'] or 0
                )
                real_paid = max(0, total_amt - vc_paid)
                invoice._vc_incentive_ratio = real_paid / total_amt
            else:
                invoice._vc_incentive_ratio = 1.0

        effective_price = float(item.total_price) * invoice._vc_incentive_ratio
        split_price = effective_price / len(staff_list)

        for member in staff_list:
            center = (
                invoice.center
                or (invoice.client.center if invoice.client and invoice.client.center else None)
                or member.center
            )
            service_name = item.description or (
                getattr(item.content_object, 'name', None) or str(item.content_object)
            )
            ct = item.content_type
            service_type = 'Service'
            if ct:
                if ct.app_label == 'inventory':
                    service_type = 'Product'
                elif ct.app_label == 'marketing':
                    m = ct.model or ''
                    if 'membership' in m:
                        service_type = 'Membership'
                    elif 'package' in m:
                        service_type = 'Package'
                    else:
                        service_type = 'Product'

            ServiceLog.objects.create(
                invoice=invoice,
                staff=member,
                center=center,
                client_name=invoice.client.full_name if invoice.client else '',
                service_name=service_name,
                service_type=service_type,
                price=split_price,
                # Use the invoice's actual date/time — not today() —
                # so backdated or corrected bills land in the right payroll period.
                date=invoice.created_at.date() if invoice.created_at else datetime.date.today(),
                time=invoice.created_at.time() if invoice.created_at else datetime.datetime.now().time()
            )


    # 5. Auto-complete Appointment
    final_appointment_id = appointment_id or invoice.appointment_id
    if final_appointment_id and invoice.status in ('paid', 'partial'):
        from appointments.models import Appointment
        updated = Appointment.objects.filter(id=final_appointment_id).update(status='Completed')
        if not updated:
            raise ValidationError('The linked appointment no longer exists.')

    # 6. Handle Advance/Wallet deductions and Value Card deductions.
    # The payment endpoint passes skip_payment_deductions=True because it has
    # already performed these locked operations.
    if not skip_payment_deductions:
        from clients.models import Client, ClientValueCard
        from billing.models import CashbackTransaction
        for payment in invoice.payments.all():
            pm = payment.payment_method.lower()
            if pm == 'cashback wallet':
                if not invoice.client_id:
                    raise ValidationError('A client is required for cashback payments.')
                locked_client = Client.objects.select_for_update().get(pk=invoice.client_id)
                balance = CashbackTransaction.objects.filter(client_id=locked_client.id).aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                if balance < payment.amount:
                    raise ValidationError(
                        f'Insufficient cashback balance. Available: ₹{balance:.2f}.'
                    )
                CashbackTransaction.objects.create(
                    client=locked_client,
                    invoice=invoice,
                    amount=-payment.amount,
                    notes=f'Used for Invoice #{invoice.id}',
                )
            elif 'advance' in pm or ('wallet' in pm and pm != 'cashback wallet'):
                if not invoice.client_id:
                    raise ValidationError('A client is required for advance payments.')
                locked_client = Client.objects.select_for_update().get(pk=invoice.client_id)
                balance = AdvancePayment.objects.filter(client_id=locked_client.id).aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0')
                if balance < payment.amount:
                    raise ValidationError(
                        f'Insufficient advance balance. Available: ₹{balance:.2f}.'
                    )
                AdvancePayment.objects.create(
                    client=locked_client,
                    invoice=invoice,
                    amount=-payment.amount,
                    notes=f'Used for Invoice #{invoice.id}',
                )
            elif 'value card' in pm:
                if not invoice.client_id or not payment.value_card_id:
                    raise ValidationError('A client and value card are required for value-card payments.')
                try:
                    client_vc = ClientValueCard.objects.select_for_update().get(
                        pk=payment.value_card_id,
                        client_id=invoice.client_id,
                        is_active=True,
                        expiry_date__gte=datetime.date.today(),
                    )
                except ClientValueCard.DoesNotExist:
                    raise ValidationError('Value card not found, expired, or not owned by this client.')
                if client_vc.balance < payment.amount:
                    raise ValidationError(
                        f'Insufficient value-card balance. Available: ₹{client_vc.balance:.2f}.'
                    )
                client_vc.balance -= payment.amount
                if client_vc.balance <= 0:
                    client_vc.balance = Decimal('0')
                    client_vc.is_active = False
                client_vc.save(update_fields=['balance', 'is_active'])

    # 7. Validate and record promotion/membership ledgers only after the
    # invoice has reached paid/partial status.
    if request_data:
        membership_id = request_data.get('membership_id') or invoice.membership_id
        promotion_id = request_data.get('promo_id') or invoice.promotion_id
        if membership_id and invoice.client_id:
            from clients.models import ClientMembership
            cm = ClientMembership.objects.select_for_update().filter(
                id=membership_id,
                client_id=invoice.client_id,
                is_active=True,
                expiry_date__gte=datetime.date.today(),
            ).select_related('membership').first()
            if not cm:
                raise ValidationError('Membership is not active or does not belong to this client.')
            allowed_discount = _money(
                Decimal(str(invoice.subtotal)) * Decimal(str(cm.membership.discount_percent or 0)) / Decimal('100')
            )
            if invoice.discount > allowed_discount + Decimal('0.01'):
                raise ValidationError('Invoice discount exceeds the selected membership benefit.')

        if promotion_id:
            from marketing.promotions import apply_promotion
            discount, error = apply_promotion(
                invoice, promotion_id, record_usage=True
            )
            if error:
                raise ValidationError(error)
            if discount > 0 and abs(invoice.discount - discount) > Decimal('0.01'):
                raise ValidationError('Invoice discount does not match the promotion rules.')

    invoice.finalized_at = timezone.now()
    invoice.save(update_fields=['finalized_at', 'updated_at'])
    logger.info(f"[Billing] finalize_invoice completed for invoice #{invoice.id}")
    return invoice

