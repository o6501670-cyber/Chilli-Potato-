import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';
import { CsvService } from '../services/csv.service';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';
@Component({
  selector: 'app-marketing',
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './marketing.html',
  styleUrl: './marketing.css'
})
export class MarketingComponent implements OnInit {
  apiService = inject(ApiService);
  toastService = inject(ToastService);
  cdr = inject(ChangeDetectorRef);
  csvService = inject(CsvService);

  isSaving = false;
  activeTab: any = 'Campaigns';
  campaignTab: any = 'Promotions';
  minDate: string = new Date().toISOString().split('T')[0];

  isOwner = false;
  hasGlobalAccess = false;
  permissions: any = {};
  centers: any[] = [];
  selectedCenterId: number | null = null;
  selectedFilterCenterId: number | null = null; // Used for WhatsApp filtering only

  // Data
  whatsappMessages: any[] = [];
  promotions: any[] = [];
  cards: any[] = [];
  memberships: any[] = [];
  packages: any[] = [];
  servicesList: any[] = [];

  newPromotion: any = {
    level: 'Organisation',
    center: null,
    name: '',
    start_date: '',
    end_date: '',
    description: '',
    members_only: false,
    max_usage_per_client: null,
    promo_type: 'Discount',
    config: {
      discount_type: 'Percentage',
      discount_value: null,
      target: 'Overall Bill',
      min_bill_amount: null,
      specific_service: '',
      flat_price: null,
      trigger_services: ['', ''],
      trigger_discount: null,
      cashback_min_bill: null,
      cashback_discount: null,
      cashback_validity_type: 'Days',
      cashback_validity_days: null,
      cashback_specific_date: ''
    }
  };

  usageStartDate = '';
  usageEndDate = '';
  usageData: any[] = [];
  hasRunUsageReport = false;
  selectedUsage: any = null;

  // Filters
  showExpired = false;
  showInactive = false;
  showOrgOnly = false;

  fetchUsageData() {
    this.selectedUsage = null;
    this.apiService.getPromotionUsage(this.usageStartDate, this.usageEndDate).subscribe(data => {
      this.usageData = data || [];
      this.hasRunUsageReport = true;
      this.cdr.detectChanges();
    });
  }

  exportExcel() {
    const headers = ['Item (Type)', 'Type', 'Start Date', 'End Date', 'Applied to', 'Status', 'Count', 'Revenue'];
    const rows = this.usageData.map(u => [
      u.name || '',
      u.type || 'Promotion',
      u.start_date || '',
      u.end_date || '',
      u.level === 'Organisation' ? 'Org Level' : 'Salon level',
      u.status || '',
      u.count || 0,
      u.revenue || 0
    ]);
    this.csvService.exportToCsv('Marketing_Usage_Report.csv', headers, rows);
  }

  viewUsageDetails(usage: any) {
    this.selectedUsage = usage;
    this.cdr.detectChanges();
  }

  newCard: any = {
    level: 'Organisation',
    center: null,
    title: '',
    pre_tax_price: null,
    post_tax_price: null,
    value: null,
    benefit_percent: null,
    incentive: null,
    expiry_days: null,
    description: ''
  };

  newMembership: any = {
    level: 'Organisation',
    center: null,
    name: '',
    discount_percent: null,
    pre_tax_price: null,
    post_tax_price: null,
    value: null,
    incentive: null,
    expiry_days: null,
    description: '',
    is_vip: false
  };

  calculateCardPostTax() {
    if (this.newCard.pre_tax_price) {
      this.newCard.post_tax_price = Math.round((Number(this.newCard.pre_tax_price) * 1.05) * 100) / 100;
      this.calculateCardBenefit();
    }
  }

  calculateCardValue() {
    if (this.newCard.post_tax_price && this.newCard.benefit_percent != null) {
      const pt = Number(this.newCard.post_tax_price);
      const bp = Number(this.newCard.benefit_percent);
      this.newCard.value = Math.round(pt * (1 + bp / 100) * 100) / 100;
    }
  }

