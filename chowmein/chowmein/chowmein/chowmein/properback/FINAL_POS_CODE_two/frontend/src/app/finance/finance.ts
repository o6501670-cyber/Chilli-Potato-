import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-finance',
  imports: [CommonModule, FormsModule],
  templateUrl: './finance.html',
  styleUrl: './finance.css'
})
export class FinanceComponent implements OnInit {
  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);

  isOwner = false;
  permissions: any = {};
  centers: any[] = [];
  selectedFilterLocation: any = null;

  // Tab State
  activeMainTab = 'single';
  activeSingleTab = 'register';
  activeMultiTab = 'balances';
  activePettyCashTab = 'admin';
  editingPettyCash: any = null;

  // Date filters
  startDate = '';
  endDate = '';

  isLoading = false;
  isSaving = false;

  // ---- Register Summary ----
  registerSummaryData: any = null;

  // ---- Monthly Sales ----
  monthlySalesData: any[] = [];

  // ---- Detailed Revenues ----
  detailedRevenuesData: any[] = [];

  // ---- Refunds ----
  refundsData: any = null;

  // ---- Procurement ----
  procurementData: any = null;

  // ---- Multi Salon ----
  multiSalonData: any[] = [];
  multiStartDate = '';
  multiEndDate = '';

  // ---- Incentives ----
  incentivesData: any[] = [];
  incentiveStartDate = '';
  incentiveEndDate = '';
  incentivePercent = 5;

  // ---- Petty Cash & Shift ----
  pettyCashForm: any = { description: '', amount: '', voucher_number: '', comments: '' };
  pettyCashLogs: any[] = [];
  
  activeShift: any = null;
  shiftFloat: number = 0;
  shiftActualCash: number = 0;

  // ---- Daily Closing ----
  closingDate = new Date().toISOString().split('T')[0];
  noClosingForDate = true;
  closingData: any = {
    opening_balance: 0,
    days_collection: 0,
    todays_expenses: 0,
    cash_in_hand: '',
    cash_deposit: '',
    credit_card: '',
    upi: '',
    paytm: '',
    bharat_pe: '',
    cheque_netbanking: '',
    google_pay: '',
    phone_pe: '',
    nearbuy: '',
    other: '',
  };
  closingHistory: any[] = [];
  closingPaymentSummary: any = null;

  ngOnInit() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.permissions = user.permissions || {};
      } catch (e) {}
    }

    if (this.isOwner || this.permissions.finance?.register_summary?.read || this.permissions.finance?.monthly_sales?.read || this.permissions.finance?.detailed_revenues?.read || this.permissions.finance?.refunds?.read || this.permissions.finance?.procurement?.read) {
      this.activeMainTab = 'single';
      if (this.isOwner || this.permissions.finance?.register_summary?.read) {
        this.activeSingleTab = 'register';
      } else if (this.permissions.finance?.monthly_sales?.read) {
        this.activeSingleTab = 'monthly';
      } else if (this.permissions.finance?.detailed_revenues?.read) {
        this.activeSingleTab = 'detailed';
      } else if (this.permissions.finance?.refunds?.read) {
        this.activeSingleTab = 'refunds';
      } else if (this.permissions.finance?.procurement?.read) {
        this.activeSingleTab = 'procurement';
      }
    } else if (this.permissions.finance?.multi_salon?.read) {
      this.activeMainTab = 'multi';
    } else if (this.permissions.finance?.incentives?.read) {
      this.activeMainTab = 'incentives';
    } else if (this.permissions.finance?.pettycash?.read) {
      this.activeMainTab = 'pettycash';
    } else {
      this.activeMainTab = '';
    }

    // Default to last 30 days
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    this.endDate = today.toISOString().split('T')[0];
    this.startDate = thirtyDaysAgo.toISOString().split('T')[0];
    this.multiStartDate = this.startDate;
    this.multiEndDate = this.endDate;
    this.incentiveStartDate = this.startDate;
    this.incentiveEndDate = this.endDate;

    this.apiService.getCenters().subscribe((data: any) => {
      this.centers = Array.isArray(data) ? data : (data.results || []);
      if (!this.isOwner) {
        const userStr2 = localStorage.getItem('user');
        if (userStr2) {
          try {
            const user = JSON.parse(userStr2);
            this.selectedFilterLocation = user?.center_id || null;
          } catch (e) {}
        }
        if (this.centers.length > 0 && !this.centers.some((c:any) => c.id == this.selectedFilterLocation)) {
          this.selectedFilterLocation = this.centers[0].id;
        }
      }
      this.loadPettyCash();
      this.cdr.detectChanges();
    });
  }

  onLocationChange() {
    this.loadPettyCash();
    // Clear cached data when location changes
    this.registerSummaryData = null;
    this.monthlySalesData = [];
    this.detailedRevenuesData = [];
    this.refundsData = null;
    this.procurementData = null;
  }

  setMainTab(tab: string) {
    this.activeMainTab = tab;
    if (tab === 'pettycash') this.loadPettyCash();
    if (tab === 'multi') this.loadMultiSalonData();
    if (tab === 'incentives') this.loadIncentives();
  }

  setSingleTab(tab: string) {
    this.activeSingleTab = tab;
  }

  setMultiTab(tab: string) {
    this.activeMultiTab = tab;
  }

  setPettyCashTab(tab: string) {
    this.activePettyCashTab = tab;
    if (tab === 'admin') this.loadClosingHistory();
    if (this.activeMainTab === 'pettycash') {
      this.loadPettyCash();
      this.checkActiveShift();
      this.loadTodayClosingData();
    }
  }

  exportExcel() {
    let centerId = this.selectedFilterLocation === 'null' ? null : this.selectedFilterLocation;
    this.apiService.exportFinance(centerId, this.startDate, this.endDate).subscribe((blob: Blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance_export_${this.startDate}_${this.endDate}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    }, (err: any) => {
      console.error('Export failed', err);
      alert('Failed to export Excel.');
    });
  }

  loadRegisterSummary() {
  }

  getCenterId(): number | undefined {
    const v = this.selectedFilterLocation;
    if (!v || v === 'null' || v === null) return undefined;
    return typeof v === 'number' ? v : parseInt(v, 10);
  }

  // ---- Register Summary ----
  runRegisterSummary() {
    this.isLoading = true;
    this.apiService.getRegisterSummary(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: res => {
        this.registerSummaryData = res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  // ---- Monthly Sales ----
  runMonthlySales() {
    this.isLoading = true;
    this.apiService.getMonthlySales(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: res => {
        this.monthlySalesData = res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  // ---- Detailed Revenues ----
  detailedRevenuesPage = 1;
  detailedRevenuesPageSize = 100;
  detailedRevenuesTotal = 0;

  runDetailedRevenues() {
    this.isLoading = true;
    this.apiService.getDetailedRevenues(this.getCenterId(), this.startDate, this.endDate, this.detailedRevenuesPage, this.detailedRevenuesPageSize).subscribe({
      next: res => {
        this.detailedRevenuesData = res.results || res;
        this.detailedRevenuesTotal = res.count || 0;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  // ---- Refunds ----
  runRefunds() {
    this.isLoading = true;
    this.apiService.getFinanceRefunds(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: res => {
        this.refundsData = res.refunds || res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  // ---- Procurement ----
  runProcurement() {
    this.isLoading = true;
    this.apiService.getProcurementReport(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: res => {
        this.procurementData = res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  // ---- Incentives ----
  loadIncentives() {
    if (!this.incentiveStartDate || !this.incentiveEndDate) return;
    this.isLoading = true;
    this.apiService.getIncentiveReport(this.incentiveStartDate, this.incentiveEndDate, this.getCenterId()).subscribe({
      next: data => {
        this.incentivesData = data;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.isLoading = false; }
    });
  }

  getIncentiveForStaff(item: any): number {
    const rev = parseFloat(item.total_sales || 0);
    return parseFloat((rev * this.incentivePercent / 100).toFixed(2));
  }

  // ---- Multi Salon ----
  loadMultiSalonData() {
    this.isLoading = true;
    if (this.centers.length === 0) {
      this.isLoading = false;
      return;
    }
    
    const observables = this.centers.map(center => 
      this.apiService.getRegisterSummary(center.id, this.multiStartDate, this.multiEndDate)
    );

    forkJoin(observables).subscribe(results => {
      this.multiSalonData = results.map((res: any, index) => ({
        center_name: this.centers[index].display_name || this.centers[index].center_name,
        ...res
      }));
      this.isLoading = false;
      this.cdr.detectChanges();
    }, () => {
      this.isLoading = false;
    });
  }

  runMultiSalon() {
    this.loadMultiSalonData();
  }

  // ---- Petty Cash ----
  loadPettyCash() {
    const cid = this.getCenterId();
    if (!cid) return;
    this.apiService.getPettyCashEntries(cid).subscribe(res => {
      this.pettyCashLogs = res;
      this.cdr.detectChanges();
    });
  }

  submitPettyCash() {
    if (this.isSaving) return;
    const cid = this.getCenterId();
    if (!cid) return alert('Select a location first');
    if (!this.pettyCashForm.comments?.trim()) return alert('Comments are compulsory');
    if (!this.pettyCashForm.description?.trim()) return alert('Description is required');
    if (!this.pettyCashForm.amount) return alert('Amount is required');

    this.isSaving = true;
    const data = { ...this.pettyCashForm, center: cid };

    if (this.editingPettyCash) {
      // Update existing entry
      this.apiService.updatePettyCashEntry(this.editingPettyCash.id, data).subscribe({
        next: () => {
          this.pettyCashForm = { description: '', amount: '', voucher_number: '', comments: '' };
          this.editingPettyCash = null;
          this.isSaving = false;
          this.loadPettyCash();
        },
        error: () => this.isSaving = false
      });
    } else {
      this.apiService.createPettyCashEntry(data).subscribe({
        next: () => {
          this.pettyCashForm = { description: '', amount: '', voucher_number: '', comments: '' };
          this.isSaving = false;
          this.loadPettyCash();
        },
        error: () => this.isSaving = false
      });
    }
  }

  editPettyCash(log: any) {
    this.editingPettyCash = log;
    this.pettyCashForm = {
      description: log.description,
      amount: log.amount,
      voucher_number: log.voucher_number || '',
      comments: log.comments || '',
    };
    // Scroll to top of form
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  get todaysExpenses(): number {
    const today = new Date().toISOString().split('T')[0];
    return this.pettyCashLogs
      .filter(l => l.date && l.date.startsWith(today))
      .reduce((sum, l) => sum + parseFloat(l.amount || 0), 0);
  }

  // ---- Daily Closing ----
  loadClosingHistory() {
    const cid = this.getCenterId();
    if (!cid) return;
    this.apiService.getDailyClosings(cid).subscribe(data => {
      this.closingHistory = data;
      this.cdr.detectChanges();
    });
  }

  loadTodayClosingData() {
    const cid = this.getCenterId();
    if (!cid) return;

    // Check if a closing already exists for this date
    this.apiService.getDailyClosings(cid, this.closingDate).subscribe(existing => {
      if (existing && existing.length > 0) {
        this.noClosingForDate = false;
        const saved = existing[0];
        this.closingData = { ...this.closingData, ...saved };
      } else {
        this.noClosingForDate = true;
      }
      this.cdr.detectChanges();
    });

    // Load today's cash collection from billing
    this.apiService.getRegisterSummary(cid, this.closingDate, this.closingDate).subscribe(res => {
      const cash = res?.payment_methods?.cash?.amount || 0;
      this.closingData.days_collection = cash;
      this.closingData.todays_expenses = this.todaysExpenses;
      this.closingPaymentSummary = res?.payment_methods;
      this.cdr.detectChanges();
    });
  }

  get expectedCash(): number {
    return (parseFloat(this.closingData.opening_balance || 0) +
            parseFloat(this.closingData.days_collection || 0) -
            parseFloat(this.closingData.todays_expenses || 0));
  }

  get cashDifference(): number {
    const cashInHand = parseFloat(this.closingData.cash_in_hand || 0);
    return cashInHand - this.expectedCash;
  }

  get closingBalance(): number {
    return this.expectedCash - parseFloat(this.closingData.cash_deposit || 0);
  }

  onClosingDateChange() {
    this.noClosingForDate = true;
    this.loadTodayClosingData();
  }

  // ---- SHIFT MANAGEMENT ----
  checkActiveShift() {
    const cid = this.getCenterId();
    if (!cid) return;
    this.apiService.getShifts(cid, 'Open').subscribe(res => {
      if (res && res.length > 0) {
        this.activeShift = res[0];
        this.closingData.opening_balance = this.activeShift.starting_float;
      } else {
        this.activeShift = null;
      }
      this.cdr.detectChanges();
    });
  }

  openShift() {
    if (this.isSaving) return;
    const cid = this.getCenterId();
    if (!cid) return alert('Select a location first');
    if (this.shiftFloat < 0) return alert('Float cannot be negative');
    
    this.isSaving = true;
    this.apiService.openShift(cid, this.shiftFloat).subscribe({
      next: () => {
        alert('Register Opened Successfully!');
        this.isSaving = false;
        this.checkActiveShift();
      },
      error: () => this.isSaving = false
    });
  }

  closeShift() {
    if (!this.activeShift || this.isSaving) return;
    this.isSaving = true;
    this.apiService.closeShift(this.activeShift.id, this.shiftActualCash, this.expectedCash).subscribe({
      next: () => {
        alert(`Register Closed! Variance: Rs. ${this.shiftActualCash - this.expectedCash}`);
        // Save the daily closing as well for historical reports
        this.submitClosing();
        this.checkActiveShift();
        this.isSaving = false;
      },
      error: () => this.isSaving = false
    });
  }

  submitClosing() {
    if (this.isSaving && !this.activeShift) return; // If called from closeShift, isSaving is already true. Otherwise, check.
    if (!this.activeShift) this.isSaving = true;
    
    const cid = this.getCenterId();
    if (!cid) {
      if (!this.activeShift) this.isSaving = false;
      return alert('Select a location first');
    }
    const data = {
      center: cid,
      date: this.closingDate,
      opening_balance: this.closingData.opening_balance || 0,
      cash_in_hand: this.closingData.cash_in_hand || 0,
      todays_expenses: this.todaysExpenses,
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
      next: () => {
        this.noClosingForDate = false;
        alert('Closing submitted successfully!');
        if (!this.activeShift) this.isSaving = false;
        this.loadClosingHistory();
      },
      error: (err) => {
        const msg = err?.error?.detail || err?.error?.non_field_errors?.[0] || 'Failed to submit closing.';
        alert(msg);
        if (!this.activeShift) this.isSaving = false;
      }
    });
  }

  formatCurrency(val: number): string {
    return new Intl.NumberFormat('en-IN').format(val || 0);
  }

  get totalIncentiveAmount(): number {
    return this.incentivesData.reduce((sum, i) => sum + (parseFloat(i.incentive_amount) || 0), 0);
  }

  get selectedCenterName(): string {
    const cid = this.getCenterId();
    if (!cid) return 'All Locations';
    const c = this.centers.find(x => x.id === cid);
    return c ? (c.display_name || c.center_name) : 'Selected Center';
  }
}
