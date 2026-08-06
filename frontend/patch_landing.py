
with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

landing_css = '''
/* LANDING VIEW */
.landing-view {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  width: 100%;
  gap: 24px;
  padding: 24px 0;
  height: calc(100vh - 160px);
}
.landing-col {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
  padding: 20px;
  border: 1px solid #e2e8f0;
  height: 100%;
}
.landing-header {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  padding-bottom: 12px;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.landing-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.landing-item {
  display: flex;
  flex-direction: column;
  padding: 14px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  color: #334155;
  transition: all 0.2s ease;
  background: #f8fafc;
}
.landing-item:hover {
  background: #ffffff;
  border-color: #38bdf8;
  box-shadow: 0 4px 6px rgba(56, 189, 248, 0.1);
  transform: translateY(-2px);
}
'''

css = css.replace('/* NEW INVOICE GRID */', landing_css + '\n/* NEW INVOICE GRID */')

with open('src/app/billing/billing.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Landing view styles restored')

