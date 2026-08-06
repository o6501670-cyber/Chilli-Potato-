
with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()
import re
print('panels:')
for m in re.findall(r'<div class="panel-card[^"]*">', text):
    print(m)
print('new invoice views:')
print(re.findall(r'<div class="billing-body new-invoice-view" \w+', text))

