import re

with open('frontend/src/app/finance/finance.html', encoding='utf-8') as f:
    content = f.read()

new_html = """    <div *ngIf="activeMainTab === 'pettycash'">
      <div class="sub-tabs">
        <div class="sub-tab" [class.active]="activeClosingTab === 'admin'" (click)="setClosingTab('admin')">Admin View</div>
        <div class="sub-tab" [class.active]="activeClosingTab === 'manager'" (click)="setClosingTab('manager')">Manager View</div>
      </div>

      <!-- MANAGER VIEW -->
      <div *ngIf="activeClosingTab === 'manager'" class="petty-cash-container" style="display: flex; gap: 20px; padding: 20px;">
        <!-- LEFT: PETTY CASH LOG -->
        <div class="petty-log-panel" style="flex: 1.2;">
          <div class="panel-title">Petty Cash Log</div>
          
          <!-- Entry Form -->
          <div class="petty-form" style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div class="petty-form-left" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
              <input type="text" class="pc-input" placeholder="Enter Description" [(ngModel)]="pettyCashForm.description">
              <input type="number" class="pc-input" placeholder="Enter Amount in Rs." [(ngModel)]="pettyCashForm.amount">
              <input type="text" class="pc-input" placeholder="Voucher Number" [(ngModel)]="pettyCashForm.voucher_number">
            </div>
            <div class="petty-form-right" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
              <textarea class="pc-textarea" placeholder="Enter Comments (Compulsory)" [(ngModel)]="pettyCashForm.comments" style="height: 100px;"></textarea>
              <button class="btn-spend" (click)="submitPettyCash()" [disabled]="isSaving" style="background-color: #0c4a6e; color: white; padding: 10px; border-radius: 4px; border: none; font-weight: 600;">
                <span *ngIf="isSaving">Saving...</span>
                <span *ngIf="!isSaving">Spend</span>
              </button>
            </div>
          </div>

          <!-- Log Table -->
          <div class="petty-table-wrap">
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
                  <td class="link-cell">{{ log.date | date:'dd-MMM-yyyy HH:mm' }}</td>
                  <td class="link-cell">{{ log.user_name || '—' }}</td>
                  <td>{{ log.description }}</td>
                  <td>{{ log.voucher_number || '—' }}</td>
                  <td class="num link-cell">Rs. {{ log.amount }}</td>
                  <td class="action-cell">
                    <button class="btn-info" title="Details">ℹ</button>
                    <button class="btn-edit" (click)="editPettyCash(log)">Edit</button>
                  </td>
                </tr>
                <tr *ngIf="pettyCashLogs.length === 0">
                  <td colspan="6" class="empty-cell">No petty cash entries for this location.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- RIGHT: DAILY CLOSING -->
        <div class="closing-form-panel" style="flex: 1;">
          <div class="panel-title" style="text-align: center; margin-bottom: 20px;">Daily Closing</div>
          
          <div class="closing-date-selector" style="text-align: center; margin-bottom: 10px;">
            <input type="date" class="closing-date-input" [(ngModel)]="closingDate" (change)="onClosingDateChange()" style="padding: 10px; border-radius: 20px; border: 1px solid #ccc;">
          </div>
          
          <div class="no-closing-msg" *ngIf="noClosingForDate" style="text-align: center; color: #ef4444; margin-bottom: 20px;">
            No Closing saved for this date!
          </div>

          <!-- CASH section -->
          <div class="closing-block" style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 15px;">
            <div class="closing-block-title" style="margin-bottom: 10px;">CASH</div>
            <div class="closing-row"><span class="closing-label">Opening Balance</span><span class="closing-val">{{ closingData.opening_balance }}</span></div>
            <div class="closing-row"><span class="closing-label">Cash in hand</span><input type="number" class="cash-in-hand-input" placeholder="Enter Amount" style="background-color: #fca5a5; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.cash_in_hand"></div>
            <div class="closing-row"><span class="closing-label">Today's Expenses</span><span class="closing-val" style="color: #ef4444;">{{ closingData.todays_expenses || 0 }}</span></div>
            <div class="closing-row"><span class="closing-label">Cash Deposit</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.cash_deposit"></div>
            <div class="closing-row"><span class="closing-label">Closing Balance</span><span class="closing-val">{{ closingBalance > 0 ? formatCurrency(closingBalance) : '-' }}</span></div>
          </div>

          <!-- Credit/Debit Card -->
          <div class="closing-block" style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 15px;">
            <div class="closing-block-title" style="margin-bottom: 10px;">CREDIT/DEBIT CARD</div>
            <div class="closing-row"><span class="closing-label">Credit/Debit Card</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.credit_card"></div>
          </div>

          <!-- Other Payment Methods -->
          <div class="closing-block" style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <div class="closing-block-title" style="margin-bottom: 10px;">OTHER PAYMENT METHODS</div>
            <div class="closing-row"><span class="closing-label">PayTM</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.paytm"></div>
            <div class="closing-row"><span class="closing-label">Bharat Pay</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.bharat_pe"></div>
            <div class="closing-row"><span class="closing-label">Cheque/Net Banking</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.cheque_netbanking"></div>
            <div class="closing-row"><span class="closing-label">GooglePay</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.google_pay"></div>
            <div class="closing-row"><span class="closing-label">Phone Pe</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.phone_pe"></div>
            <div class="closing-row"><span class="closing-label">NearBuy</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.nearbuy"></div>
            <div class="closing-row"><span class="closing-label">Other</span><input type="number" class="closing-amount-input" placeholder="Enter Amount" style="background-color: #e5e7eb; padding: 5px; border: none; border-radius: 4px;" [(ngModel)]="closingData.other"></div>
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
      <div *ngIf="activeClosingTab === 'admin'" class="admin-closing-container" style="display: flex; gap: 20px; padding: 20px;">
        
        <!-- LEFT: Totals Table -->
        <div class="admin-closing-left" style="flex: 1.5; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <div class="filters-row" style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
            <div>
              <label>Salon: </label>
              <select class="dropdown" [(ngModel)]="selectedFilterLocation" (change)="loadClosingHistory()">
                <option [value]="null">All Location</option>
                <option *ngFor="let c of centers" [value]="c.id">{{ c.center_name }}</option>
              </select>
            </div>
            <input type="date" class="date-input" [(ngModel)]="startDate">
            <input type="date" class="date-input" [(ngModel)]="endDate">
            <button class="btn-primary" (click)="loadClosingHistory()" style="padding: 8px 15px;">Run</button>
            <button class="btn-secondary" title="Export Excel" (click)="exportClosingHistory()">X</button>
          </div>
          
          <table class="data-table" style="font-size: 13px;">
            <thead>
              <tr style="background: #9ca3af; color: white;">
                <th colspan="8" style="text-align: center;">Totals</th>
              </tr>
              <tr style="background: #e5e7eb;">
                <th></th>
                <th>{{ formatCurrency(adminTotals.opening) }}</th>
                <th>{{ formatCurrency(adminTotals.system) }}</th>
                <th style="color: #ef4444;">{{ formatCurrency(-adminTotals.expenses) }}</th>
                <th>{{ formatCurrency(adminTotals.cash_in_hand) }}</th>
                <th [ngStyle]="{'color': adminTotals.diff < 0 ? '#ef4444' : 'inherit'}">{{ formatCurrency(adminTotals.diff) }}</th>
                <th>{{ formatCurrency(adminTotals.deposit) }}</th>
                <th>{{ formatCurrency(adminTotals.closing) }}</th>
              </tr>
              <tr style="background: #d1d5db;">
                <th colspan="8" style="text-align: center;">Cash</th>
              </tr>
              <tr>
                <th>Date</th>
                <th>Op. Bal.</th>
                <th>System</th>
                <th>Expenses</th>
                <th>Cash in hand</th>
                <th>Diff</th>
                <th>Bank Dep.</th>
                <th>Cl. Bal.</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let row of closingHistory" (click)="selectAdminClosing(row)" [style.background]="selectedAdminClosing === row ? '#f3f4f6' : 'transparent'" style="cursor: pointer;">
                <td>{{ row.date | date:'dd-MMM-yyyy' }}</td>
                <td>{{ row.opening_balance }}</td>
                <td>{{ row.system_cash }}</td>
                <td style="color: #ef4444;">-{{ row.todays_expenses }}</td>
                <td>{{ row.cash_in_hand }}</td>
                <td [ngStyle]="{'color': row.difference < 0 ? '#ef4444' : 'inherit'}">{{ row.difference }}</td>
                <td>{{ row.cash_deposit }}</td>
                <td>{{ row.closing_balance }}</td>
              </tr>
              <tr *ngIf="closingHistory.length === 0">
                <td colspan="8" style="text-align: center; padding: 20px;">No closing records found.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- RIGHT: Selected Date Details -->
        <div class="admin-closing-right" style="flex: 1;" *ngIf="selectedAdminClosing">
          <div style="font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 20px;">
            {{ selectedAdminClosing.date | date:'dd-MMM-yyyy' }}
          </div>
          
          <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <div class="closing-block-title" style="margin-bottom: 15px;">CASH</div>
            <div class="closing-row"><span class="closing-label">Opening Balance</span><span>{{ selectedAdminClosing.opening_balance }}</span></div>
            <div class="closing-row"><span class="closing-label">Day's Collection</span><span>{{ selectedAdminClosing.system_cash }}</span></div>
            <div class="closing-row"><span class="closing-label">Expenses</span><span style="color: #ef4444;">-{{ selectedAdminClosing.todays_expenses }}</span></div>
            <div class="closing-row"><span class="closing-label">Expected Cash</span><span style="color: #059669;">{{ (parseFloat(selectedAdminClosing.opening_balance) + parseFloat(selectedAdminClosing.system_cash) - parseFloat(selectedAdminClosing.todays_expenses)).toFixed(2) }}</span></div>
            <div class="closing-row"><span class="closing-label">Cash in Hand</span><span style="color: #0284c7;">{{ selectedAdminClosing.cash_in_hand }}</span></div>
            <div class="closing-row"><span class="closing-label">Difference</span><span [ngStyle]="{'color': selectedAdminClosing.difference < 0 ? '#ef4444' : 'inherit'}">{{ selectedAdminClosing.difference }}</span></div>
            <div class="closing-row" style="margin-top: 15px;">
              <span class="closing-label">Cash for Deposit</span>
              <span style="display: inline-block; background: #e5e7eb; padding: 5px 15px; border-radius: 4px;">{{ selectedAdminClosing.cash_deposit }}</span>
            </div>
            <div class="closing-row">
              <span class="closing-label">Closing Balance</span>
              <span style="display: inline-block; background: #f3f4f6; padding: 5px 15px; border-radius: 4px;">{{ selectedAdminClosing.closing_balance }}</span>
            </div>
          </div>

          <div class="closing-block" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto;">
            <div class="closing-block-title" style="margin-bottom: 15px;">OTHER PAYMENT METHODS</div>
            <table class="data-table" style="font-size: 12px;">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>CARD</th>
                  <th>PayTM</th>
                  <th>BharatPe</th>
                  <th>Cheque/NetBanking</th>
                  <th>Google Pay</th>
                  <th>PhonePe</th>
                  <th>NearBuy</th>
                  <th>Other</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Collection</td>
                  <td>{{ selectedAdminClosing.credit_card || 0 }}</td>
                  <td>{{ selectedAdminClosing.paytm || 0 }}</td>
                  <td>{{ selectedAdminClosing.bharat_pe || 0 }}</td>
                  <td>{{ selectedAdminClosing.cheque_netbanking || 0 }}</td>
                  <td>{{ selectedAdminClosing.google_pay || 0 }}</td>
                  <td>{{ selectedAdminClosing.phone_pe || 0 }}</td>
                  <td>{{ selectedAdminClosing.nearbuy || 0 }}</td>
                  <td>{{ selectedAdminClosing.other || 0 }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>"""

content = re.sub(r'    <div \*ngIf=\"activeMainTab === \'pettycash\'\">.*?</div><!-- /pettycash -->', new_html + '\n    <!-- /pettycash -->', content, flags=re.DOTALL)
open('frontend/src/app/finance/finance.html', 'w', encoding='utf-8').write(content)
