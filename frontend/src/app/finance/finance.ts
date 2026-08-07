import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-finance',
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './finance.html',
  styleUrl: './finance.css'
})
export class FinanceComponent implements OnInit {
  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);

  isOwner = false;
  hasGlobalAccess = false;
  permissions: any = {};
  centers: any[] = [];
  selectedFilterLocation: any = null;

  currentRange: string = ''; // Track active date pill

  // Tab State
  activeMainTab = 'single';
  activeSingleTab = 'register';
  activeMultiTab = 'balances';
  activePettyCashTab = 'admin';
  activeClosingTab = 'admin';
  selectedAdminClosing: any = null;
  parseFloat = parseFloat;
  editingPettyCash: any = null;
  targetMultiplier = 2.5;

  // Date filters
  startDate = '';
  endDate = '';
  closingStartDate = '';
  closingEndDate = '';

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
  incentiveFrequency = 'monthly';
  incentiveSearchQuery = '';
  selectedStaffBreakdown: any = null;
  showStaffBreakdownModal = false;
  incentiveConfigs: any[] = [];
  showIncentiveConfigModal = false;
  currentIncentiveConfig: any = null;

  // ---- Manage Rules (Incentive Structure) ----
  manageViewMode: 'monthly' | 'daily' = 'monthly';
  manageDailySubTab: 'business_slabs' | 'service_addons_targets' = 'business_slabs';
  incentiveRules: any[] = [];
  manageCategoryFilter = 'all';
  manageFrequencyFilter = 'all';
  manageCenterFilter: any = null;
  manageSearchQuery = '';
  showRuleModal = false;
  showDuplicateModal = false;
  selectedRuleForDuplicate: any = null;
  duplicateTargetCenterId: any = null;
  currentRule: any = {
    name: '',
    category: 'services',
    frequency: 'monthly',
    center: null,
    applicable_role: 'all',
    rule_type: 'multiple',
    flat_percent: 0,
    flat_amount: 0,
    tiers: [],
    slabs: [],
    effective_from: new Date().toISOString().split('T')[0],
    effective_to: null,
    description: '',
    is_active: true
  };

  loadIncentiveRules() {
    this.isLoading = true;
    const cat = this.manageCategoryFilter !== 'all' ? this.manageCategoryFilter : undefined;
    const freq = this.manageViewMode === 'daily' ? 'daily' : (this.manageFrequencyFilter !== 'all' ? this.manageFrequencyFilter : undefined);
    const cid = this.manageCenterFilter ? this.manageCenterFilter : undefined;
    this.apiService.getIncentiveRules(cid, cat, freq).subscribe({
      next: res => {
        this.incentiveRules = res || [];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  getFilteredRules(): any[] {
    if (!this.incentiveRules) return [];
    return this.incentiveRules.filter(r => {
      if (this.manageViewMode === 'monthly') {
        if (r.category === 'daily_business' || r.category === 'service_target') return false;
        if (r.frequency === 'daily') return false;
      } else if (this.manageViewMode === 'daily') {
        if (this.manageDailySubTab === 'business_slabs') {
          if (r.category !== 'daily_business') return false;
        } else {
          if (r.category !== 'service_addon' && r.category !== 'service_target') return false;
        }
      }

      if (this.manageCategoryFilter !== 'all' && r.category !== this.manageCategoryFilter) return false;
      if (this.manageCenterFilter && r.center !== this.manageCenterFilter) return false;
      if (this.manageSearchQuery?.trim()) {
        const q = this.manageSearchQuery.toLowerCase().trim();
        const matchName = r.name?.toLowerCase().includes(q);
        const matchRole = r.applicable_role?.toLowerCase().includes(q);
        const matchCenter = r.center_name?.toLowerCase().includes(q);
        if (!matchName && !matchRole && !matchCenter) return false;
      }
      return true;
    });
  }

  getDailyBusinessRules(roleCategory?: string): any[] {
    if (!this.incentiveRules) return [];
    return this.incentiveRules.filter(r => {
      if (r.category !== 'daily_business') return false;
      if (roleCategory && r.applicable_role !== roleCategory) return false;
      return true;
    });
  }

  getServiceAddonRules(): any[] {
    if (!this.incentiveRules) return [];
    return this.incentiveRules.filter(r => r.category === 'service_addon');
  }

  getServiceTargetRules(): any[] {
    if (!this.incentiveRules) return [];
    return this.incentiveRules.filter(r => r.category === 'service_target');
  }

  openCreateRuleModal(category: string = 'services') {
    const today = new Date().toISOString().split('T')[0];
    const freq = this.manageViewMode === 'daily' ? 'daily' : 'monthly';
    
    let defaultRuleType = 'multiple';
    let defaultTiers: any[] = [];
    let defaultSlabs: any[] = [];
    let role = 'all';

    if (category === 'daily_business') {
      defaultRuleType = 'slab';
      role = 'lhds_uhds';
      defaultTiers = [
        { min_amount: 8000, bonus_type: 'flat', bonus_amount: 350, bonus_percent: 0 },
        { min_amount: 10000, bonus_type: 'flat', bonus_amount: 450, bonus_percent: 0 },
        { min_amount: 15000, bonus_type: 'flat', bonus_amount: 700, bonus_percent: 0 },
        { min_amount: 20000, bonus_type: 'percentage', bonus_amount: 0, bonus_percent: 5.0 }
      ];
    } else if (category === 'service_addon') {
      defaultRuleType = 'slab';
      role = 'pedicurist_k_ambassador';
      defaultTiers = [
        { service_name: 'Fusio Dose / Scrub', match_keyword: 'fusio', worth_amount: 0, incentive_amount: 100 },
        { service_name: 'Express Ritual (Fusio Dose +)', match_keyword: 'express ritual', worth_amount: 3600, incentive_amount: 150 },
        { service_name: 'Experience Ritual', match_keyword: 'experience ritual', worth_amount: 4500, incentive_amount: 200 },
        { service_name: 'K Premiere Ritual', match_keyword: 'premiere ritual', worth_amount: 5500, incentive_amount: 250 },
        { service_name: 'Chronologist', match_keyword: 'chronologist', worth_amount: 6000, incentive_amount: 300 },
        { service_name: 'Be Spoke Signature Ritual', match_keyword: 'be spoke', worth_amount: 7000, incentive_amount: 400 },
        { service_name: 'Alga Exquis Mani/Pedi', match_keyword: 'alga exquis', worth_amount: 2500, incentive_amount: 200 },
        { service_name: 'Algae Mani/Pedi', match_keyword: 'algae', worth_amount: 1800, incentive_amount: 150 },
        { service_name: 'Footlogix / Alga Fondu Mani/Pedi', match_keyword: 'footlogix', worth_amount: 0, incentive_amount: 50 },
        { service_name: 'Absolute Repair Molecular', match_keyword: 'absolute repair', worth_amount: 2500, incentive_amount: 100 }
      ];
    } else if (category === 'service_target') {
      defaultRuleType = 'target';
      role = 'pedicurist_k_ambassador';
      defaultTiers = [
        { service_name: 'Rituals Target', match_keyword: 'ritual', target_count: 5, reward_amount: 500 },
        { service_name: 'Mani / Pedi Target', match_keyword: 'mani', target_count: 8, reward_amount: 400 }
      ];
    } else if (category === 'value_cards') {
      defaultRuleType = 'slabs';
      defaultSlabs = [
        { name: 'Elite', min_amount: 11000, max_amount: 14000, incentive_amount: 200 },
        { name: 'Luxe', min_amount: 21000, max_amount: 30000, incentive_amount: 400 },
        { name: 'Prestige', min_amount: 51000, max_amount: 80000, incentive_amount: 600 },
        { name: 'Infinity', min_amount: 111000, max_amount: 180000, incentive_amount: 800 }
      ];
    } else {
      defaultRuleType = 'multiple';
      defaultTiers = [
        { min_multiple: 5.0, max_multiple: 5.99, incentive_percent: 3.0 },
        { min_multiple: 6.0, max_multiple: 6.99, incentive_percent: 6.0 },
        { min_multiple: 7.0, max_multiple: null, incentive_percent: 7.0 }
      ];
    }

    this.currentRule = {
      name: '',
      category: category,
      frequency: freq,
      center: this.getCenterId() || null,
      applicable_role: role,
      rule_type: defaultRuleType,
      flat_percent: 5,
      flat_amount: 200,
      tiers: defaultTiers,
      slabs: defaultSlabs,
      effective_from: today,
      effective_to: null,
      description: '',
      is_active: true
    };
    this.showRuleModal = true;
  }

  openCreateDailyBusinessModal(role: string = 'lhds_uhds') {
    this.openCreateRuleModal('daily_business');
    this.currentRule.applicable_role = role;
    if (role === 'lhds_uhds') {
      this.currentRule.name = 'LHDS / UHDS Daily Sales Slabs';
      this.currentRule.tiers = [
        { min_amount: 8000, bonus_type: 'flat', bonus_amount: 350, bonus_percent: 0 },
        { min_amount: 10000, bonus_type: 'flat', bonus_amount: 450, bonus_percent: 0 },
        { min_amount: 15000, bonus_type: 'flat', bonus_amount: 700, bonus_percent: 0 },
        { min_amount: 20000, bonus_type: 'percentage', bonus_amount: 0, bonus_percent: 5.0 }
      ];
    } else {
      this.currentRule.name = 'MHDS / Beauty Daily Sales Slabs';
      this.currentRule.tiers = [
        { min_amount: 6000, bonus_type: 'flat', bonus_amount: 200, bonus_percent: 0 },
        { min_amount: 8000, bonus_type: 'flat', bonus_amount: 350, bonus_percent: 0 },
        { min_amount: 10000, bonus_type: 'flat', bonus_amount: 450, bonus_percent: 0 },
        { min_amount: 15000, bonus_type: 'percentage', bonus_amount: 0, bonus_percent: 5.0 }
      ];
    }
  }

  openEditRuleModal(rule: any) {
    this.currentRule = JSON.parse(JSON.stringify(rule));
    if (!this.currentRule.tiers) this.currentRule.tiers = [];
    if (!this.currentRule.slabs) this.currentRule.slabs = [];
    
    // Reverse-map tiers to slabs for the UI builder
    if (this.currentRule.category === 'daily_business' && this.currentRule.tiers.length > 0) {
      this.currentRule.slabs = this.currentRule.tiers.map((t: any) => ({
        min_amount: t.min_amount,
        type: t.bonus_type === 'percentage' ? 'percent' : 'flat',
        incentive_amount: t.bonus_type === 'percentage' ? t.bonus_percent : t.bonus_amount
      }));
    } else if (this.currentRule.category === 'service_addon' && this.currentRule.tiers.length > 0) {
      this.currentRule.slabs = this.currentRule.tiers.map((t: any) => ({
        name: t.service_name,
        keyword: t.match_keyword,
        worth: t.worth_amount,
        incentive_amount: t.incentive_amount
      }));
    } else if (this.currentRule.category === 'service_target' && this.currentRule.tiers.length > 0) {
      this.currentRule.slabs = this.currentRule.tiers.map((t: any) => ({
        name: t.service_name,
        keyword: t.match_keyword,
        min_amount: t.target_count,
        incentive_amount: t.reward_amount
      }));
    }

    this.showRuleModal = true;
  }

  openDuplicateRuleModal(rule: any) {
    this.selectedRuleForDuplicate = rule;
    this.duplicateTargetCenterId = null;
    this.showDuplicateModal = true;
  }

  confirmDuplicateRule() {
    if (!this.selectedRuleForDuplicate) return;
    this.apiService.duplicateIncentiveRule(this.selectedRuleForDuplicate.id, this.duplicateTargetCenterId).subscribe({
      next: () => {
        this.showDuplicateModal = false;
        this.selectedRuleForDuplicate = null;
        this.loadIncentiveRules();
        alert('Rule duplicated successfully with clean date-isolation!');
      },
      error: (err) => alert(err.error?.detail || 'Error duplicating rule')
    });
  }

  saveRule() {
    if (!this.currentRule.name?.trim()) {
      alert('Please enter a descriptive Rule Name.');
      return;
    }
    if (!this.currentRule.effective_from) {
      alert('Please select an Effective From date.');
      return;
    }
    if (this.currentRule.effective_to && this.currentRule.effective_from > this.currentRule.effective_to) {
      alert('Effective To date cannot be earlier than Effective From date.');
      return;
    }

    const payload = { ...this.currentRule };
    // Synchronize tiers/slabs based on rule_type or category
    if (payload.rule_type === 'slabs' && payload.slabs?.length > 0) {
      payload.tiers = payload.slabs;
    } else if (payload.category === 'daily_business' && payload.slabs?.length > 0) {
      // Map inline builder slabs → backend tiers format
      payload.tiers = payload.slabs.map((s: any) => ({
        min_amount: s.min_amount || 0,
        bonus_type: s.type === 'percent' ? 'percentage' : 'flat',
        bonus_amount: s.type !== 'percent' ? (s.incentive_amount || 0) : 0,
        bonus_percent: s.type === 'percent' ? (s.incentive_amount || 0) : 0
      }));
    } else if (payload.category === 'service_addon' && payload.slabs?.length > 0) {
      // Map inline builder slabs → backend tiers format
      payload.tiers = payload.slabs.map((s: any) => ({
        service_name: s.name || '',
        match_keyword: s.keyword || '',
        worth_amount: s.worth || 0,
        incentive_amount: s.incentive_amount || 0
      }));
    } else if (payload.category === 'service_target' && payload.slabs?.length > 0) {
      // Map inline builder slabs → backend tiers format
      payload.tiers = payload.slabs.map((s: any) => ({
        service_name: s.name || '',
        match_keyword: s.keyword || '',
        target_count: s.min_amount || 1,
        reward_amount: s.incentive_amount || 0
      }));
    }

    if (payload.id) {
      this.apiService.updateIncentiveRule(payload.id, payload).subscribe({
        next: () => {
          this.showRuleModal = false;
          this.loadIncentiveRules();
          alert('Incentive Rule updated successfully!');
        },
        error: (err) => alert(err.error?.detail || JSON.stringify(err.error) || 'Error updating rule')
      });
    } else {
      this.apiService.createIncentiveRule(payload).subscribe({
        next: () => {
          this.showRuleModal = false;
          this.loadIncentiveRules();
          alert('Incentive Rule created successfully!');
        },
        error: (err) => alert(err.error?.detail || JSON.stringify(err.error) || 'Error creating rule')
      });
    }
  }

  toggleRuleStatus(rule: any) {
    const updated = { ...rule, is_active: !rule.is_active };
    this.apiService.updateIncentiveRule(rule.id, updated).subscribe({
      next: () => {
        rule.is_active = !rule.is_active;
        this.cdr.detectChanges();
      },
      error: (err) => alert(err.error?.detail || 'Failed to toggle status')
    });
  }

  deleteRule(id: number) {
    if (!confirm('Are you sure you want to delete this rule? Historical calculations prior to today will remain unaffected.')) return;
    this.apiService.deleteIncentiveRule(id).subscribe({
      next: () => this.loadIncentiveRules(),
      error: (err) => alert(err.error?.detail || 'Error deleting rule')
    });
  }

  addRuleTier() {
    if (!this.currentRule.tiers) this.currentRule.tiers = [];
    if (this.currentRule.category === 'daily_business') {
      this.currentRule.tiers.push({ min_amount: 0, bonus_type: 'flat', bonus_amount: 0, bonus_percent: 0 });
    } else if (this.currentRule.category === 'service_addon') {
      this.currentRule.tiers.push({ service_name: '', match_keyword: '', worth_amount: 0, incentive_amount: 0 });
    } else if (this.currentRule.category === 'service_target') {
      this.currentRule.tiers.push({ service_name: '', match_keyword: '', target_count: 1, reward_amount: 0 });
    } else {
      this.currentRule.tiers.push({ min_multiple: 0, max_multiple: null, incentive_percent: 0 });
    }
  }

  removeRuleTier(index: number) {
    this.currentRule.tiers.splice(index, 1);
  }

  addRuleSlab() {
    if (!this.currentRule.slabs) this.currentRule.slabs = [];
    this.currentRule.slabs.push({ name: '', min_amount: 0, max_amount: 0, incentive_amount: 0 });
  }

  removeRuleSlab(index: number) {
    this.currentRule.slabs.splice(index, 1);
  }

  // Daily Business Slabs builder (used by inline modal table for category=daily_business)
  addDailyBusinessSlab() {
    if (!this.currentRule.slabs) this.currentRule.slabs = [];
    this.currentRule.slabs.push({ min_amount: 0, type: 'flat', incentive_amount: 0 });
  }

  // Service Add-on builder (used by inline modal table for category=service_addon)
  addServiceAddonItem() {
    if (!this.currentRule.slabs) this.currentRule.slabs = [];
    this.currentRule.slabs.push({ name: '', keyword: '', worth: 0, incentive_amount: 0 });
  }

  // Service Volume Target builder (used by inline modal table for category=service_target)
  addServiceTargetItem() {
    if (!this.currentRule.slabs) this.currentRule.slabs = [];
    this.currentRule.slabs.push({ name: '', keyword: '', min_amount: 1, incentive_amount: 0 });
  }

  onCategoryChangeInModal() {
    if (this.currentRule.category === 'value_cards') {
      this.currentRule.rule_type = 'slabs';
      if (!this.currentRule.slabs || this.currentRule.slabs.length === 0) {
        this.currentRule.slabs = [
          { name: 'Elite', min_amount: 11000, max_amount: 14000, incentive_amount: 200 },
          { name: 'Luxe', min_amount: 21000, max_amount: 30000, incentive_amount: 400 },
          { name: 'Prestige', min_amount: 51000, max_amount: 80000, incentive_amount: 600 },
          { name: 'Infinity', min_amount: 111000, max_amount: 180000, incentive_amount: 800 }
        ];
      }
    } else if (this.currentRule.category === 'daily_business') {
      this.currentRule.rule_type = 'slab';
      this.currentRule.frequency = 'daily';
      if (!this.currentRule.tiers || this.currentRule.tiers.length === 0) {
        this.currentRule.tiers = [
          { min_amount: 8000, bonus_type: 'flat', bonus_amount: 350, bonus_percent: 0 },
          { min_amount: 10000, bonus_type: 'flat', bonus_amount: 450, bonus_percent: 0 },
          { min_amount: 15000, bonus_type: 'flat', bonus_amount: 700, bonus_percent: 0 },
          { min_amount: 20000, bonus_type: 'percentage', bonus_amount: 0, bonus_percent: 5.0 }
        ];
      }
    } else if (this.currentRule.category === 'service_addon') {
      this.currentRule.rule_type = 'slab';
      this.currentRule.frequency = 'daily';
      if (!this.currentRule.tiers || this.currentRule.tiers.length === 0) {
        this.currentRule.tiers = [
          { service_name: 'Fusio Dose / Scrub', match_keyword: 'fusio', worth_amount: 0, incentive_amount: 100 },
          { service_name: 'Express Ritual (Fusio Dose +)', match_keyword: 'express ritual', worth_amount: 3600, incentive_amount: 150 }
        ];
      }
    } else if (this.currentRule.category === 'service_target') {
      this.currentRule.rule_type = 'target';
      this.currentRule.frequency = 'daily';
      if (!this.currentRule.tiers || this.currentRule.tiers.length === 0) {
        this.currentRule.tiers = [
          { service_name: 'Rituals Target', match_keyword: 'ritual', target_count: 5, reward_amount: 500 }
        ];
      }
    } else if (this.currentRule.category === 'services' || this.currentRule.category === 'products') {
      this.currentRule.rule_type = 'multiple';
      if (!this.currentRule.tiers || this.currentRule.tiers.length === 0) {
        this.currentRule.tiers = [
          { min_multiple: 5.0, max_multiple: 5.99, incentive_percent: 3.0 },
          { min_multiple: 6.0, max_multiple: 6.99, incentive_percent: 6.0 },
          { min_multiple: 7.0, max_multiple: null, incentive_percent: 7.0 }
        ];
      }
    }
  }

  getCategoryName(cat: string): string {
    const map: any = {
      'services': 'Services',
      'products': 'Products',
      'value_cards': 'Value Cards',
      'daily_business': 'Daily Business Slabs',
      'service_addon': 'Service Add-on Bonuses',
      'service_target': 'Service Volume Targets'
    };
    return map[cat] || cat;
  }

  getCategoryIcon(cat: string): string {
    const map: any = {
      'services': '✂️',
      'products': '🧴',
      'value_cards': '💳',
      'daily_business': '⚡',
      'service_addon': '✨',
      'service_target': '🎯'
    };
    return map[cat] || '⚙️';
  }
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
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
        this.permissions = user.permissions || {};
      } catch (e) { }
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

    // Default to this month (more relevant than past 30 days)
    const today = new Date();
    const tzOffset = today.getTimezoneOffset() * 60000;
    const localToday = new Date(today.getTime() - tzOffset);
    const y = today.getFullYear();
    const m = today.getMonth();
    const thisMonthStart = `${y}-${String(m + 1).padStart(2, '0')}-01`;
    const todayStr = localToday.toISOString().split('T')[0];
    
    this.startDate = thisMonthStart;
    this.endDate = todayStr;
    this.multiStartDate = thisMonthStart;
    this.multiEndDate = todayStr;
    this.incentiveStartDate = thisMonthStart;
    this.incentiveEndDate = todayStr;
    this.closingStartDate = thisMonthStart;
    this.closingEndDate = todayStr;
    this.currentRange = 'thisMonth'; // Set default fast-pill to "This Month"

    this.apiService.getCenters().subscribe((data: any) => {
      this.centers = Array.isArray(data) ? data : (data.results || []);
      if (!this.isOwner) {
        const userStr2 = localStorage.getItem('user');
        if (userStr2) {
          try {
            const user = JSON.parse(userStr2);
            this.selectedFilterLocation = user?.center_id || null;
          } catch (e) { }
        }
        if (this.centers.length > 0 && !this.centers.some((c: any) => c.id == this.selectedFilterLocation)) {
          this.selectedFilterLocation = this.centers[0].id;
        }
      }
      // Auto-load data for the active tab once centers are known
      if (this.activeMainTab === 'single') {
        this.setSingleTab(this.activeSingleTab);
      } else if (this.activeMainTab === 'pettycash') {
        this.loadPettyCash();
        this.loadClosingHistory();
        this.checkActiveShift();
        this.loadTodayClosingData();
      } else if (this.activeMainTab === 'multi') {
        this.loadMultiSalonData();
      } else if (this.activeMainTab === 'incentives') {
        this.loadIncentives();
      } else {
        this.loadPettyCash();
      }
      this.cdr.detectChanges();
    });
  }

  onLocationChange() {
    this.refreshCurrentTab();
  }

  setDateRange(range: string) {
    this.currentRange = range;
    const today = new Date();
    const y = today.getFullYear();
    const m = today.getMonth();
    const d = today.getDate();

    let start = '';
    let end = '';

    if (range === 'thisMonth') {
      start = `${y}-${String(m + 1).padStart(2, '0')}-01`;
      end = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    } else if (range === 'past3Months') {
      const past = new Date(y, m - 2, 1);
      start = `${past.getFullYear()}-${String(past.getMonth() + 1).padStart(2, '0')}-01`;
      end = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    } else if (range === 'past6Months') {
      const past = new Date(y, m - 5, 1);
      start = `${past.getFullYear()}-${String(past.getMonth() + 1).padStart(2, '0')}-01`;
      end = `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    }

    if (this.activeMainTab === 'single' || this.activeMainTab === 'pettycash') {
      this.startDate = start;
      this.endDate = end;
      this.onApplyFilter();
    } else if (this.activeMainTab === 'multi') {
      this.multiStartDate = start;
      this.multiEndDate = end;
      this.loadMultiSalonData();
    } else if (this.activeMainTab === 'incentives') {
      this.incentiveStartDate = start;
      this.incentiveEndDate = end;
      this.loadIncentives();
    }
  }

  refreshCurrentTab() {
    this.clearSingleTabData();
    this.pettyCashLogs = [];
    // Reload data for the new location
    if (this.activeMainTab === 'single') {
      this.setSingleTab(this.activeSingleTab);
    } else if (this.activeMainTab === 'pettycash') {
      this.loadPettyCash();
      this.loadClosingHistory();
    } else if (this.activeMainTab === 'multi') {
      this.loadMultiSalonData();
    } else if (this.activeMainTab === 'incentives') {
      this.loadIncentives();
    }
  }

  onApplyFilter() {
    if (this.activeMainTab === 'pettycash') {
      this.loadPettyCash();
      this.checkActiveShift();
      this.loadTodayClosingData();
    } else if (this.activeMainTab === 'single') {
      this.clearSingleTabData();
      this.setSingleTab(this.activeSingleTab);
    } else if (this.activeMainTab === 'manage') {
      this.loadIncentiveRules();
    } else if (this.activeMainTab === 'incentives') {
      this.loadIncentives();
    }
  }

  setMainTab(tab: string) {
    this.activeMainTab = tab;
    if (tab === 'single') {
      // Clear stale data and load the active sub-tab immediately
      this.clearSingleTabData();
      this.setSingleTab(this.activeSingleTab);
    }
    if (tab === 'pettycash') {
      this.loadPettyCash();
      this.loadClosingHistory();
    }
    if (tab === 'multi') this.loadMultiSalonData();
    if (tab === 'incentives') {
      this.resetIncentiveDates();
      this.loadIncentives();
    }
    if (tab === 'manage') this.loadIncentiveRules();
  }

  setClosingTab(tab: string) {
    this.activeClosingTab = tab;
  }

  selectAdminClosing(row: any) {
    this.selectedAdminClosing = row;
  }

  exportClosingHistory() {
    alert("Export functionality coming soon");
  }

  setSingleTab(tab: string) {
    this.activeSingleTab = tab;
    if (tab === 'register') this.runRegisterSummary();
    else if (tab === 'monthly') this.runMonthlySales();
    else if (tab === 'detailed') this.runDetailedRevenues();
    else if (tab === 'refunds') this.runRefunds();
    else if (tab === 'procurement') this.runProcurement();
  }

  onDateChange() {
    // Only fire if both dates are fully entered (YYYY-MM-DD = 10 chars)
    if (!this.startDate || !this.endDate || this.startDate.length < 10 || this.endDate.length < 10) return;
    // Sanity check: start must not be after end
    if (this.startDate > this.endDate) return;

    if (this.activeMainTab === 'single') {
      // Clear stale data immediately so user sees loading state, not stale data
      this.clearSingleTabData();
      this.setSingleTab(this.activeSingleTab);
    } else if (this.activeMainTab === 'pettycash') {
      this.loadPettyCash();
      this.checkActiveShift();
      this.loadTodayClosingData();
    } else if (this.activeMainTab === 'multi') {
      this.multiStartDate = this.startDate;
      this.multiEndDate = this.endDate;
      this.loadMultiSalonData();
    } else if (this.activeMainTab === 'incentives') {
      this.incentiveStartDate = this.startDate;
      this.incentiveEndDate = this.endDate;
      this.loadIncentives();
    }
  }

  clearSingleTabData() {
    this.registerSummaryData = null;
    this.monthlySalesData = [];
    this.detailedRevenuesData = [];
    this.refundsData = null;
    this.procurementData = null;
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
    this.registerSummaryData = null;
    this.cdr.detectChanges();
    this.apiService.getRegisterSummary(this.getCenterId(), this.startDate, this.endDate).subscribe({
      next: res => {
        this.registerSummaryData = res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('[Finance] Register summary error:', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  // ---- Monthly Sales ----
  runMonthlySales() {
    this.isLoading = true;
    this.monthlySalesData = [];
    this.cdr.detectChanges();
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
      next: (res) => {
        this.refundsData = res;
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
      error: () => { 
        this.isLoading = false; 
      }
    });
  }

  exportPdfMulti() {
    // Not implemented
  }

  getTargetColor(percentage: number | string): string {
    const p = typeof percentage === 'string' ? parseFloat(percentage) : percentage;
    if (isNaN(p)) return '#ef4444';
    if (p >= 100) return '#10b981'; // Emerald Green
    if (p >= 80) return '#0ea5e9'; // Light Blue
    if (p >= 65) return '#b45309'; // Brown/Gold
    if (p >= 50) return '#f97316'; // Orange
    return '#ef4444'; // Red
  }

  getTrendColor(current: number | string, previous: number | string | undefined, invert: boolean = false): string {
    if (previous === undefined || previous === null || previous === '') return '';
    const curr = typeof current === 'string' ? parseFloat(current.replace(/,/g, '')) : current;
    const prev = typeof previous === 'string' ? parseFloat(previous.replace(/,/g, '')) : previous;
    if (isNaN(curr) || isNaN(prev)) return '';
    
    if (curr > prev) return invert ? '#ef4444' : '#10b981'; // Green (or Red if inverted)
    if (curr < prev) return invert ? '#10b981' : '#ef4444'; // Red (or Green if inverted)
    return ''; // Equal
  }

  // ---- Incentives (Upgraded Dashboard & Engine) ----
  formatDateLocal(d: Date): string {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  resetIncentiveDates() {
    const now = new Date();
    if (this.incentiveFrequency === 'monthly') {
      const year = now.getFullYear();
      const month = now.getMonth();
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      this.incentiveStartDate = this.formatDateLocal(firstDay);
      this.incentiveEndDate = this.formatDateLocal(lastDay);
    } else {
      const todayStr = this.formatDateLocal(now);
      this.incentiveStartDate = todayStr;
      this.incentiveEndDate = todayStr;
    }
  }

  loadIncentives() {
    if (!this.incentiveStartDate || !this.incentiveEndDate) {
      this.resetIncentiveDates();
    }
    this.isLoading = true;
    this.apiService.getIncentiveReport(
      this.incentiveStartDate,
      this.incentiveEndDate,
      this.getCenterId() || undefined,
      this.incentiveFrequency
    ).subscribe({
      next: data => {
        this.incentivesData = data || [];
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  onIncentiveFrequencyChange(freq: string) {
    this.incentiveFrequency = freq;
    this.resetIncentiveDates();
    this.loadIncentives();
  }

  getFilteredIncentives(): any[] {
    if (!this.incentivesData) return [];
    if (!this.incentiveSearchQuery?.trim()) return this.incentivesData;
    const q = this.incentiveSearchQuery.toLowerCase().trim();
    return this.incentivesData.filter(item =>
      (item.staff_name && item.staff_name.toLowerCase().includes(q)) ||
      (item.role && item.role.toLowerCase().includes(q)) ||
      (item.center && item.center.toLowerCase().includes(q))
    );
  }

  openStaffBreakdown(staff: any) {
    this.selectedStaffBreakdown = staff;
    this.showStaffBreakdownModal = true;
  }

  closeStaffBreakdown() {
    this.selectedStaffBreakdown = null;
    this.showStaffBreakdownModal = false;
  }

  getTotalSalesRevenue(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.revenue) || 0), 0);
  }

  getTotalIncentivePayout(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.incentive_amount) || 0), 0);
  }

  getTotalCardsSold(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (curr.cards_count || (curr.card_slabs?.length || 0)), 0);
  }

  getTotalCardsIncentive(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.cards_incentive) || 0), 0);
  }

  getTotalProductIncentive(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.products_incentive) || 0), 0);
  }

  getTotalServiceIncentive(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.services_incentive) || 0), 0);
  }

  // Daily-mode specific totals
  getTotalDailyBonus(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.daily_bonus) || 0), 0);
  }

  getTotalAddonIncentive(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.service_addon_incentive) || 0), 0);
  }

  getTotalTargetIncentive(): number {
    if (!this.incentivesData) return 0;
    return this.incentivesData.reduce((acc, curr) => acc + (parseFloat(curr.service_target_incentive) || 0), 0);
  }

  exportIncentives() {
    if (!this.incentiveStartDate || !this.incentiveEndDate) return;
    let url = `${this.apiService.baseUrl}/finance/api/reports/incentive-calculation/?export=true&start_date=${this.incentiveStartDate}&end_date=${this.incentiveEndDate}&frequency=${this.incentiveFrequency}`;
    const cid = this.getCenterId();
    if (cid) url += `&center_id=${cid}`;
    const token = localStorage.getItem('access_token');
    if (token) {
      fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
        .then(res => res.blob())
        .then(blob => {
          const a = document.createElement('a');
          a.href = window.URL.createObjectURL(blob);
          a.download = `incentive_report_${this.incentiveFrequency}_${this.incentiveStartDate}_to_${this.incentiveEndDate}.xlsx`;
          a.click();
        });
    } else {
      window.open(url);
    }
  }

  getCenterName(centerId: any): string {
    if (!centerId) return 'Organisation-Wide (All Centers)';
    const found = this.centers.find(c => c.id === centerId);
    return found ? (found.display_name || found.center_name) : `Center #${centerId}`;
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
      let mapped = results.map((res: any, index) => ({
        center_name: this.centers[index].display_name || this.centers[index].center_name,
        ...res
      }));
      
      mapped.sort((a, b) => {
        const valA = a.categories?.target_achieved_percentage || 0;
        const valB = b.categories?.target_achieved_percentage || 0;
        return valA - valB;
      });

      this.multiSalonData = mapped;
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
    this.apiService.getPettyCashEntries(cid, this.startDate, this.endDate).subscribe(res => {
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
      this.apiService.updatePettyCashEntry(this.editingPettyCash.id, data).subscribe({
        next: () => {
          this.pettyCashForm = { description: '', amount: '', voucher_number: '', comments: '' };
          this.editingPettyCash = null;
          this.isSaving = false;
          alert('Petty cash entry updated successfully!');
          this.loadPettyCash();
        },
        error: (err) => {
          this.isSaving = false;
          let msg = 'Failed to update petty cash entry. Please try again.';
          if (err?.error?.detail) msg = err.error.detail;
          alert(msg);
          this.cdr.detectChanges();
        }
      });
    } else {
      this.apiService.createPettyCashEntry(data).subscribe({
        next: () => {
          this.pettyCashForm = { description: '', amount: '', voucher_number: '', comments: '' };
          this.isSaving = false;
          alert('Petty cash entry added successfully!');
          this.loadPettyCash();
        },
        error: (err) => {
            this.isSaving = false;
            let msg = 'Failed to add petty cash entry. Please try again.';
            if (err?.error?.detail) msg = err.error.detail;
            alert(msg);
            this.cdr.detectChanges();
        }
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

  // ---- Daily Closing ----  // Admin View petty cash logs
  adminPettyCashLogs: any[] = [];

  loadClosingHistory() {
    const cid = this.getCenterId();
    if (!cid) return;
    // Pass the current date range so the admin view is filtered correctly
    this.apiService.getDailyClosings(cid, undefined, this.closingStartDate, this.closingEndDate).subscribe(data => {
      this.closingHistory = data;
      this.cdr.detectChanges();
    });

    // Also load petty cash for the admin view using these dates
    this.apiService.getPettyCashEntries(cid, this.closingStartDate, this.closingEndDate).subscribe(data => {
      this.adminPettyCashLogs = data;
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
}