  calculateCardPreTax() {
    if (this.newCard.post_tax_price) {
      this.newCard.pre_tax_price = Math.round((Number(this.newCard.post_tax_price) / 1.05) * 100) / 100;
      this.calculateCardBenefit();
    }
  }

  calculateCardBenefit() {
    if (this.newCard.post_tax_price && this.newCard.value) {
      const pt = Number(this.newCard.post_tax_price);
      const val = Number(this.newCard.value);
      if (pt > 0) {
        this.newCard.benefit_percent = Math.round(((val - pt) / pt) * 10000) / 100;
      }
    }
  }

  calculateMembershipBenefit() {
    if (this.newMembership.post_tax_price && this.newMembership.value) {
      const pt = Number(this.newMembership.post_tax_price);
      const val = Number(this.newMembership.value);
      if (pt > 0) {
        this.newMembership.discount_percent = Math.round(((val - pt) / pt) * 10000) / 100;
      }
    }
  }

  calculateMembershipValue() {
    if (this.newMembership.post_tax_price && this.newMembership.discount_percent != null) {
      const pt = Number(this.newMembership.post_tax_price);
      const bp = Number(this.newMembership.discount_percent);
      this.newMembership.value = Math.round(pt * (1 + bp / 100) * 100) / 100;
    }
  }

  calculateMembershipPostTax() {
    if (this.newMembership.pre_tax_price) {
      this.newMembership.post_tax_price = Math.round((Number(this.newMembership.pre_tax_price) * 1.05) * 100) / 100;
      this.calculateMembershipBenefit();
    }
  }

  calculateMembershipPreTax() {
    if (this.newMembership.post_tax_price) {
      this.newMembership.pre_tax_price = Math.round((Number(this.newMembership.post_tax_price) / 1.05) * 100) / 100;
      this.calculateMembershipBenefit();
    }
  }

  newPackage: any = {
    level: 'Organisation',
    center: null,
    name: '',
    service_name: '',
    description: '',
    price: null,
    validity_days: null
  };

