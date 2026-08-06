def apply_promotion(invoice, promotion_id):
    """Apply a promotion to an invoice. Returns (discount_amount, error_message)."""
    try:
        from .models import Promotion, PromotionUsage
        promo = Promotion.objects.get(id=promotion_id, is_active=True)
    except Promotion.DoesNotExist:
        return 0, "Promotion not found or inactive"

    import datetime
    today = datetime.date.today()
    if not (promo.start_date <= today <= promo.end_date):
        return 0, "Promotion has expired"

    # Per-client usage limit
    if promo.max_usage_per_client and invoice.client:
        usage_count = PromotionUsage.objects.filter(
            promotion=promo, client=invoice.client
        ).count()
        if usage_count >= promo.max_usage_per_client:
            return 0, "Usage limit reached for this client"

    before = float(invoice.subtotal)
    discount = 0

    if promo.promo_type == 'Discount':
        if promo.discount_type == 'Percentage':
            discount = before * float(promo.discount_value) / 100
        else:
            discount = float(promo.discount_value)
    elif promo.promo_type == 'FlatPrice':
        # Handled per-item — skip invoice level
        pass
    elif promo.promo_type == 'Trigger':
        # Trigger deal mathematically deducted by the POS frontend
        pass
    elif promo.promo_type == 'Cashback':
        # Check minimum bill requirement
        min_bill = float(promo.config.get('cashback_min_bill') or 0)
        if before >= min_bill:
            # Cashback gives money to the client's wallet for future use
            if invoice.client:
                cashback_percent = float(promo.config.get('cashback_discount') or 0)
                cashback_val = before * cashback_percent / 100
                
                if cashback_val > 0:
                    try:
                        from billing.models import CashbackTransaction
                        CashbackTransaction.objects.create(
                            client=invoice.client,
                            invoice=invoice,
                            amount=cashback_val,
                            notes=f"Cashback from Promotion: {promo.name}"
                        )
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error applying cashback: {e}")
        # Cashback does not discount the current bill
        discount = 0

    discount = min(discount, before)  # Never discount more than invoice total
    after = before - discount

    # Log usage
    PromotionUsage.objects.create(
        promotion=promo, center=invoice.center, client=invoice.client,
        bill_amount_before=before, bill_amount_after=after,
        revenue_generated=after
    )

    return round(discount, 2), None
