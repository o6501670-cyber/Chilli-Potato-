
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

# Add properties
if 'toastMessage: string' not in text:
    props = '''  // Toast Notifications
  toastMessage: string = '';
  toastType: 'success' | 'error' | 'info' = 'info';
  toastVisible: boolean = false;
  toastTimeout: any;

  showToast(msg: string, type: 'success' | 'error' | 'info' = 'info') {
    this.toastMessage = msg;
    this.toastType = type;
    this.toastVisible = true;
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      this.toastVisible = false;
    }, 3000);
  }
'''
    text = text.replace('export class BillingComponent implements OnInit {', 'export class BillingComponent implements OnInit {\n' + props)

# Replace alerts
import re
text = re.sub(r'alert\((.*?)\);', r'this.showToast(\1, \'error\');', text)
text = text.replace('this.showToast(\\\'Invoice updated successfully!\\\', \\\'error\\\');', 'this.showToast(\\\'Invoice updated successfully!\\\', \\\'success\\\');')
text = text.replace('this.showToast(\\\'Invoice generated successfully!\\\', \\\'error\\\');', 'this.showToast(\\\'Invoice generated successfully!\\\', \\\'success\\\');')

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('Toast logic added to TS')

