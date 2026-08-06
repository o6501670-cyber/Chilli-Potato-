import re

with open('frontend/src/app/finance/finance.ts', encoding='utf-8') as f:
    content = f.read()

# Add activeClosingTab
content = content.replace("activePettyCashTab = 'admin';", "activeClosingTab = 'manager';")
content = content.replace("this.activePettyCashTab = tab;", "this.activeClosingTab = tab;")
content = content.replace("if (tab === 'admin') this.loadClosingHistory();", "if (tab === 'admin') this.loadClosingHistory();\n    if (tab === 'manager') this.loadTodayClosingData();")

# Update setPettyCashTab
content = content.replace("setPettyCashTab(tab: string) {", "setClosingTab(tab: string) {")

# Remove Shift logic in loadTodayClosingData
load_today_closing_logic = '''
  loadTodayClosingData() {
    if (!this.selectedFilterLocation) return;
    const cid = this.selectedFilterLocation;
    
    // Fetch today's register summary for 'system cash'
    this.apiService.getRegisterSummary(cid, this.closingDate, this.closingDate).subscribe(res => {
      const cash = parseFloat(res?.summary?.total_cash || 0);
      this.closingData.system_cash = cash;
      this.closingPaymentSummary = res?.payment_methods;
      
      // Check if a closing already exists for this date
      this.apiService.getDailyClosings(cid, this.closingDate).subscribe(existing => {
        if (existing && existing.length > 0) {
          const saved = existing[0];
          this.noClosingForDate = false;
          this.closingData = { ...this.closingData, ...saved };
        } else {
          this.noClosingForDate = true;
          this.closingData.todays_expenses = this.todaysExpenses;
        }
      });
    });
  }
'''
# Using regex to replace loadTodayClosingData function completely
content = re.sub(r'  loadTodayClosingData\(\) \{.*?\n  \}\n', load_today_closing_logic.lstrip(), content, flags=re.DOTALL)

# Simplify expectedCash calculation
expected_cash_logic = '''
  get expectedCash(): number {
    return (parseFloat(this.closingData.opening_balance || 0) +
            parseFloat(this.closingData.system_cash || 0) -
            parseFloat(this.closingData.todays_expenses || 0));
  }
'''
content = re.sub(r'  get expectedCash\(\): number \{.*?\n  \}\n', expected_cash_logic.lstrip(), content, flags=re.DOTALL)

# Modify closing payload
submit_closing_logic = '''
  submitClosing() {
    if (!this.selectedFilterLocation) return;
    this.isSaving = true;

    const data = {
      center: this.selectedFilterLocation,
      date: this.closingDate,
      opening_balance: this.closingData.opening_balance || 0,
      system_cash: this.closingData.system_cash || 0,
      todays_expenses: this.closingData.todays_expenses || 0,
      cash_in_hand: this.closingData.cash_in_hand || 0,
      difference: (parseFloat(this.closingData.cash_in_hand || 0) - this.expectedCash),
      cash_deposit: this.closingData.cash_deposit || 0,
      closing_balance: this.closingBalance,
      credit_card: this.closingData.credit_card || 0,
      upi: this.closingData.upi || 0,
      paytm: this.closingData.paytm || 0,
      bharat_pe: this.closingData.bharat_pe || 0,
      cheque_netbanking: this.closingData.cheque_netbanking || 0,
      google_pay: this.closingData.google_pay || 0,
      phone_pe: this.closingData.phone_pe || 0,
      nearbuy: this.closingData.nearbuy || 0,
      other: this.closingData.other || 0,
    };

    this.apiService.submitDailyClosing(data).subscribe({
      next: (res) => {
        this.noClosingForDate = false;
        alert('Closing submitted successfully!');
        this.loadClosingHistory();
        this.isSaving = false;
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.error?.non_field_errors?.[0] || 'Failed to submit closing.';
        alert(msg);
        this.isSaving = false;
      }
    });
  }
'''
content = re.sub(r'  submitClosing\(\) \{.*?\n  \}\n', submit_closing_logic.lstrip(), content, flags=re.DOTALL)

# Remove shift related logic
content = re.sub(r'  openShift\(\) \{.*?\n  \}\n', '', content, flags=re.DOTALL)
content = re.sub(r'  closeShift\(\) \{.*?\n  \}\n', '', content, flags=re.DOTALL)
content = re.sub(r'  loadActiveShift\(\) \{.*?\n  \}\n', '', content, flags=re.DOTALL)

# Add load closing history date range filtering
load_history_logic = '''
  loadClosingHistory() {
    if (!this.selectedFilterLocation) return;
    const params: any = { center_id: this.selectedFilterLocation };
    if (this.startDate) params.start_date = this.startDate;
    if (this.endDate) params.end_date = this.endDate;
    
    this.apiService.get('finance/api/daily-closing/', params).subscribe(data => {
      this.closingHistory = data;
    });
  }
'''
content = re.sub(r'  loadClosingHistory\(\) \{.*?\n  \}\n', load_history_logic.lstrip(), content, flags=re.DOTALL)


# Calculate totals for admin view table
admin_totals_logic = '''
  // ---- Admin View Data ----
  selectedAdminClosing: any = null;
  
  get adminTotals() {
    let totals = {
      opening: 0, system: 0, expenses: 0, cash_in_hand: 0, diff: 0, deposit: 0, closing: 0
    };
    if (this.closingHistory && this.closingHistory.length > 0) {
      for (let row of this.closingHistory) {
        totals.opening += parseFloat(row.opening_balance || 0);
        totals.system += parseFloat(row.system_cash || 0);
        totals.expenses += parseFloat(row.todays_expenses || 0);
        totals.cash_in_hand += parseFloat(row.cash_in_hand || 0);
        totals.diff += parseFloat(row.difference || 0);
        totals.deposit += parseFloat(row.cash_deposit || 0);
        totals.closing += parseFloat(row.closing_balance || 0);
      }
    }
    return totals;
  }
  
  selectAdminClosing(row: any) {
    this.selectedAdminClosing = row;
  }
'''
content = content.replace("  // ---- Monthly Sales ----", admin_totals_logic + "\n  // ---- Monthly Sales ----")

with open('frontend/src/app/finance/finance.ts', 'w', encoding='utf-8') as f:
    f.write(content)
