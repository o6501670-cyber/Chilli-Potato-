
with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<div class="config-form-grid-large" style="display:flex; flex-direction:column; gap:16px; width:100%;">', '<div class="config-form-grid-large">')
text += '\n<!-- force reload html -->'

with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
    f.write(text)

with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()
css += '\n/* force reload css */\n'
with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Forced reload.')

