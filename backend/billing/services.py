import logging
import datetime
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


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
                return
            for _ in range(int(item.quantity)):
                existing_cm = ClientMembership.objects.filter(
                    client=invoice.client,
                    membership=membership,
                    is_active=True
                ).order_by('-expiry_date').first()

                if existing_cm and existing_cm.expiry_date >= datetime.date.today():
                    existing_cm.expiry_date = existing_cm.expiry_date + timedelta(days=membership.expiry_days)
                    existing_cm.save(update_fields=['expiry_date'])
                else:
                    ClientMembership.objects.create(
                        client=invoice.client,
                        membership=membership,
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
                    balance=vcard.value,
                    expiry_date=datetime.date.today() + timedelta(days=vcard.expiry_days)
                )

    except Exception as ex:
        logger.error(f"[Billing] Error provisioning perk: {ex}", exc_info=True)


def _deduct_package_service(invoice, item, active_packages_map):
    """When a package service is redeemed at Rs 0, decrement the client's remaining count."""
    if not invoice.client:
        return
    if not item.content_type or item.content_type.app_label != 'services':
        return
    if Decimal(str(item.unit_price)) != 0:
        return
    if not item.description or '🎁 [Redeem]' not in item.description:
        return
    
    try:
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
                    
                    if qty_to_deduct <= 0:
                        break
    except Exception as e:
        logger.error(f"[Billing] Error deducting package service: {e}", exc_info=True)


