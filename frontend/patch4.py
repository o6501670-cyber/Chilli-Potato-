
with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

css = css.replace(
'''/* CLIENT SEARCH BOX */
.client-search-box { display: flex; gap: 10px; margin-bottom: 20px; }
.client-search-box input {
  flex: 1; padding: 12px 16px; border-radius: 10px;
  border: 1px solid #cbd5e1; background: #f8fafc; font-size: 14px;
  outline: none; color: #0f172a; transition: all 0.2s;
}
.client-search-box input:focus { border-color: #38bdf8; background: #ffffff; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1); }
.btn-add-client {
  width: 44px; height: 44px; border-radius: 10px; border: 1px solid #cbd5e1;
  background: #ffffff; font-size: 18px; cursor: pointer; color: #64748b;
  transition: all 0.2s ease; display: flex; align-items: center; justify-content: center;
}''',
'''/* CLIENT SEARCH BOX */
.client-search-box { display: flex; gap: 8px; margin-bottom: 16px; }
.client-search-box input {
  flex: 1; padding: 8px 12px; border-radius: 8px;
  border: 1px solid #cbd5e1; background: #f8fafc; font-size: 13px;
  outline: none; color: #0f172a; transition: all 0.2s;
}
.client-search-box input:focus { border-color: #38bdf8; background: #ffffff; box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.1); }
.btn-add-client {
  width: 36px; height: 36px; border-radius: 8px; border: 1px solid #cbd5e1;
  background: #ffffff; font-size: 16px; cursor: pointer; color: #64748b;
  transition: all 0.2s ease; display: flex; align-items: center; justify-content: center;
}''')

css = css.replace(
'''.client-name-large { display: flex; gap: 12px; margin-bottom: 12px; }
.client-name-large input {
  border: none; border-bottom: 2px solid #e2e8f0; padding: 8px 4px;
  font-size: 20px; font-weight: 800; color: #0f172a; width: 100%;
  transition: border-color 0.2s; background: transparent;
}''',
'''.client-name-large { display: flex; gap: 8px; margin-bottom: 8px; }
.client-name-large input {
  border: none; border-bottom: 2px solid #e2e8f0; padding: 6px 4px;
  font-size: 18px; font-weight: 700; color: #0f172a; width: 100%;
  transition: border-color 0.2s; background: transparent;
}''')

css = css.replace(
'''.client-phone-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.client-phone-row input {
  border: none; border-bottom: 2px solid #e2e8f0; font-size: 15px; width: 60%;
  padding: 6px 4px; color: #475569; transition: border-color 0.2s; background: transparent;
}''',
'''.client-phone-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.client-phone-row input {
  border: none; border-bottom: 2px solid #e2e8f0; font-size: 14px; width: 60%;
  padding: 4px 4px; color: #475569; transition: border-color 0.2s; background: transparent;
}''')

css = css.replace(
'''.client-input-group { margin-bottom: 12px; }
.client-input-group input, .client-input-group textarea {
  width: 100%; padding: 12px 16px; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 10px; font-size: 14px; color: #0f172a; transition: all 0.2s; font-family: inherit;
}''',
'''.client-input-group { margin-bottom: 8px; }
.client-input-group input, .client-input-group textarea {
  width: 100%; padding: 8px 12px; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; font-size: 13px; color: #0f172a; transition: all 0.2s; font-family: inherit;
}''')

css = css.replace(
'''.btn-save-client {
  width: 100%; padding: 14px; background: #0f172a; color: white;
  border-radius: 10px; border: none; font-weight: 700; font-size: 14px;
  cursor: pointer; transition: all 0.2s; margin-top: 10px;
}''',
'''.btn-save-client {
  width: 100%; padding: 10px; background: #0f172a; color: white;
  border-radius: 8px; border: none; font-weight: 600; font-size: 13px;
  cursor: pointer; transition: all 0.2s; margin-top: 8px;
}''')

with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Client section compact styles updated')

