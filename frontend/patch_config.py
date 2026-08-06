
missing_css = '''
/* Configuration Forms (Restored) */
.config-container {
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  overflow-y: auto;
}
.config-title {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  margin-bottom: 16px;
  text-align: center;
}
.config-form-grid {
  display: grid;
  grid-template-columns: 160px 1fr auto;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  margin-bottom: 16px;
  width: 100%;
}
.config-form-grid label {
  text-align: right;
  color: #475569;
  font-weight: 600;
}
.config-form-grid select, .config-form-grid input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #0f172a;
  outline: none;
  font-size: 13px;
}
.config-form-grid-large {
  display: grid;
  grid-template-columns: 140px 1fr auto;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  margin-bottom: 20px;
  width: 100%;
}
.config-form-grid-large label {
  text-align: right;
  color: #475569;
  font-weight: 600;
}
.config-form-grid-large select, .config-form-grid-large input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #0f172a;
  outline: none;
  font-size: 13px;
}
.input-grey-center {
  background: #f1f5f9 !important;
  text-align: center;
  color: #0f172a !important;
  border: 1px solid #e2e8f0 !important;
}
.btn-green-teal {
  background: #0f766e;
  color: #ffffff;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  width: 100%;
  transition: opacity 0.2s;
}
.btn-green-teal:hover { opacity: 0.9; }
.btn-gray {
  background: #94a3b8;
  color: #ffffff;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-gray:hover { opacity: 0.9; }
.btn-link {
  background: transparent;
  color: #0ea5e9;
  border: none;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  text-decoration: underline;
}
.final-price-row {
  margin: 16px 0;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  text-align: center;
}
.final-price-row span {
  color: #0ea5e9;
  font-weight: 800;
}
.accordion-body .data-table th { 
  padding: 4px; font-size: 10px; border-bottom: 1px solid #e2e8f0; 
}
.accordion-body .data-table td { 
  padding: 4px; font-size: 11px; border-bottom: 1px solid #f1f5f9; 
}
'''

with open('src/app/billing/billing.css', 'a', encoding='utf-8') as f:
    f.write(missing_css)

print('Configuration styles appended.')

