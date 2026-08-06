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
    <div *ngIf="activeClosingTab === 'manager'" class="petty-cash-container" style="display: flex; gap: 20px; padding: 20px; background-color: #f8fafc;">
      
      <!-- LEFT: PETTY CASH LOG -->
      <div class="petty-log-panel" style="flex: 1.2;">
        <div class="manager-location-bar" style="margin-bottom: 20px;">
          <select class="location-select" [(ngModel)]="selectedFilterLocation" (change)="onLocationChange()" style="padding: 8px; border-radius: 4px; border: 1px solid #cbd5e1;">
            <option [ngValue]="null" *ngIf="isOwner">All Locations</option>
            <option *ngFor="let c of centers" [ngValue]="c.id">{{ c.display_name || c.center_name }}</option>
          </select>
        </div>
        <div class="panel-title" style="font-weight: bold; margin-bottom: 15px;">Petty Cash Log</div>
        
        <!-- Entry Form -->
        <div class="petty-form" style="display: flex; gap: 20px; margin-bottom: 20px;">
          <div class="petty-form-left" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
            <input type="text" class="pc-input" placeholder="Enter Description" [(ngModel)]="pettyCashForm.description" style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 20px; outline: none;">
            <input type="number" class="pc-input" placeholder="Enter Amount in Rs." [(ngModel)]="pettyCashForm.amount" style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 20px; outline: none;">
            <input type="text" class="pc-input" placeholder="Voucher Number" [(ngModel)]="pettyCashForm.voucher_number" style="padding: 10px; border: 1px solid #e2e8f0; border-radius: 20px; outline: none;">
          </div>
          <div class="petty-form-right" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
            <textarea class="pc-textarea" placeholder="Enter Comments (Compulsory)" [(ngModel)]="pettyCashForm.comments" style="height: 100px; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; outline: none;"></textarea>
            <button class="btn-spend" (click)="submitPettyCash()" [disabled]="isSaving" style="background-color: #0c4a6e; color: white; padding: 10px; border-radius: 4px; border: none; font-weight: 600; cursor: pointer;">
              <span *ngIf="isSaving">Saving...</span>
              <span *ngIf="!isSaving">Spend</span>
            </button>
          </div>
        </div>

        <!-- Log Table -->
        <div class="petty-table-wrap" style="background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <table class="data-table" style="width: 100%; text-align: left; border-collapse: collapse;">
            <thead>
              <tr style="background: #f1f5f9; border-bottom: 1px solid #e2e8f0;">
                <th style="padding: 10px;">Date</th>
                <th style="padding: 10px;">Name</th>
                <th style="padding: 10px;">Description</th>
                <th style="padding: 10px;">Voucher No.</th>
                <th class="num" style="padding: 10px;">Amount</th>
                <th style="padding: 10px;"></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let log of pettyCashLogs" style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 10px; color: #0284c7;">{{ log.date | date:'dd-MMM-yyyy HH:mm' }}</td>
                <td style="padding: 10px;">{{ log.user_name || '—' }}</td>
                <td style="padding: 10px;">{{ log.description }}</td>
                <td style="padding: 10px;">{{ log.voucher_number || '—' }}</td>
                <td class="num" style="padding: 10px; color: #0284c7;">Rs. {{ log.amount }}</td>
                <td class="action-cell" style="padding: 10px;">
                  <button class="btn-info" title="Details" style="background: #0284c7; color: white; border: none; border-radius: 50%; width: 24px; height: 24px; cursor: pointer;">ℹ</button>
                  <button class="btn-edit" (click)="editPettyCash(log)" style="background: transparent; color: #64748b; border: none; cursor: pointer; text-decoration: underline;">Edit</button>
                </td>
              </tr>
              <tr *ngIf="pettyCashLogs.length === 0">
                <td colspan="6" class="empty-cell" style="padding: 20px; text-align: center;">No petty cash entries for this location.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- RIGHT: DAILY CLOSING -->
      <div class="closing-form-panel" style="flex: 1;">
        <div class="panel-title" style="text-align: center; margin-bottom: 20px; font-weight: bold;">Daily Closing</div>
        
        <div class="closing-date-selector" style="text-align: center; margin-bottom: 10px;">
          <input type="date" class="closing-date-input" [(ngModel)]="closingDate" (change)="onClosingDateChange()" style="padding: 8px 16px; border-radius: 20px; border: 1px solid #cbd5e1; outline: none; background: white;">
        </div>
        
        <div class="no-closing-msg" *ngIf="noClosingForDate" style="text-align: center; color: #ef4444; margin-bottom: 20px; font-size: 13px;">
          No Closing saved for this date!
        </div>

        <!-- CASH section -->
        <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 15px;">
          <div class="closing-block-title" style="margin-bottom: 15px; font-weight: bold; font-size: 14px;">CASH</div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Opening Balance</span><span class="closing-val">{{ closingData.opening_balance }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;">
            <span class="closing-label">Cash in hand</span>
            <input type="number" class="cash-in-hand-input" placeholder="Enter Amount" style="background-color: #fca5a5; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.cash_in_hand">
          </div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Today's Expenses</span><span class="closing-val" style="color: #ef4444;">{{ closingData.todays_expenses || 0 }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;">
            <span class="closing-label">Cash Deposit</span>
            <input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.cash_deposit">
          </div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 13px;"><span class="closing-label">Closing Balance</span><span class="closing-val">{{ closingBalance > 0 ? formatCurrency(closingBalance) : '-' }}</span></div>
        </div>

        <!-- Credit/Debit Card -->
        <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 15px;">
          <div class="closing-block-title" style="margin-bottom: 15px; font-weight: bold; font-size: 14px;">CREDIT/DEBIT CARD</div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
            <span class="closing-label">Credit/Debit Card</span>
            <input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.credit_card">
          </div>
        </div>

        <!-- Other Payment Methods -->
        <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
          <div class="closing-block-title" style="margin-bottom: 15px; font-weight: bold; font-size: 14px;">OTHER PAYMENT METHODS</div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">PayTM</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.paytm"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Bharat Pay</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.bharat_pe"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Cheque/Net Banking</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.cheque_netbanking"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">GooglePay</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.google_pay"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Phone Pe</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.phone_pe"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">NearBuy</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.nearbuy"></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px;"><span class="closing-label">Other</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 6px 12px; border: none; border-radius: 16px; outline: none; text-align: center; width: 120px;" [(ngModel)]="closingData.other"></div>
        </div>

        <div style="text-align: center; margin-top: 20px;">
          <button class="btn-submit-closing" (click)="submitClosing()" [disabled]="isSaving" style="background-color: #0c4a6e; color: white; padding: 10px 40px; border-radius: 4px; border: none; font-weight: 600; cursor: pointer;">
            <span *ngIf="isSaving">Submitting...</span>
            <span *ngIf="!isSaving">SUBMIT</span>
          </button>
        </div>
      </div>
    </div>

    <!-- ADMIN VIEW -->
    <div *ngIf="activeClosingTab === 'admin'" class="admin-closing-container" style="display: flex; gap: 20px; padding: 20px; background-color: #f8fafc;">
      
      <!-- LEFT: Totals Table -->
      <div class="admin-closing-left" style="flex: 1.5;">
        <div class="filters-row" style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <label style="font-size: 13px; color: #64748b;">Salon: </label>
            <select class="dropdown" [(ngModel)]="selectedFilterLocation" (change)="loadClosingHistory()" style="padding: 6px 12px; border-radius: 16px; border: 1px solid #cbd5e1; outline: none; background: white;">
              <option [ngValue]="null">All Locations</option>
              <option *ngFor="let c of centers" [ngValue]="c.id">{{ c.center_name }}</option>
            </select>
          </div>
          <input type="date" class="date-input" [(ngModel)]="startDate" style="padding: 6px 12px; border-radius: 16px; border: 1px solid #cbd5e1; outline: none; background: white;">
          <input type="date" class="date-input" [(ngModel)]="endDate" style="padding: 6px 12px; border-radius: 16px; border: 1px solid #cbd5e1; outline: none; background: white;">
          <button class="btn-primary" (click)="loadClosingHistory()" style="background-color: #0c4a6e; color: white; padding: 6px 12px; border-radius: 16px; border: none; cursor: pointer;">Run</button>
          <button class="btn-secondary" title="Export Excel" (click)="exportClosingHistory()" style="background-color: #10b981; color: white; padding: 6px 12px; border-radius: 4px; border: none; cursor: pointer;">
            <span style="font-weight: bold;">X</span>
          </button>
        </div>
        
        <table class="data-table" style="font-size: 12px; width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <thead>
            <tr style="background: #9ca3af; color: white;">
              <th colspan="8" style="text-align: center; padding: 8px;">Totals</th>
            </tr>
            <tr style="background: #e5e7eb;">
              <th style="padding: 8px;"></th>
              <th style="padding: 8px; text-align: right;">{{ formatCurrency(adminTotals.opening) }}</th>
              <th style="padding: 8px; text-align: right;">{{ formatCurrency(adminTotals.system) }}</th>
              <th style="padding: 8px; text-align: right; color: #ef4444;">{{ formatCurrency(-adminTotals.expenses) }}</th>
              <th style="padding: 8px; text-align: right;">{{ formatCurrency(adminTotals.cash_in_hand) }}</th>
              <th style="padding: 8px; text-align: right;" [ngStyle]="{'color': adminTotals.diff < 0 ? '#ef4444' : 'inherit'}">{{ formatCurrency(adminTotals.diff) }}</th>
              <th style="padding: 8px; text-align: right;">{{ formatCurrency(adminTotals.deposit) }}</th>
              <th style="padding: 8px; text-align: right;">{{ formatCurrency(adminTotals.closing) }}</th>
            </tr>
            <tr style="background: #d1d5db;">
              <th colspan="8" style="text-align: center; padding: 8px;">Cash</th>
            </tr>
            <tr style="background: white; border-bottom: 1px solid #e2e8f0; color: #64748b;">
              <th style="padding: 8px; text-align: left;">Closed Type: Date</th>
              <th style="padding: 8px; text-align: right;">Op. Bal.</th>
              <th style="padding: 8px; text-align: right;">System</th>
              <th style="padding: 8px; text-align: right;">Expenses</th>
              <th style="padding: 8px; text-align: right;">Cash in hand</th>
              <th style="padding: 8px; text-align: right;">Diff</th>
              <th style="padding: 8px; text-align: right;">Bank Dep.</th>
              <th style="padding: 8px; text-align: right;">Cl. Bal.</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let row of closingHistory" (click)="selectAdminClosing(row)" [style.background]="selectedAdminClosing === row ? '#f1f5f9' : 'transparent'" style="cursor: pointer; border-bottom: 1px solid #f1f5f9;">
              <td style="padding: 10px;">{{ row.date | date:'dd-MMM-yyyy' }}</td>
              <td style="padding: 10px; text-align: right; color: #9ca3af;">{{ row.opening_balance }}</td>
              <td style="padding: 10px; text-align: right;">{{ row.system_cash }}</td>
              <td style="padding: 10px; text-align: right; color: #ef4444;">-{{ row.todays_expenses }}</td>
              <td style="padding: 10px; text-align: right;">{{ row.cash_in_hand }}</td>
              <td style="padding: 10px; text-align: right;" [ngStyle]="{'color': row.difference < 0 ? '#ef4444' : 'inherit'}">{{ row.difference }}</td>
              <td style="padding: 10px; text-align: right;">{{ row.cash_deposit }}</td>
              <td style="padding: 10px; text-align: right; color: #9ca3af;">{{ row.closing_balance }}</td>
            </tr>
            <tr *ngIf="closingHistory.length === 0">
              <td colspan="8" style="text-align: center; padding: 20px; color: #64748b;">No closing records found.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- RIGHT: Selected Date Details -->
      <div class="admin-closing-right" style="flex: 1;" *ngIf="selectedAdminClosing">
        <div style="font-size: 16px; text-align: center; margin-bottom: 20px;">
          {{ selectedAdminClosing.date | date:'dd-MMM-yyyy' }}
        </div>
        
        <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
          <div class="closing-block-title" style="margin-bottom: 15px; font-size: 12px; color: #64748b;">CASH</div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Opening Balance</span><span>{{ selectedAdminClosing.opening_balance }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Day's Collection</span><span>{{ selectedAdminClosing.system_cash }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Expenses</span><span style="color: #ef4444;">-{{ selectedAdminClosing.todays_expenses }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Expected Cash</span><span style="color: #059669;">{{ (parseFloat(selectedAdminClosing.opening_balance) + parseFloat(selectedAdminClosing.system_cash) - parseFloat(selectedAdminClosing.todays_expenses)).toFixed(2) }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Cash in Hand</span><span style="color: #0284c7;">{{ selectedAdminClosing.cash_in_hand }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;"><span class="closing-label" style="color: #64748b;">Difference</span><span [ngStyle]="{'color': selectedAdminClosing.difference < 0 ? '#ef4444' : 'inherit'}">{{ selectedAdminClosing.difference }}</span></div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-top: 15px; font-size: 13px;">
            <span class="closing-label" style="color: #64748b;">Cash for Deposit</span>
            <span style="display: inline-block; background: #e5e7eb; padding: 4px 20px; border-radius: 4px;">{{ selectedAdminClosing.cash_deposit }}</span>
          </div>
          <div class="closing-row" style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 13px;">
            <span class="closing-label" style="color: #64748b;">Closing Balance</span>
            <span style="display: inline-block; background: #f8fafc; padding: 4px 20px; border-radius: 4px; color: #0284c7;">{{ selectedAdminClosing.closing_balance }}</span>
          </div>
        </div>

        <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto;">
          <div class="closing-block-title" style="margin-bottom: 15px; font-size: 12px; color: #64748b;">OTHER PAYMENT METHODS</div>
          <table class="data-table" style="font-size: 11px; width: 100%; border-collapse: collapse;">
            <thead>
              <tr style="border-bottom: 1px solid #e2e8f0; color: #64748b;">
                <th style="padding: 8px; text-align: left;">Type</th>
                <th style="padding: 8px; text-align: right;">CARD</th>
                <th style="padding: 8px; text-align: right;">PayTM</th>
                <th style="padding: 8px; text-align: right;">BharatPe</th>
                <th style="padding: 8px; text-align: right;">Cheque/NetBanking</th>
                <th style="padding: 8px; text-align: right;">Google Pay</th>
                <th style="padding: 8px; text-align: right;">PhonePe</th>
                <th style="padding: 8px; text-align: right;">NearBuy</th>
                <th style="padding: 8px; text-align: right;">Other</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="padding: 8px; color: #64748b;">Collection</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.credit_card || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.paytm || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.bharat_pe || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.cheque_netbanking || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.google_pay || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.phone_pe || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.nearbuy || 0 }}</td>
                <td style="padding: 8px; text-align: right; color: #0284c7;">{{ selectedAdminClosing.other || 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
"""

# We want to replace from `<!-- CLOSING & PETTY CASH` down to `</div><!-- /pettycash -->`
# Wait, let's just use re.sub with carefully matching the start and end comments.
# If they don't exactly match, we can use the tab-body structure.

pattern = re.compile(r'  <!-- ================================================ -->\n  <!-- CLOSING & PETTY CASH                            -->\n  <!-- ================================================ -->\n.*?</div><!-- /pettycash -->', re.DOTALL)
content = pattern.sub(new_html, content)

open('frontend/src/app/finance/finance.html', 'w', encoding='utf-8').write(content)
