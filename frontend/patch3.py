
with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

css = css.replace(
'''/* SUBHEADER */
.billing-subheader-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 0 20px 0;
  padding: 14px 24px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}''',
'''/* SUBHEADER */
.billing-subheader-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 0 0 16px 0;
  padding: 10px 16px;
  background: #2d3748;
  border-radius: 8px;
}''')

with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Subheader updated')

