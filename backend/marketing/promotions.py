"""Server-side promotion calculations and promotion-ledger writes."""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from rest_framework.exceptions import ValidationError


MONEY_QUANTUM = Decimal('0.01')


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@transaction.atomic
def apply_promotion(invoice, promotion_id, *, record_usage=True):
    """Validate and calculate a promotion for an invoice.

    ``record_usage=False`` is used by the draft preview endpoint. Usage and
    cashback are ledger entries and are only committed when a bill is paid or
    becomes partial. The promotion row is locked so per-client limits cannot
    be bypassed by two concurrent checkouts.
    """
    from .models import Promotion, PromotionUsage

    try:
        promo = Promotion.objects.select_for_update().get(
            id=promotion_id, is_active=True
        )
    except (Promotion.DoesNotExist, TypeError, ValueError):
        return Decimal('0.00'), 'Promotion not found or inactive'

    today = invoice.created_at.date() if invoice.created_at else __import__('datetime').date.today()
    if not (promo.start_date <= today <= promo.end_date):
        return Decimal('0.00'), 'Promotion is not valid for the invoice date'

    if promo.level == 'Center' and promo.center_id != invoice.center_id:
        return Decimal('0.00'), 'Promotion is not valid for this center'

    if promo.members_only:
        if not invoice.client_id:
            return Decimal('0.00'), 'This promotion is available to members only'
        from clients.models import ClientMembership
        if not ClientMembership.objects.filter(
            client_id=invoice.client_id,
            is_active=True,
            expiry_date__gte=today,
        ).exists():
            return Decimal('0.00'), 'Client does not have an active membership'

    existing_usage = PromotionUsage.objects.filter(
        promotion=promo, invoice_id=invoice.id
    ).first() if invoice.pk else None
    if existing_usage:
        # Idempotent retry: do not issue a second cashback or usage row.
        return _money(invoice.discount), None

    if promo.max_usage_per_client and invoice.client_id:
        usage_count = PromotionUsage.objects.filter(
            promotion=promo, client_id=invoice.client_id
        ).count()
        if usage_count >= promo.max_usage_per_client:
            return Decimal('0.00'), 'Usage limit reached for this client'

    before = _money(invoice.subtotal)
    discount = Decimal('0.00')

    if promo.promo_type == 'Discount':
        if promo.discount_type == 'Percentage':
            discount = before * _money(promo.discount_value) / Decimal('100')
        elif promo.discount_type == 'Flat':
            discount = _money(promo.discount_value)
    elif promo.promo_type in ('FlatPrice', 'Trigger'):
        # These promotions are applied at line level by the POS. We still
        # record their usage once the invoice is finalized.
        discount = Decimal('0.00')
    elif promo.promo_type == 'Cashback':
        if record_usage and invoice.client_id:
            minimum = _money((promo.config or {}).get('cashback_min_bill'))
            cashback_percent = _money((promo.config or {}).get('cashback_discount'))
            if before >= minimum and cashback_percent > 0:
                cashback_value = _money(before * cashback_percent / Decimal('100'))
                from billing.models import CashbackTransaction
                CashbackTransaction.objects.create(
                    client_id=invoice.client_id,
                    invoice=invoice,
                    amount=cashback_value,
                    notes=f'Cashback from Promotion: {promo.name}',
                )

    discount = min(_money(discount), before)
    if record_usage:
        center_id = invoice.center_id or getattr(invoice.client, 'center_id', None)
        if not center_id:
            raise ValidationError('A center is required to record promotion usage.')
        PromotionUsage.objects.create(
            promotion=promo,
            invoice=invoice,
            center_id=center_id,
            client_id=invoice.client_id,
            bill_amount_before=before,
            bill_amount_after=_money(before - discount),
            revenue_generated=_money(before - discount),
        )

    return discount, None
