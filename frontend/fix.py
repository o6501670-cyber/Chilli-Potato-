
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix syntax errors caused by invalid escapes
text = text.replace('\\\'error\\\'', 'error')
text = text.replace('\\\'success\\\'', 'success')

# Now properly replace handlePostSave
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

# Since regex is fragile with nested braces, I'll find the exact start and end
start_idx = text.find('handlePostSave(onHold: boolean, invoice: any) {')
if start_idx != -1:
    # Find matching brace
    brace_count = 0
    end_idx = -1
    for i in range(start_idx + len('handlePostSave(onHold: boolean, invoice: any) '), len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
    if end_idx != -1:
        text = text[:start_idx] + handle_post_save + text[end_idx+1:]

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed syntax errors and replaced handlePostSave')

