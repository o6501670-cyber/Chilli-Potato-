
with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update Accordion headers to match the image's dark teal/blue headers
css = css.replace(
'''/* ACCORDIONS -> Modernized cleanly */
.accordion-header {
  background: #f8fafc; color: #334155; padding: 14px 16px; font-size: 14px;
  font-weight: 700; border-radius: 10px; margin-top: 16px; cursor: pointer;
  border: 1px solid #e2e8f0; transition: all 0.2s;
}
.accordion-header:hover { background: #f1f5f9; border-color: #cbd5e1; }
.accordion-body { padding: 12px 16px; font-size: 13px; color: #475569; }''',
'''/* ACCORDIONS -> Match Image Style */
.accordion-header {
  background: #066b8b; color: #ffffff; padding: 8px 12px; font-size: 14px;
  font-weight: 600; margin-top: 16px; text-align: center;
  border: 1px solid #066b8b;
}
.accordion-body { 
  padding: 8px; font-size: 12px; color: #334155; 
  border: 1px solid #cbd5e1; border-top: none;
}
.accordion-body .data-table { margin: 0; width: 100%; }
.accordion-body .data-table td { padding: 8px; font-size: 12px; border-bottom: 1px solid #f1f5f9; }
''')

# 2. Update Cart buttons to match solid colors in the image
css = css.replace(
'''.btn-discard {
  flex: 1; background: #ffffff; color: #ef4444; border: 1px solid #fecaca;
  padding: 14px; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 13px; transition: all 0.2s;
}
.btn-discard:hover { background: #fef2f2; border-color: #ef4444; }
.btn-save {
  flex: 1; background: #ffffff; color: #f59e0b; border: 1px solid #fde68a;
  padding: 14px; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 13px; transition: all 0.2s;
}
.btn-save:hover { background: #fffbeb; border-color: #f59e0b; }
.btn-finalise {
  flex: 2; background: #10b981; color: #ffffff; border: none; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);
  padding: 14px; border-radius: 10px; cursor: pointer; font-weight: 800; font-size: 14px; transition: all 0.2s; letter-spacing: 0.5px;
}
.btn-finalise:hover { background: #059669; transform: translateY(-1px); box-shadow: 0 6px 8px rgba(16, 185, 129, 0.3); }''',
'''.btn-discard {
  flex: 1; background: #ef4444; color: #ffffff; border: none;
  padding: 12px; cursor: pointer; font-weight: 600; font-size: 14px;
}
.btn-discard:hover { opacity: 0.9; }
.btn-save {
  flex: 1; background: #d97706; color: #ffffff; border: none;
  padding: 12px; cursor: pointer; font-weight: 600; font-size: 14px;
}
.btn-save:hover { opacity: 0.9; }
.btn-finalise {
  flex: 2; background: #0f766e; color: #ffffff; border: none;
  padding: 12px; cursor: pointer; font-weight: 600; font-size: 14px;
}
.btn-finalise:hover { opacity: 0.9; }''')

with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)

print('CSS Updated')

