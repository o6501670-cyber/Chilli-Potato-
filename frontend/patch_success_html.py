
with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()

success_html = '''
<!-- Invoice Success Modal -->
<div class="modal-overlay" *ngIf="showSuccessModal" style="display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); position: fixed; inset: 0; z-index: 2000; backdrop-filter: blur(4px);">
  <div class="modal-content" style="background: var(--bg-card); border-radius: var(--radius-lg); width: 400px; padding: 32px 24px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.15); border: 1px solid var(--border); position: relative;">
    
    <div style="width: 64px; height: 64px; background: #10b981; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; margin: 0 auto 20px auto; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">
      <i class="fa fa-check"></i>
    </div>
    
    <h2 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 800; color: var(--text-primary);">Sale Complete!</h2>
    <p style="margin: 0 0 24px 0; font-size: 14px; color: var(--text-secondary);">Invoice #{{ completedInvoiceData?.id }} has been generated successfully.</p>
    
    <div style="display: flex; gap: 12px;">
      <button (click)="closeSuccessModal()" style="flex: 1; background: var(--bg-subtle); color: var(--text-primary); border: 1px solid var(--border); padding: 12px; border-radius: var(--radius-pill); font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#e7e8ec'" onmouseout="this.style.background='var(--bg-subtle)'">New Sale</button>
      <button (click)="printInvoice()" style="flex: 1; background: var(--ink); color: white; border: none; padding: 12px; border-radius: var(--radius-pill); font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.1);" onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'"><i class="fa fa-print" style="margin-right: 6px;"></i> Print Invoice</button>
    </div>

  </div>
</div>

<!-- Printable Invoice Section -->
<div class="print-only-invoice" *ngIf="completedInvoiceData">
  <div style="text-align: center; margin-bottom: 20px; border-bottom: 2px solid #000; padding-bottom: 10px;">
    <h1 style="margin: 0; font-size: 24px;">GEETANJALI SALON</h1>
    <p style="margin: 5px 0 0 0; font-size: 14px;">Invoice #{{ completedInvoiceData.id }}</p>
  </div>
  
  <div style="margin-bottom: 20px; font-size: 14px;">
    <strong>Billed To:</strong> {{ client?.first_name }} {{ client?.last_name }}<br>
    <strong>Phone:</strong> {{ client?.phone }}<br>
    <strong>Date:</strong> {{ completedInvoiceData.created_at | date:'medium' }}
  </div>

  <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
    <thead>
      <tr style="border-bottom: 1px solid #000;">
        <th style="text-align: left; padding: 8px 0;">Item</th>
        <th style="text-align: center; padding: 8px 0;">Qty</th>
        <th style="text-align: right; padding: 8px 0;">Amount</th>
      </tr>
    </thead>
    <tbody>
      <tr *ngFor="let item of completedInvoiceData.items" style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px 0;">{{ item.description }}</td>
        <td style="text-align: center; padding: 8px 0;">{{ item.quantity }}</td>
        <td style="text-align: right; padding: 8px 0;">Rs. {{ item.unit_price * item.quantity | number:'1.2-2' }}</td>
      </tr>
    </tbody>
  </table>

  <div style="text-align: right; font-size: 14px;">
    <p>Subtotal: Rs. {{ completedInvoiceData.subtotal | number:'1.2-2' }}</p>
    <p>Discount: Rs. {{ completedInvoiceData.discount | number:'1.2-2' }}</p>
    <p *ngIf="completedInvoiceData.cgst > 0">CGST: Rs. {{ completedInvoiceData.cgst | number:'1.2-2' }}</p>
    <p *ngIf="completedInvoiceData.sgst > 0">SGST: Rs. {{ completedInvoiceData.sgst | number:'1.2-2' }}</p>
    <h3 style="margin-top: 10px; border-top: 1px solid #000; padding-top: 10px; font-size: 18px;">Total: Rs. {{ completedInvoiceData.total_amount | number:'1.2-2' }}</h3>
  </div>
  
  <div style="text-align: center; margin-top: 40px; font-size: 12px; color: #666;">
    Thank you for your visit!
  </div>
</div>
'''

if 'Invoice Success Modal' not in text:
    text = text.replace('<!-- force reload html -->', success_html + '\n<!-- force reload html -->')
    with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
        f.write(text)

with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

print_css = '''
/* Print Styles */
.print-only-invoice {
  display: none;
}
@media print {
  body * {
    visibility: hidden;
  }
  .print-only-invoice, .print-only-invoice * {
    visibility: visible;
  }
  .print-only-invoice {
    display: block;
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    background: white;
    padding: 20px;
    box-sizing: border-box;
    color: black;
  }
}
'''
if 'print-only-invoice' not in css:
    with open('src/app/billing/billing.css', 'a', encoding='utf-8') as f:
        f.write(print_css)

print('Success Modal and Print Invoice HTML/CSS added')

