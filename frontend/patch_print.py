
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

props = '''
  // Success & Print Flow
  showSuccessModal: boolean = false;
  completedInvoiceData: any = null;

  printInvoice() {
    window.print();
  }

  closeSuccessModal() {
    this.showSuccessModal = false;
    this.completedInvoiceData = null;
    this.discardInvoice();
  }
'''
if 'showSuccessModal' not in text:
    text = text.replace('toastVisible: boolean = false;', 'toastVisible: boolean = false;\n' + props)

handle_post_save = '''handlePostSave(onHold: boolean, invoice: any) {
    this.closeCheckoutModal();
    const advanceItem = this.cart.find(it => it.content_type === 'advance');
    
    const finish = () => {
        if (!onHold) {
            this.completedInvoiceData = invoice;
            this.showSuccessModal = true;
        } else {
            this.discardInvoice();
        }
    };

    if (!onHold && advanceItem) {
        this.apiService.post(illing/advances/, {
            client: this.client.id,
            amount: advanceItem.unit_price * advanceItem.quantity,
            notes: advanceItem.description || 'Advance Payment'
        }).subscribe(() => {
            finish();
        });
    } else {
        finish();
    }
  }'''

import re
text = re.sub(r'handlePostSave\(onHold: boolean, invoice: any\)\s*\{(?:[^{}]*|\{[^{}]*\})*\}', handle_post_save, text)

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('Success modal logic added to TS')

