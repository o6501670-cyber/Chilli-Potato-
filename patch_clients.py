
with open('backend/clients/models.py', 'r', encoding='utf-8') as f:
    text = f.read()

prop = '''
    @property
    def advance_balance(self):
        from django.db.models import Sum
        from billing.models import AdvancePayment, Payment
        
        total_adv = AdvancePayment.objects.filter(client=self).aggregate(total=Sum('amount'))['total'] or 0
        
        # Payment model payment_method is string.
        # Check payments where method is 'Advance' or 'Wallet'
        total_used = Payment.objects.filter(
            invoice__client=self,
            payment_method__icontains='Advance'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_wallet = Payment.objects.filter(
            invoice__client=self,
            payment_method__icontains='Wallet'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(total_adv) - float(total_used) - float(total_wallet)

    def __str__(self):'''

text = text.replace('    def __str__(self):', prop, 1)

with open('backend/clients/models.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('backend/clients/serializers.py', 'r', encoding='utf-8') as f:
    text2 = f.read()

text2 = text2.replace(
'''    active_value_cards = serializers.SerializerMethodField()''',
'''    active_value_cards = serializers.SerializerMethodField()
    advance_balance = serializers.FloatField(read_only=True)'''
)
with open('backend/clients/serializers.py', 'w', encoding='utf-8') as f:
    f.write(text2)

print('Models and serializers patched.')