def finalize_invoice(invoice, appointment_id=None, request_data=None, skip_payment_deductions=False):
    """Run all post-save finalization tasks: stock deduction, perks, logs, wallet.
    This must only be called ONCE per invoice lifecycle transition (draft → paid/partial).

    Args:
        skip_payment_deductions: Set True when called from the /pay/ endpoint which
            handles its own advance/value-card deductions to prevent double-deducting.
    """
    from staff.models import ServiceLog
    from billing.models import AdvancePayment
    from inventory.models import StockTransaction

    # Pre-fetch active packages ONCE to avoid N+1 inside the loop
    active_packages_map = {}
    if invoice.client:
        from clients.models import ClientPackage
        # Use select_for_update to lock rows and prevent concurrent double-redemptions
        active_packages = ClientPackage.objects.select_for_update().filter(
            client=invoice.client, is_active=True, expiry_date__gte=datetime.date.today()
        )
        active_packages_map[invoice.client.id] = list(active_packages)

    for item in invoice.items.select_related('content_type', 'staff').prefetch_related('staff_members', 'content_object').all():

        # 1. Deduct Inventory Stock (floor at 0) + create audit StockTransaction
        try:
            if item.content_type and item.content_type.app_label == 'inventory':
                product = item.content_object
                if product and hasattr(product, 'current_stock'):
                    # Atomic update to avoid race condition on concurrent billing
                    locked_product = type(product).objects.select_for_update().get(pk=product.pk)
                    new_stock = max(0, locked_product.current_stock - int(item.quantity))
                    locked_product.current_stock = new_stock
                    locked_product.save(update_fields=['current_stock'])
                    # Audit trail
                    try:
                        StockTransaction.objects.create(
                            product=product,
                            center=invoice.center or (invoice.client.center if invoice.client else None),
                            transaction_type='SALE',
                            quantity_change=-int(item.quantity),
                            notes=f"Sold via Invoice #{invoice.id}",
                        )
                    except Exception as ste:
                        logger.warning(f"[Billing] Could not create StockTransaction: {ste}")
        except Exception as e:
            logger.error(f"[Billing] Error deducting stock: {e}", exc_info=True)

        # 2. Deduct Package Redeemed Services
        _deduct_package_service(invoice, item, active_packages_map)

        # 3. Auto-Provision Marketing Perks
        _provision_marketing_perks(invoice, item, request_data)

        # 4. Create Staff Service Logs
        try:
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
                total_amt = Decimal(str(invoice.total_amount or 0))
                if total_amt > 0:
                    # Sum all value-card payments for this invoice
                    vc_paid = Decimal(str(
                        invoice.payments.filter(
                            payment_method__icontains='value card'
                        ).aggregate(s=Sum('amount'))['s'] or 0
                    ))
                    real_paid = max(0, total_amt - vc_paid)
                    invoice._vc_incentive_ratio = real_paid / total_amt
                else:
                    invoice._vc_incentive_ratio = 1.0

            effective_price = Decimal(str(item.total_price)) * invoice._vc_incentive_ratio
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
                    time=invoice.created_at.time() if invoice.created_at else timezone.now().time()
                )
        except Exception as e:
            logger.error(f"[Billing] Error creating ServiceLog: {e}", exc_info=True)
            continue


    # 5. Auto-complete Appointment
    try:
        final_appointment_id = appointment_id or invoice.appointment_id
        if final_appointment_id and invoice.status in ('paid', 'partial'):
            from appointments.models import Appointment
            Appointment.objects.filter(id=final_appointment_id).update(status='Completed')
    except Exception as e:
        logger.error(f"[Billing] Error auto-completing appointment: {e}", exc_info=True)

    # 6. Handle Advance/Wallet deductions and Value Card deductions.
    # GUARD: skip_payment_deductions=True when called from the /pay/ endpoint, which
    # handles its own deductions. Prevents double-deducting wallet/value cards.
    if not skip_payment_deductions:
        try:
            for payment in invoice.payments.all():
                pm = payment.payment_method.lower()

                # Cashback Wallet — create a negative CashbackTransaction row (debit from balance)
                if pm == 'cashback wallet':
                    from clients.models import Client
                    locked_client = Client.objects.select_for_update().get(id=invoice.client.id)
                    cashback_bal = locked_client.cashback_balance

                    if Decimal(str(payment.amount)) > cashback_bal:
                        logger.warning(
                            f"[Billing] Invoice #{invoice.id}: cashback deduction {payment.amount} "
                            f"exceeds balance {cashback_bal}. Capping deduction."
                        )
                        deduct_amount = Decimal(str(max(0, cashback_bal)))
                    else:
                        deduct_amount = payment.amount

                    if deduct_amount > 0:
                        from billing.models import CashbackTransaction
                        CashbackTransaction.objects.create(
                            client=invoice.client,
                            invoice=invoice,
                            amount=-deduct_amount,
                            notes=f"Used for Invoice #{invoice.id}"
                        )

                # Advance / Wallet — create a negative AdvancePayment row (debit from balance)
                elif 'advance' in pm or ('wallet' in pm and pm != 'cashback wallet'):
                    # Guard: only deduct if client actually has sufficient balance
                    from clients.models import Client
                    locked_client = Client.objects.select_for_update().get(id=invoice.client.id)
                    advance_bal = locked_client.advance_balance

                    if Decimal(str(payment.amount)) > advance_bal:
                        logger.warning(
                            f"[Billing] Invoice #{invoice.id}: advance deduction {payment.amount} "
                            f"exceeds balance {advance_bal}. Capping deduction."
                        )
                        deduct_amount = Decimal(str(max(0, advance_bal)))
                    else:
                        deduct_amount = payment.amount

                    if deduct_amount > 0:
                        AdvancePayment.objects.create(
                            client=invoice.client,
                            invoice=invoice,
                            amount=-deduct_amount,
                            notes=f"Used for Invoice #{invoice.id}"
                        )

                # Value Card — use the stored value_card_id (not fragile string parsing)
                if 'value card' in pm and payment.value_card_id:
                    try:
                        from clients.models import ClientValueCard
                        with transaction.atomic():
                            client_vc = ClientValueCard.objects.select_for_update().get(id=payment.value_card_id)
                            if payment.amount > client_vc.balance:
                                logger.warning(
                                    f"[Billing] Invoice #{invoice.id}: value card deduction {payment.amount} "
                                    f"exceeds balance {client_vc.balance}. Capping deduction."
                                )
                                payment.amount = client_vc.balance
                                payment.save()
                                
                            client_vc.balance = max(Decimal('0'), client_vc.balance - payment.amount)
                            if client_vc.balance <= 0:
                                client_vc.is_active = False
                            client_vc.save()
                    except Exception as ex:
                        logger.error(f"[Billing] Error deducting Value Card id={payment.value_card_id}: {ex}", exc_info=True)

        except Exception as e:
            logger.error(f"[Billing] Error handling payment deduction: {e}", exc_info=True)

    # 7. Apply Promotion logic (Usage tracking & Cashback)
    if request_data:
        # Validate Membership Discount to prevent spoofing
        if request_data.get('membership_id') and invoice.client:
            membership_id = request_data.get('membership_id')
            try:
                from clients.models import ClientMembership
                cm = ClientMembership.objects.filter(
                    id=membership_id, client=invoice.client, is_active=True
                ).first()
                if cm and cm.membership.discount_percent:
                    expected_discount = Decimal(str(invoice.subtotal)) * Decimal(str(cm.membership.discount_percent)) / 100
                    if Decimal(str(invoice.discount)) > expected_discount + 1:  # Allow 1 unit rounding difference
                        logger.warning(f"[Security] Invoice #{invoice.id} claimed discount {invoice.discount} exceeds membership allowed {expected_discount}. Reverting.")
                        invoice.discount = Decimal(str(expected_discount))
                        invoice.total_amount = invoice.subtotal - invoice.discount + invoice.cgst + invoice.sgst
                        invoice.save(update_fields=['discount', 'total_amount'])
            except Exception as e:
                logger.error(f"[Billing] Error validating membership discount: {e}", exc_info=True)

        if request_data.get('promo_id'):
            try:
                from marketing.promotions import apply_promotion
                apply_promotion(invoice, request_data.get('promo_id'))
            except Exception as e:
                logger.error(f"[Billing] Error processing promotion logic: {e}", exc_info=True)

    logger.info(f"[Billing] finalize_invoice completed for invoice #{invoice.id}")