  ngOnInit() {
    let user: any = null;
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        user = JSON.parse(userStr);
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
        this.permissions = user.permissions || {};
      } catch (e) {
        console.error('Failed to parse user from localStorage', e);
      }
    }

    if (this.isOwner || this.permissions.marketing?.campaigns?.read) {
      this.activeTab = 'Campaigns';
    } else if (this.permissions.marketing?.whatsapp?.read) {
      this.activeTab = 'WhatsApp';
    } else if (this.permissions.marketing?.usage?.read) {
      this.activeTab = 'Usage';
    } else {
      this.activeTab = '';
    }

    this.apiService.getCenters().subscribe(data => {
      this.centers = data || [];
      if (this.isOwner) {
        this.selectedFilterCenterId = null;
      } else {
        this.selectedFilterCenterId = user?.center_id || null;
        if (this.centers.length > 0 && !this.centers.some(c => c.id == this.selectedFilterCenterId)) {
          this.selectedFilterCenterId = this.centers[0].id;
        }
      }
      this.selectedCenterId = this.selectedFilterCenterId;
      if (!this.isOwner) {
        this.newPromotion.level = 'Center';
        this.newCard.level = 'Center';
        this.newMembership.level = 'Center';
        this.newPackage.level = 'Center';
      }
      this.loadData();
    });
  }

  setTab(tab: string) {
    this.activeTab = tab;
    this.loadData();
  }

  setCampaignTab(tab: string) {
    this.campaignTab = tab;
  }

  onFilterCenterChange() {
    this.selectedCenterId = this.selectedFilterCenterId;
    this.loadData();
  }

  loadData() {
    if (this.activeTab === 'WhatsApp') {
      const cid = this.selectedFilterCenterId ? this.selectedFilterCenterId : undefined;
      this.apiService.getWhatsAppMessages(cid).subscribe(data => {
        this.whatsappMessages = data;
        this.cdr.detectChanges();
      });
    } else {
      const cid = this.selectedFilterCenterId ? this.selectedFilterCenterId : undefined;
      this.apiService.getPromotions(cid, true, true).subscribe(data => {
        this.promotions = data;
        this.cdr.detectChanges();
      });
      this.apiService.getValueCards(cid, true).subscribe(data => {
        this.cards = data;
        this.cdr.detectChanges();
      });
      this.apiService.getMemberships(cid, true).subscribe(data => {
        this.memberships = data;
        this.cdr.detectChanges();
      });
      this.apiService.getPackages(cid, true).subscribe(data => {
        this.packages = data;
        this.cdr.detectChanges();
      });
      this.apiService.getServices().subscribe(data => {
        this.servicesList = data || [];
        this.cdr.detectChanges();
      });
    }
  }

  private getCreateCenterId(): number | null {
    return this.selectedCenterId ?? this.selectedFilterCenterId ?? null;
  }

  // --- Promotions ---
  private filterCampaigns(list: any[], hasExpiry: boolean = false) {
    return list.filter(item => {
      if (!this.showInactive && item.is_active === false) return false;
      if (this.showOrgOnly && item.level !== 'Organisation') return false;
      if (hasExpiry && !this.showExpired && item.end_date) {
        if (new Date(item.end_date) < new Date()) return false;
      }
      return true;
    });
  }

  get orgPromotions() { return this.filterCampaigns(this.promotions, true).filter((p: any) => p.level === 'Organisation'); }
  get centerPromotions() { return this.filterCampaigns(this.promotions, true).filter((p: any) => p.level === 'Center'); }

  addPromotion() {
    const payload = { ...this.newPromotion };
    if (payload.level === 'Center') {
      const centerId = this.getCreateCenterId();
      if (!centerId) { this.toastService.showError('Please select a center for this promotion'); return; }
      payload.center = centerId;
    } else {
      payload.center = null;
    }

    if (!payload.name || !payload.start_date || !payload.end_date) {
      this.toastService.showError('Please fill all required fields (Name, Start Date, End Date)');
      return;
    }

    this.isSaving = true;
    this.apiService.createPromotion(payload).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.showSuccess('Promotion created successfully');
        this.loadData();
        this.newPromotion = {
          level: 'Organisation', center: null, name: '', start_date: '', end_date: '', description: '', members_only: false,
          max_usage_per_client: null,
          promo_type: 'Discount',
          config: {
            discount_type: 'Percentage', discount_value: null, target: 'Overall Bill', min_bill_amount: null, specific_service: '',
            flat_price: null, trigger_services: ['', ''], trigger_discount: null, cashback_min_bill: null, cashback_discount: null, cashback_validity_type: 'Days', cashback_validity_days: null, cashback_specific_date: ''
          }
        };
      },
      error: (err) => {
        this.isSaving = false;
        let msg = 'Failed to create promotion';
        if (err.error && typeof err.error === 'object') {
          msg += ': ' + JSON.stringify(err.error);
        }
        this.toastService.showError(msg);
      }
    });
  }

  // --- Cards ---
  get orgCards() { return this.filterCampaigns(this.cards).filter((p: any) => p.level === 'Organisation'); }
  get centerCards() { return this.filterCampaigns(this.cards).filter((p: any) => p.level === 'Center'); }

  addCard() {
    const payload = { ...this.newCard };
    if (!payload.title || payload.post_tax_price == null || payload.value == null || payload.expiry_days == null) {
      this.toastService.showError('Please fill all required fields');
      return;
    }
    if (payload.level === 'Center') {
      const centerId = this.getCreateCenterId();
      if (!centerId) { this.toastService.showError('Please select a center for this card'); return; }
      payload.center = centerId;
    } else {
      payload.center = null;
    }

    this.isSaving = true;
    this.apiService.createValueCard(payload).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.showSuccess('Card created successfully');
        this.loadData();
        this.newCard = { level: 'Organisation', center: null, title: '', pre_tax_price: null, post_tax_price: null, value: null, benefit_percent: null, incentive: null, expiry_days: null, description: '' };
      },
      error: (err) => { this.isSaving = false; this.toastService.showError('Failed to create card: ' + JSON.stringify(err.error)); }
    });
  }

  // --- Memberships ---
  get orgMemberships() { return this.filterCampaigns(this.memberships).filter((p: any) => p.level === 'Organisation'); }
  get centerMemberships() { return this.filterCampaigns(this.memberships).filter((p: any) => p.level === 'Center'); }

  addMembership() {
    const payload = { ...this.newMembership };
    if (payload.level === 'Center') {
      const centerId = this.getCreateCenterId();
      if (!centerId) { this.toastService.showError('Please select a center for this membership'); return; }
      payload.center = centerId;
    } else {
      payload.center = null;
    }

    this.isSaving = true;
    this.apiService.createMembership(payload).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.showSuccess('Membership created successfully');
        this.loadData();
        this.newMembership = { level: 'Organisation', center: null, name: '', discount_percent: null, pre_tax_price: null, post_tax_price: null, value: null, incentive: null, expiry_days: null, description: '', is_vip: false };
      },
      error: (err) => { this.isSaving = false; this.toastService.showError('Failed to create membership: ' + JSON.stringify(err.error)); }
    });
  }

  // --- Packages ---
  get orgPackages() { return this.filterCampaigns(this.packages).filter((p: any) => p.level === 'Organisation'); }
  get centerPackages() { return this.filterCampaigns(this.packages).filter((p: any) => p.level === 'Center'); }

  addPackage() {
    const payload = { ...this.newPackage };
    if (payload.level === 'Center') {
      const centerId = this.getCreateCenterId();
      if (!centerId) { this.toastService.showError('Please select a center for this package'); return; }
      payload.center = centerId;
    } else {
      payload.center = null;
    }

    if (payload.service_name) {
      const selectedSvc = this.servicesList.find(s => s.name === payload.service_name);
      if (selectedSvc) {
        payload.services_json = [{
          id: selectedSvc.id,
          service_id: selectedSvc.id,
          name: selectedSvc.name,
          service_name: selectedSvc.name,
          price: selectedSvc.price || selectedSvc.default_price || 0,
          pkgQty: payload.pkgQty || 1
        }];
      }
    }

    this.isSaving = true;
    this.apiService.createPackage(payload).subscribe({
      next: () => {
        this.isSaving = false;
        this.toastService.showSuccess('Package created successfully');
        this.loadData();
        this.newPackage = { level: 'Organisation', center: null, name: '', service_name: '', pkgQty: null, description: '', price: null, validity_days: null };
      },
      error: (err) => { this.isSaving = false; this.toastService.showError('Failed to create package: ' + JSON.stringify(err.error)); }
    });
  }
  // --- Actions ---
  toggleStatus(item: any, type: string) {
    if (this.isSaving) return;
    this.isSaving = true;
    let obs: any;

    // Use dedicated toggle-status endpoints that bypass the is_active filter,
    // so a deactivated item can always be re-activated (no 404 on inactive items).
    if (type === 'promotion') obs = this.apiService.togglePromotion(item.id);
    else if (type === 'card') obs = this.apiService.toggleValueCard(item.id);
    else if (type === 'membership') obs = this.apiService.toggleMembership(item.id);
    else if (type === 'package') obs = this.apiService.togglePackage(item.id);

    if (obs) {
      obs.subscribe({
        next: (res: any) => {
          this.isSaving = false;
          // Optimistically update the UI state instantly
          item.is_active = res.is_active;
          const label = res.is_active ? 'Activated' : 'Deactivated';
          this.toastService.showSuccess(`${label} successfully`);
          // Still fetch in background to ensure sync
          this.loadData();
        },
        error: (err: any) => {
          this.isSaving = false;
          this.toastService.showError('Failed to update status: ' + (err.error?.detail || JSON.stringify(err.error)));
        }
      });
    } else {
      this.isSaving = false;
    }
  }

  deleteCampaign(item: any, type: string) {
    if (this.isSaving) return;
    if (!confirm('Are you sure you want to delete this?')) return;
    this.isSaving = true;
    let obs: any;

    if (type === 'promotion') obs = this.apiService.deletePromotion(item.id);
    else if (type === 'card') obs = this.apiService.deleteValueCard(item.id);
    else if (type === 'membership') obs = this.apiService.deleteMembership(item.id);
    else if (type === 'package') obs = this.apiService.deletePackage(item.id);

    if (obs) {
      obs.subscribe({
        next: () => {
          this.isSaving = false;
          this.toastService.showSuccess('Deleted successfully');
          this.loadData();
        },
        error: (err: any) => {
          this.isSaving = false;
          this.toastService.showError('Failed to delete: ' + JSON.stringify(err.error));
        }
      });
    } else {
      this.isSaving = false;
    }
  }

  // --- Edit Modal Logic ---
  showEditModal: boolean = false;
  editItemType: 'promotion' | 'card' | 'membership' | 'package' | null = null;
  editItemData: any = {};

  openEditModal(item: any, type: 'promotion' | 'card' | 'membership' | 'package') {
    this.editItemType = type;
    // deep copy the object so we don't mutate the list immediately
    this.editItemData = JSON.parse(JSON.stringify(item));

    // Ensure config exists for promotions
    if (type === 'promotion' && !this.editItemData.config) {
      this.editItemData.config = {};
    }

    // For packages, ensure services_json exists and extract pkgQty
    if (type === 'package') {
      if (!this.editItemData.services_json) {
        this.editItemData.services_json = [];
      }
      if (this.editItemData.services_json.length > 0) {
        this.editItemData.pkgQty = this.editItemData.services_json[0].pkgQty || 1;
      }
    }

    this.showEditModal = true;
  }

  closeEditModal() {
    this.showEditModal = false;
    this.editItemType = null;
    this.editItemData = {};
  }

  saveEdit() {
    if (this.isSaving || !this.editItemType) return;
    this.isSaving = true;

    // Special logic for package to update services_json if service_name changed
    if (this.editItemType === 'package' && this.editItemData.service_name) {
      const selectedSvc = this.servicesList.find(s => s.name === this.editItemData.service_name);
      if (selectedSvc) {
        this.editItemData.services_json = [{
          id: selectedSvc.id,
          service_id: selectedSvc.id,
          name: selectedSvc.name,
          service_name: selectedSvc.name,
          price: selectedSvc.price || selectedSvc.default_price || 0,
          pkgQty: this.editItemData.pkgQty || 1
        }];
      }
    }

    let obs: any;
    if (this.editItemType === 'promotion') obs = this.apiService.updatePromotion(this.editItemData.id, this.editItemData);
    else if (this.editItemType === 'card') obs = this.apiService.updateValueCard(this.editItemData.id, this.editItemData);
    else if (this.editItemType === 'membership') obs = this.apiService.updateMembership(this.editItemData.id, this.editItemData);
    else if (this.editItemType === 'package') obs = this.apiService.updatePackage(this.editItemData.id, this.editItemData);

    if (obs) {
      obs.subscribe({
        next: () => {
          this.isSaving = false;
          this.toastService.showSuccess('Updated successfully');
          this.closeEditModal();
          this.loadData();
        },
        error: (err: any) => {
          this.isSaving = false;
          this.toastService.showError('Failed to update: ' + (err.error?.detail || JSON.stringify(err.error)));
        }
      });
    }
  }

  calculateEditCardPostTax() {
    if (this.editItemData.pre_tax_price) {
      this.editItemData.post_tax_price = Math.round((Number(this.editItemData.pre_tax_price) * 1.05) * 100) / 100;
      this.calculateEditCardBenefit();
    }
  }

  calculateEditCardValue() {
    if (this.editItemData.post_tax_price && this.editItemData.benefit_percent != null) {
      const pt = Number(this.editItemData.post_tax_price);
      const bp = Number(this.editItemData.benefit_percent);
      this.editItemData.value = Math.round(pt * (1 + bp / 100) * 100) / 100;
    }
  }

  calculateEditCardPreTax() {
    if (this.editItemData.post_tax_price) {
      this.editItemData.pre_tax_price = Math.round((Number(this.editItemData.post_tax_price) / 1.05) * 100) / 100;
      this.calculateEditCardBenefit();
    }
  }

  calculateEditCardBenefit() {
    if (this.editItemData.post_tax_price && this.editItemData.value) {
      const pt = Number(this.editItemData.post_tax_price);
      const val = Number(this.editItemData.value);
      if (pt > 0) {
        this.editItemData.benefit_percent = Math.round(((val - pt) / pt) * 10000) / 100;
      }
    }
  }

  calculateEditMembershipBenefit() {
    if (this.editItemData.post_tax_price && this.editItemData.value) {
      const pt = Number(this.editItemData.post_tax_price);
      const val = Number(this.editItemData.value);
      if (pt > 0) {
        this.editItemData.discount_percent = Math.round(((val - pt) / pt) * 10000) / 100;
      }
    }
  }

  calculateEditMembershipValue() {
    if (this.editItemData.post_tax_price && this.editItemData.discount_percent != null) {
      const pt = Number(this.editItemData.post_tax_price);
      const bp = Number(this.editItemData.discount_percent);
      this.editItemData.value = Math.round(pt * (1 + bp / 100) * 100) / 100;
    }
  }

  calculateEditMembershipPostTax() {
    if (this.editItemData.pre_tax_price) {
      this.editItemData.post_tax_price = Math.round((Number(this.editItemData.pre_tax_price) * 1.05) * 100) / 100;
      this.calculateEditMembershipBenefit();
    }
  }

  calculateEditMembershipPreTax() {
    if (this.editItemData.post_tax_price) {
      this.editItemData.pre_tax_price = Math.round((Number(this.editItemData.post_tax_price) / 1.05) * 100) / 100;
      this.calculateEditMembershipBenefit();
    }
  }


  // --- WhatsApp Campaign Logic ---
  showNewCampaignModal: boolean = false;
  campaignMessage: string = '';
  campaignCenterId: any = 'all';

  openNewCampaignModal() {
    this.campaignMessage = '';
    this.campaignCenterId = 'all';
    this.showNewCampaignModal = true;
  }

  closeNewCampaignModal() {
    this.showNewCampaignModal = false;
  }

  sendCampaign() {
    if (!this.campaignMessage.trim()) {
      this.toastService.showError('Please enter a message to send.');
      return;
    }

    // Using native confirm for confirmation
    const target = this.campaignCenterId === 'all' ? 'all clients' : 'clients in selected center';
    if (confirm(`Send Campaign?\nAre you sure you want to send this message to ${target}?`)) {
      this.apiService.sendWhatsAppCampaign(this.campaignCenterId, this.campaignMessage).subscribe({
        next: (res: any) => {
          this.toastService.showSuccess(`Campaign sent successfully to ${res.count || 0} clients!`);
          this.closeNewCampaignModal();
          this.loadData(); // Refresh list
        },
        error: (err: any) => {
          this.toastService.showError(err.error?.error || 'Failed to send campaign.');
        }
      });
    }
  }

}
