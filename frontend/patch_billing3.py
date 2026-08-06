
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

old_load = '''  loadClientAdvances(clientId: number) {
    this.apiService.get(\illing/advances/?client_id=\).subscribe((data: any) => {
      this.clientAdvances = data;
      this.clientAdvanceBalance = data.reduce((sum: number, adv: any) => sum + parseFloat(adv.amount), 0);
      this.buildClientHistory();
    });
  }'''

new_load = '''  loadClientAdvances(clientId: number) {
    this.apiService.get(\illing/advances/?client_id=\).subscribe((data: any) => {
      this.clientAdvances = data;
      // Balance is now correctly calculated by the backend and sent in the Client payload!
      this.clientAdvanceBalance = this.client?.advance_balance || 0;
      this.buildClientHistory();
    });
  }'''

text = text.replace(old_load, new_load)

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('frontend billing.ts patched.')

