import re
html = open('frontend/src/app/marketing/marketing.html', 'r', encoding='utf-8').read()

html = re.sub(r'(<input\s+type="date")(.*?ngModel="(?:newPromotion|editItemData)\.(?:start_date|end_date)".*?>)', r'\1 [min]="minDate"\2', html)
html = re.sub(r'(<input\s+type="date")(.*?ngModel="(?:newPromotion|editItemData)\.config\.cashback_specific_date".*?>)', r'\1 [min]="minDate"\2', html)

open('frontend/src/app/marketing/marketing.html', 'w', encoding='utf-8').write(html)
