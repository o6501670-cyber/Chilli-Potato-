import re

with open('frontend/src/app/finance/finance.html', encoding='utf-8') as f:
    content = f.read()

new_html = """  <!-- CLOSING & PETTY CASH -->
  <div class="tab-body" *ngIf="activeMainTab === 'pettycash'">
    <div class="sub-tabs-bar">
      <button class="sub-tab" [class.active]="activeClosingTab === 'admin'" (click)="setClosingTab('admin')">Admin View</button>
      <button class="sub-tab" [class.active]="activeClosingTab === 'manager'" (click)="setClosingTab('manager')">Manager View</button>
    </div>

    <!-- MANAGER VIEW -->
    <div *ngIf="activeClosingTab === 'manager'" class="split-layout">
      
      <!-- LEFT: PETTY CASH LOG -->
      <div class="list-column" style="flex: 1.2;">
        <div class="form-card" style="margin-bottom: 1.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h4 style="margin: 0;">Petty Cash Log</h4>
            <select class="form-control" style="width: auto; margin-bottom: 0;" [(ngModel)]="selectedFilterLocation" (change)="onLocationChange()">
              <option [ngValue]="null" *ngIf="isOwner">All Locations</option>
              <option *ngFor="let c of centers" [ngValue]="c.id">{{ c.display_name || c.center_name }}</option>
            </select>
          </div>
          
          <!-- Entry Form -->
          <div class="form-row">
            <input type="text" class="form-control" placeholder="Enter Description" [(ngModel)]="pettyCashForm.description">
            <input type="number" class="form-control" placeholder="Enter Amount in Rs." [(ngModel)]="pettyCashForm.amount">
            <input type="text" class="form-control" placeholder="Voucher Number" [(ngModel)]="pettyCashForm.voucher_number">
          </div>
          <div class="form-row" style="align-items: flex-start;">
            <textarea class="form-control" placeholder="Enter Comments (Compulsory)" [(ngModel)]="pettyCashForm.comments" rows="2" style="flex: 2; margin-bottom: 0;"></textarea>
            <button class="btn btn-primary" (click)="submitPettyCash()" [disabled]="isSaving" style="flex: 1; height: 100%; margin-left: 1rem;">
              <span *ngIf="isSaving">Saving...</span>
              <span *ngIf="!isSaving">Spend</span>
            </button>
          </div>
        </div>

        <!-- Log Table -->
        <div class="list-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Name</th>
                <th>Description</th>
                <th>Voucher No.</th>
                <th class="num">Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let log of pettyCashLogs">
                <td style="color: var(--primary-color);">{{ log.date | date:'dd-MMM-yyyy HH:mm' }}</td>
                <td>{{ log.user_name || '—' }}</td>
                <td>{{ log.description }}</td>
                <td>{{ log.voucher_number || '—' }}</td>
                <td class="num" style="color: var(--primary-color);">Rs. {{ log.amount }}</td>
                <td>
                  <button class="btn btn-primary" style="padding: 0.2rem 0.5rem; font-size: 0.7rem; margin-right: 0.5rem;" title="Details">ℹ</button>
                  <button class="btn btn-primary" style="padding: 0.2rem 0.5rem; font-size: 0.7rem; background: var(--surface); color: var(--text-primary); border: 1px solid var(--border);" (click)="editPettyCash(log)">Edit</button>
                </td>
              </tr>
              <tr *ngIf="pettyCashLogs.length === 0">
                <td colspan="6" class="text-center" style="padding: 2rem; color: var(--text-secondary); text-align: center;">No petty cash entries for this location.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- RIGHT: DAILY CLOSING -->
      <div class="form-card" style="flex: 1;">
        <h3 class="text-center">Daily Closing</h3>
        
        <div style="text-align: center; margin-bottom: 1.5rem;">
          <input type="date" class="form-control" style="width: auto; display: inline-block;" [(ngModel)]="closingDate" (change)="onClosingDateChange()">
        </div>
        
        <div class="empty-state-small" style="color: #ef4444;" *ngIf="noClosingForDate">
          No Closing saved for this date!
        </div>

        <!-- CASH section -->
        <div class="list-card" style="margin-bottom: 1.5rem;">
          <h4 style="margin-top: 0;">CASH</h4>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>Opening Balance</span><span>{{ closingData.opening_balance }}</span></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;">
            <span>Cash in hand</span>
            <input type="number" class="form-control" placeholder="Amount" style="width: 120px; margin-bottom: 0; background: #fca5a5; text-align: center;" [(ngModel)]="closingData.cash_in_hand">
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>Today's Expenses</span><span style="color: #ef4444;">{{ closingData.todays_expenses || 0 }}</span></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; font-size: 0.9rem;">
            <span>Cash Deposit</span>
            <input type="number" class="form-control" placeholder="Amount" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.cash_deposit">
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.9rem; border-top: 1px solid var(--border); padding-top: 0.5rem;"><span>Closing Balance</span><strong>{{ closingBalance > 0 ? formatCurrency(closingBalance) : '-' }}</strong></div>
        </div>

        <!-- Credit/Debit Card -->
        <div class="list-card" style="margin-bottom: 1.5rem;">
          <h4 style="margin-top: 0;">CREDIT/DEBIT CARD</h4>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span>Credit/Debit Card</span>
            <input type="number" class="form-control" placeholder="Amount" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.credit_card">
          </div>
        </div>

        <!-- Other Payment Methods -->
        <div class="list-card" style="margin-bottom: 1.5rem;">
          <h4 style="margin-top: 0;">OTHER PAYMENT METHODS</h4>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>PayTM</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.paytm"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>Bharat Pay</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.bharat_pe"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>Cheque/Net Banking</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.cheque_netbanking"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>GooglePay</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.google_pay"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>Phone Pe</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.phone_pe"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; font-size: 0.9rem;"><span>NearBuy</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.nearbuy"></div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;"><span>Other</span><input type="number" class="form-control" style="width: 120px; margin-bottom: 0; text-align: center;" [(ngModel)]="closingData.other"></div>
        </div>

        <button class="btn btn-primary" (click)="submitClosing()" [disabled]="isSaving" style="width: 100%; padding: 0.75rem;">
          <span *ngIf="isSaving">Submitting...</span>
          <span *ngIf="!isSaving">SUBMIT</span>
        </button>
      </div>
    </div>

    <!-- ADMIN VIEW -->
    <div *ngIf="activeClosingTab === 'admin'" class="split-layout">
      
      <!-- LEFT: Totals Table -->
      <div class="list-column" style="flex: 1.5;">
        <div style="display: flex; gap: 1rem; align-items: center; font-size: 0.85rem; margin-bottom: 1rem; padding: 0.5rem; background: var(--surface); border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <label style="color: var(--text-secondary);">Salon: </label>
            <select class="form-control" [(ngModel)]="selectedFilterLocation" (change)="loadClosingHistory()" style="width: auto; margin-bottom: 0; padding: 0.3rem 0.5rem;">
              <option [ngValue]="null">All Locations</option>
              <option *ngFor="let c of centers" [ngValue]="c.id">{{ c.center_name }}</option>
            </select>
          </div>
          <input type="date" class="form-control" [(ngModel)]="startDate" style="width: auto; margin-bottom: 0; padding: 0.3rem 0.5rem;">
          <input type="date" class="form-control" [(ngModel)]="endDate" style="width: auto; margin-bottom: 0; padding: 0.3rem 0.5rem;">
          <button class="btn btn-primary" (click)="loadClosingHistory()" style="padding: 0.35rem 1rem;">Run</button>
          <button class="btn btn-outline" title="Export Excel" (click)="exportClosingHistory()" style="padding: 0.35rem 1rem; color: #10b981; border-color: #10b981;">
            <i class="bi bi-file-earmark-excel"></i> Export
          </button>
        </div>
        
        <div class="list-card">
          <table class="data-table">
            <thead>
              <tr style="background: var(--bg-3);">
                <th colspan="8" style="text-align: center;">Totals</th>
              </tr>
              <tr style="background: var(--bg-2);">
                <th></th>
                <th class="num">{{ formatCurrency(adminTotals.opening) }}</th>
                <th class="num">{{ formatCurrency(adminTotals.system) }}</th>
                <th class="num" style="color: #ef4444;">{{ formatCurrency(-adminTotals.expenses) }}</th>
                <th class="num">{{ formatCurrency(adminTotals.cash_in_hand) }}</th>
                <th class="num" [ngStyle]="{'color': adminTotals.diff < 0 ? '#ef4444' : 'inherit'}">{{ formatCurrency(adminTotals.diff) }}</th>
                <th class="num">{{ formatCurrency(adminTotals.deposit) }}</th>
                <th class="num">{{ formatCurrency(adminTotals.closing) }}</th>
              </tr>
              <tr style="background: var(--bg-3);">
                <th colspan="8" style="text-align: center;">Cash</th>
              </tr>
              <tr>
                <th style="text-align: left;">Closed Type: Date</th>
                <th class="num">Op. Bal.</th>
                <th class="num">System</th>
                <th class="num">Expenses</th>
                <th class="num">Cash in hand</th>
                <th class="num">Diff</th>
                <th class="num">Bank Dep.</th>
                <th class="num">Cl. Bal.</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let row of closingHistory" (click)="selectAdminClosing(row)" [style.background]="selectedAdminClosing === row ? 'var(--bg-2)' : 'transparent'" style="cursor: pointer;">
                <td>{{ row.date | date:'dd-MMM-yyyy' }}</td>
                <td class="num" style="color: var(--text-secondary);">{{ row.opening_balance }}</td>
                <td class="num">{{ row.system_cash }}</td>
                <td class="num" style="color: #ef4444;">-{{ row.todays_expenses }}</td>
                <td class="num">{{ row.cash_in_hand }}</td>
                <td class="num" [ngStyle]="{'color': row.difference < 0 ? '#ef4444' : 'inherit'}">{{ row.difference }}</td>
                <td class="num">{{ row.cash_deposit }}</td>
                <td class="num" style="color: var(--text-secondary);">{{ row.closing_balance }}</td>
              </tr>
              <tr *ngIf="closingHistory.length === 0">
                <td colspan="8" class="text-center" style="padding: 2rem; color: var(--text-secondary); text-align: center;">No closing records found.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- RIGHT: Selected Date Details -->
      <div class="list-column" style="flex: 1;" *ngIf="selectedAdminClosing">
        <h3 class="text-center" style="margin-top: 0;">{{ selectedAdminClosing.date | date:'dd-MMM-yyyy' }}</h3>
        
        <div class="list-card" style="margin-bottom: 1.5rem;">
          <h4 style="margin-top: 0; color: var(--text-secondary);">CASH</h4>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Opening Balance</span><span>{{ selectedAdminClosing.opening_balance }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Day's Collection</span><span>{{ selectedAdminClosing.system_cash }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Expenses</span><span style="color: #ef4444;">-{{ selectedAdminClosing.todays_expenses }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Expected Cash</span><span style="color: #059669;">{{ (parseFloat(selectedAdminClosing.opening_balance) + parseFloat(selectedAdminClosing.system_cash) - parseFloat(selectedAdminClosing.todays_expenses)).toFixed(2) }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Cash in Hand</span><span style="color: var(--primary-color);">{{ selectedAdminClosing.cash_in_hand }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.9rem;"><span style="color: var(--text-secondary);">Difference</span><span [ngStyle]="{'color': selectedAdminClosing.difference < 0 ? '#ef4444' : 'inherit'}">{{ selectedAdminClosing.difference }}</span></div>
          <div style="display: flex; justify-content: space-between; margin-top: 1rem; font-size: 0.9rem; padding-top: 0.5rem; border-top: 1px solid var(--border);">
            <span style="color: var(--text-secondary);">Cash for Deposit</span>
            <span style="display: inline-block; background: var(--bg-2); padding: 0.25rem 1rem; border-radius: 4px;">{{ selectedAdminClosing.cash_deposit }}</span>
          </div>
          <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; font-size: 0.9rem;">
            <span style="color: var(--text-secondary);">Closing Balance</span>
            <span style="display: inline-block; background: var(--surface); padding: 0.25rem 1rem; border-radius: 4px; color: var(--primary-color); border: 1px solid var(--border);">{{ selectedAdminClosing.closing_balance }}</span>
          </div>
        </div>

        <div class="list-card">
          <h4 style="margin-top: 0; color: var(--text-secondary);">OTHER PAYMENT METHODS</h4>
          <table class="data-table">
            <thead>
              <tr>
                <th style="text-align: left;">Type</th>
                <th class="num">CARD</th>
                <th class="num">PayTM</th>
                <th class="num">BharatPe</th>
                <th class="num">Cheque/NetBanking</th>
                <th class="num">Google Pay</th>
                <th class="num">PhonePe</th>
                <th class="num">NearBuy</th>
                <th class="num">Other</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="color: var(--text-secondary);">Collection</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.credit_card || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.paytm || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.bharat_pe || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.cheque_netbanking || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.google_pay || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.phone_pe || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.nearbuy || 0 }}</td>
                <td class="num" style="color: var(--primary-color);">{{ selectedAdminClosing.other || 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
"""

parts = content.split('  <!-- CLOSING & PETTY CASH -->')
new_content = parts[0] + new_html + "\n</div>\n"

with open('frontend/src/app/finance/finance.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated finance.html")
