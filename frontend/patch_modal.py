
checkout_modal_html = '''
<!-- Checkout Modal (Split Payments) -->
<div class="modal-overlay" *ngIf="showCheckoutModal" style="display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.6); position: fixed; inset: 0; z-index: 1000; backdrop-filter: blur(4px);">
  <div class="modal-content" style="background: var(--bg-card); border-radius: var(--radius-lg); width: 600px; max-width: 90vw; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.15); border: 1px solid var(--border); position: relative;">
    
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 16px;">
      <h2 style="margin: 0; font-size: 18px; font-weight: 800; color: var(--text-primary);">Checkout & Payment</h2>
      <button (click)="closeCheckoutModal()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted); line-height: 1;">&times;</button>
    </div>

    <div style="background: var(--bg-subtle); padding: 20px; border-radius: var(--radius-md); margin-bottom: 24px; text-align: center; border: 1px solid var(--border);">
      <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">Total Bill Amount</div>
      <div style="font-size: 32px; font-weight: 800; color: var(--ink); margin-top: 8px;">Rs. {{ finalTotalAmount | number:'1.2-2' }}</div>
    </div>

    <h4 style="margin-top: 0; font-size: 13px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">Split Payments</h4>
    
    <div *ngFor="let p of checkoutPayments; let i = index" style="display: flex; gap: 12px; margin-bottom: 12px; align-items: center;">
      <select [(ngModel)]="p.method" (ngModelChange)="calcCheckoutRemaining()" style="flex: 1; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 13px; background: var(--bg-card); color: var(--text-primary); outline: none;">
        <option value="Cash">Cash</option>
        <option value="Card">Card</option>
        <option value="UPI">UPI</option>
        <option value="Cheque">Cheque</option>
        <option value="Advance">Advance/Wallet (Bal: Rs. {{clientAdvanceBalance}})</option>
        <!-- Value Cards -->
        <option *ngFor="let vc of client?.active_value_cards" [value]="'Value Card ' + vc.id">
          ?? {{ vc.value_card_detail?.title }} (Bal: ?{{ vc.balance | number:'1.2-2' }})
        </option>
      </select>
      
      <div style="position: relative; flex: 1;">
        <span style="position: absolute; left: 12px; top: 12px; color: var(--text-secondary); font-weight: 600; font-size: 13px;">Rs.</span>
        <input type="number" [(ngModel)]="p.amount" (ngModelChange)="calcCheckoutRemaining()" style="width: 100%; padding: 12px 12px 12px 40px; border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: 13px; font-weight: 600; box-sizing: border-box; background: var(--bg-card); color: var(--text-primary); outline: none;">
      </div>
      
      <button (click)="removePaymentRow(i)" *ngIf="checkoutPayments.length > 1" class="btn-icon-danger" style="padding: 10px;"><i class="fa fa-trash"></i></button>
    </div>

    <button (click)="addPaymentRow()" style="background: transparent; border: 1px dashed var(--border-strong, #c7cad3); width: 100%; padding: 12px; border-radius: var(--radius-sm); cursor: pointer; color: var(--text-secondary); font-weight: 600; font-size: 12.5px; margin-bottom: 24px; transition: all 0.2s;" onmouseover="this.style.background='var(--bg-subtle)'; this.style.color='var(--ink)'" onmouseout="this.style.background='transparent'; this.style.color='var(--text-secondary)'">
      + Add Another Payment Method
    </button>

    <div style="display: flex; justify-content: space-between; align-items: center; padding: 20px 0 0 0; border-top: 1px solid var(--border);">
      <div style="font-size: 13px; font-weight: 600;">
        <span style="color: var(--text-secondary);">Remaining to pay:</span> 
        <strong [style.color]="checkoutRemaining > 0 ? '#ef4444' : (checkoutRemaining < 0 ? '#d97706' : '#10b981')" style="font-size: 16px; margin-left: 8px;">Rs. {{ checkoutRemaining | number:'1.2-2' }}</strong>
      </div>
      <button (click)="saveInvoice(false)" [disabled]="checkoutRemaining > 0" [style.opacity]="checkoutRemaining > 0 ? '0.5' : '1'" style="background: var(--ink); color: white; border: none; padding: 14px 28px; border-radius: var(--radius-pill); font-weight: 700; font-size: 13px; cursor: pointer; transition: opacity 0.2s;">
        COMPLETE SALE
      </button>
    </div>

  </div>
</div>
'''

with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<!-- force reload html -->', checkout_modal_html + '\n<!-- force reload html -->')

with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Checkout modal restored and restyled.')

