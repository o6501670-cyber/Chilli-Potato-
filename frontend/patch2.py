
with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

css = css.replace(
'''.btn-green-teal {
  background: #0f172a; color: #ffffff;
  border: none; padding: 12px 20px;
  border-radius: 8px; font-weight: 700;
  font-size: 14px; cursor: pointer; width: 100%; transition: opacity 0.2s;
}''',
'''.btn-green-teal {
  background: #0f766e; color: #ffffff;
  border: none; padding: 12px 20px;
  border-radius: 0; font-weight: 600;
  font-size: 14px; cursor: pointer; width: 100%; transition: opacity 0.2s;
}''')

with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)

with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('SAVE (ON HOLD)', 'SAVE')
html = html.replace('CHECKOUT', 'Finalise')

# Also, the image doesn't use rounded corners for the layout panels as much, but user said 'with our ui existing'
# So I'll keep the rounded corners on the main panels.

with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Updated labels and ADD TO INVOICE button')

