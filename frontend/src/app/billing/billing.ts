import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, ElementRef, HostListener, OnInit, ViewChild, inject } from '@angular/core';

import { ActivatedRoute } from '@angular/router';

import { CommonModule } from '@angular/common';

import { FormsModule } from '@angular/forms';
import { BillingLandingComponent } from './components/landing/billing-landing.component';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';

import { ApiService } from '../services/api';



@Component({

  selector: 'app-billing',

  standalone: true,

  imports: [CommonModule, FormsModule, BillingLandingComponent, LocationSelectorComponent],

  templateUrl: './billing.html',

  styleUrls: ['./billing.css']
,
  changeDetection: ChangeDetectionStrategy.OnPush
})

export class BillingComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  @ViewChild('clientSearchInput') clientSearchInput!: ElementRef;
  @ViewChild('serviceSearchInput') serviceSearchInput!: ElementRef;
  // Toast Notifications
  toastMessage: string = '';
  toastType: 'success' | 'error' | 'info' = 'info';
  toastVisible: boolean = false;

  // Success & Print Flow
  showSuccessModal: boolean = false;
  completedInvoiceData: any = null;

  printInvoice() {
    window.print();
  }

  closeSuccessModal() {
    this.showSuccessModal = false;
    this.completedInvoiceData = null;
  }

  toastTimeout: any;

  showToast(msg: string, type: 'success' | 'error' | 'info' = 'info') {
    this.toastMessage = msg;
    this.toastType = type;
    this.toastVisible = true;
    if (this.toastTimeout) clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      this.toastVisible = false;
    }, 3000);
  }


  apiService = inject(ApiService);

  cdr = inject(ChangeDetectorRef);

  route = inject(ActivatedRoute);



  viewMode: 'landing' | 'new-invoice' = 'landing';



  centers: any[] = [];

  selectedCenterId: number | null = null;



  // Landing view data

  globalInvoices: any[] = [];

  appointments: any[] = [];
  selectedAppointmentId: any = null;

  staffActivity: any[] = [];



  get selectedCenterName(): string {

    if (!this.selectedCenterId || !this.centers) return 'All Centers';

    const center = this.centers.find(c => c.id === this.selectedCenterId);

    return center ? center.display_name : 'All Centers';

  }



  // New Invoice view data

  searchPhone: string = '';

  clients: any[] = [];

  client: any = null;

  clientInvoices: any[] = [];

  clientServiceHistory: any[] = [];

  clientAdvances: any[] = [];

  clientAdvanceBalance: number = 0;
  clientCashbackBalance: number = 0;

  clientHistory: any[] = [];

  useAdvancePayment: boolean = false;



  advances: any[] = [];



  services: any[] = [];

  products: any[] = [];

  memberships: any[] = [];

  packages: any[] = [];

  cards: any[] = [];

  staffMembers: any[] = [];
  activityFeed: any[] = [];


  currentInvoiceId: number | null = null;
  currentInvoiceStatus: string = 'draft';

  promotions: any[] = [];

  selectedPromotion: any = null;

  configStaffIds: number[] = [];



  showCheckoutModal: boolean = false;

  // Advanced POS States
  heldCarts: any[] = [];
  showHeldCartsModal: boolean = false;
  barcodeBuffer: string = '';
  lastBarcodeKeystrokeTime: number = 0;

  checkoutPayments: any[] = [];

  checkoutRemaining: number = 0;





  cart: any[] = [];

  activeTab: 'search' | 'cards' | 'packages' | 'memberships' | 'advance' = 'search';

  serviceSearchTerm: string = '';
  productSearchTerm: string = '';
  showServiceDropdown: boolean = false;
  showProductDropdown: boolean = false;
  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (target && !target.closest('.search-blocks-container')) {
      this.showServiceDropdown = false;
      this.showProductDropdown = false;
    }
  }

  toggleServiceDropdown(event?: Event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.activeTab = 'search';
    this.showServiceDropdown = true;
    this.showProductDropdown = false;
    this.cdr.detectChanges();
  }

  toggleProductDropdown(event?: Event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    this.activeTab = 'search';
    this.showProductDropdown = true;
    this.showServiceDropdown = false;
    this.cdr.detectChanges();
  }



  // Detailed Configuration State

  selectedItemForConfig: any = null;

  configType: 'service' | 'product' | 'card' | 'advance' | 'package' | 'membership' | null = null;

  managerDiscountPercent: number = 0;

  managerDiscountAmount: number = 0;

  finalConfigPrice: number = 0;

  configStaffId: any = null;

  advanceAmount: number = 0;

  advanceDescription: string = '';



  // Taxes and Discounts

  invoiceDiscount: number = 0;

  invoiceCGST: number = 0;

  invoiceSGST: number = 0;



  // Package Config

  packageSearchTerm: string = '';

  packageSelectedServices: any[] = [];



  isOwner = false;
  hasGlobalAccess = false;

  permissions: any = {};



  ngOnInit(): void {

    this.route.queryParams.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {

      if (params['appointment_id']) {

        this.loadAppointmentIntoBilling(params['appointment_id']);

      }

    });

    const userStr = localStorage.getItem('user');

    if (userStr) {

      try {

        const user = JSON.parse(userStr);

        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
        this.permissions = user.permissions || {};

      } catch (e) { }

    }

    this.loadCenters();

  }



  loadAppointmentIntoBilling(appointmentId: string | number) {

    this.apiService.get('appointments/api/appointments/' + appointmentId + '/').pipe(takeUntilDestroyed(this.destroyRef)).subscribe((appt: any) => {

      if (!appt) return;
      this.selectedAppointmentId = appointmentId;



      if (appt.center && this.selectedCenterId !== appt.center) {

        this.selectedCenterId = appt.center;

        this.loadMasters();

      }



      this.apiService.getClients(appt.client_phone).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({

        next: (clients: any[]) => {

          this.openNewInvoice();

          const existingClient = (clients || []).find(c => c.phone === appt.client_phone);

          if (existingClient) {

            this.selectClient(existingClient);

          } else {

            this.client = {

              name: appt.client_name,

              phone: appt.client_phone,

            };

            this.searchPhone = appt.client_phone;

          }



          if (appt.services && appt.services.length > 0) {

            let attempts = 0;

            const populateCart = () => {

              if (this.services.length === 0 && attempts < 10) {

                attempts++;

                setTimeout(populateCart, 300);

                return;

              }

              appt.services.forEach((s: any) => {

                const matchedService = this.services.find(ms => ms.name === s.service_name);

                const objId = matchedService ? matchedService.id : null;



                this.cart.push({

                  content_type: 'services.servicemaster',

                  object_id: objId,

                  description: s.service_name,

                  unit_price: Number(s.price),

                  discount: 0,

                  quantity: 1,

                  staff_members: s.staff ? [Number(s.staff)] : []

                });

              });

              this.cdr.detectChanges();

            };

            populateCart();

          } else {

            this.cdr.detectChanges();

          }

        },

        error: (err: any) => {

          this.client = {

            name: appt.client_name,

            phone: appt.client_phone,

          };

          this.searchPhone = appt.client_phone;

          this.openNewInvoice();

          this.cdr.detectChanges();

        }

      });

    }, (err: any) => {

      console.error("Failed to load appointment", err);

    });

  }



  loadCenters() {

    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data: any) => {

      this.centers = Array.isArray(data) ? data : (data.results || []);

      if (this.centers.length && !this.selectedCenterId) {

        this.selectedCenterId = this.centers[0].id;

      }

      this.loadLandingData();

      this.loadMasters();

      this.cdr.detectChanges();

    }, (err: any) => {

      console.error('Failed to load centers', err);

    });

  }



  onCenterChange() {

    this.loadLandingData();

    this.loadMasters();

  }



  setViewMode(mode: 'landing' | 'new-invoice') {
    this.viewMode = mode;
    if (mode === 'landing') {
      this.loadLandingData();
    }
  }

  loadLandingData() {
    const now = new Date();
    const today = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');

    // 1. Fetch Global Invoices (Only Open/Draft Invoices)
    this.apiService.getInvoices(undefined, this.selectedCenterId || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => {
      this.globalInvoices = (d || []).filter(inv => inv.status === 'draft');
      this.cdr.detectChanges();
    });

  // 2. Fetch Appointments for today
    this.apiService.getAppointments(this.selectedCenterId || undefined, today).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => {
      this.appointments = d || [];
      this.cdr.detectChanges();
    });

    // 3. Fetch Staff Activity for today (using StaffRevenueReport)
    this.apiService.getStaffRevenueReport(this.selectedCenterId || undefined, today, today).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any) => {

      this.staffActivity = (d?.breakdown || []).map((b: any) => ({
         staff_name: b.staff_name,
         amount: b.revenue,
         count: b.services
      }));
      this.activityFeed = d?.activity_feed || [];

      this.cdr.detectChanges();

    });

  }

  deleteDraftInvoice(inv: any) {
    if (!confirm("Are you sure you want to permanently delete this draft invoice?")) return;
    this.apiService.deleteInvoice(inv.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.showToast('Draft invoice deleted successfully.', 'success');
        this.globalInvoices = this.globalInvoices.filter(x => x.id !== inv.id);
        if (this.currentInvoiceId === inv.id) {
           this.discardInvoice();
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.showToast('Failed to delete draft invoice.', 'error');
        console.error(err);
      }
    });
  }



  loadMasters() {

    const cid = this.selectedCenterId ?? undefined;

    this.apiService.getServices(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.services = d || []);

    this.apiService.getProducts(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.products = d || []);

    this.apiService.getMemberships(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.memberships = d || []);

    this.apiService.getPackages(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.packages = d || []);

    this.apiService.getValueCards(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.cards = d || []);

    this.apiService.getStaffMembers(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => {

      this.staffMembers = (d || []).filter((s: any) => s.is_active !== false);

      this.cdr.detectChanges();

    });

    this.apiService.get('marketing/api/promotions/').pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => this.promotions = d || []);



  }



  loadClients() {

    this.apiService.getClients('').pipe(takeUntilDestroyed(this.destroyRef)).subscribe((d: any[]) => {

      this.clients = d || [];

      this.cdr.detectChanges();

    }, (err: any) => {

      console.error('Failed to load clients', err);

    });

  }



  // --- View Mode Toggles ---

  openNewInvoice() {
    this.cart = [];
    this.client = null;
    this.resetConfig();
    this.searchPhone = '';
    this.clientHistory = [];
    this.invoiceCGST = 0;
    this.invoiceSGST = 0;
    this.invoiceDiscount = 0;
    this.clearDraft();
    this.setViewMode('new-invoice');
  }



  discardInvoice() {
    if (this.currentInvoiceId && this.currentInvoiceStatus === 'draft') {
      this.apiService.delete(`billing/invoices/${this.currentInvoiceId}/`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.finalizeDiscard();
        },
        error: (err) => {
          console.error('Failed to delete draft', err);
          this.finalizeDiscard();
        }
      });
    } else {
      this.finalizeDiscard();
    }
  }

  finalizeDiscard() {
    this.isSaving = false;
    this.setViewMode('landing');
    this.cart = [];
    this.client = null;
    this.searchPhone = '';
    this.currentInvoiceId = null;
    this.currentInvoiceStatus = 'draft';
    this.invoiceDiscount = 0;
    this.clearDraft();

    this.invoiceCGST = 0;

    this.invoiceSGST = 0;

    this.useAdvancePayment = false;

    this.loadLandingData();
    this.cdr.detectChanges();
  }



  searchTimeout: any;

  onSearchPhoneChange() {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      if (this.searchPhone && this.searchPhone.trim().length > 0) {
        this.searchClients();
      } else {
        this.clients = [];
      }
    }, 400);
  }





  // --- Client Search & Select ---

  searchClients() {

    this.apiService.getClients(this.searchPhone).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res: any) => {
        const d = res && res.results ? res.results : res;
        this.clients = d || [];
        this.cdr.detectChanges();
      }, error: (err: any) => {
        console.error('Clients API error', err);
      }
    });

  }



  selectClient(client: any) {
    if (client.is_blacklisted) {
      this.showToast('This client is blacklisted and cannot be billed.', 'error');
      this.searchPhone = '';
      this.clients = [];
      return;
    }
    this.client = client;
    this.searchPhone = client.phone;
    this.clients = [];
    
    if (client.is_blacklisted) {
      this.showToast(`WARNING: Client is blacklisted! Reason: ${client.blacklist_reason || 'No reason provided.'}`, 'error');
    }

    this.loadClientHistory(client.id);

    this.loadClientAdvances(client.id);



    // Inject Active Memberships into Promotions
    // First, remove any previously injected memberships
    this.promotions = this.promotions.filter((p: any) => !p.id || !p.id.toString().startsWith('m_'));
    if (this.selectedPromotion && this.selectedPromotion.id && this.selectedPromotion.id.toString().startsWith('m_')) {
      this.selectedPromotion = null;
      this.applyPromotion();
    }

    if (this.client.active_memberships && this.client.active_memberships.length > 0) {

      this.client.active_memberships.forEach((am: any) => {

        if (am.membership_detail) {

          const exists = this.promotions.find((p: any) => p.id === 'm_' + am.id);

          if (!exists) {

            this.promotions.push({

              id: 'm_' + am.id,

              name: '👑 ' + am.membership_detail.name,

              discount_percent: am.membership_detail.discount_percent,

              discount_type: 'Percentage'

            });

          }

        }

      });

    }



    // Inject Active Packages into Services (Redeem for Rs. 0)
    this.services = this.services.filter(s => !(s.name && s.name.startsWith('🎁 [Redeem]')));
    if (this.client.active_packages && this.client.active_packages.length > 0) {
      this.client.active_packages.forEach((ap: any) => {
        if (ap.package_detail && ap.services_remaining) {
          Object.keys(ap.services_remaining).forEach(svcId => {
            const remaining = ap.services_remaining[svcId];
            if (remaining > 0) {
              const originalSvc = this.services.find(s => s.id === Number(svcId) && s.name && !s.name.includes('🎁'));
              if (originalSvc) {
                const redeemSvc = { ...originalSvc };
                redeemSvc.name = `🎁 [Redeem] ${originalSvc.name} (${remaining} left)`;
                redeemSvc.price = 0;
                redeemSvc.default_price = 0;
                redeemSvc.center_override = null;
                this.services.unshift(redeemSvc);
              }
            }
          });
        }
      });
    }
    this.cdr.detectChanges();
    this.saveDraft();
  }



  loadClientHistory(clientId: number) {
    this.apiService.get(`billing/invoices/?client_id=${clientId}`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data: any) => {
      this.clientInvoices = data;
      this.buildClientHistory();
      this.cdr.detectChanges();
    });
  }

  loadClientAdvances(clientId: number) {
    this.apiService.get(`billing/advances/?client_id=${clientId}`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data: any) => {
      this.clientAdvances = data;
      this.clientAdvanceBalance = this.client?.advance_balance || 0;
      this.clientCashbackBalance = this.client?.cashback_balance || 0;
      this.buildClientHistory();
      this.cdr.detectChanges();
    });
  }



  buildClientHistory() {

    const history = [];

    for (const inv of this.clientInvoices) {

      history.push({

        type: 'Invoice',

        center: inv.client?.center_detail?.display_name || 'All Centers',

        date: new Date(inv.created_at),

        ref: inv.id,

        amount: inv.total_amount,

        status: inv.status

      });

    }

    for (const adv of this.clientAdvances) {

      history.push({

        type: 'Advance',

        center: adv.client?.center_detail?.display_name || 'All Centers',

        date: new Date(adv.created_at),

        ref: adv.id,

        amount: adv.amount

      });

    }

    history.sort((a, b) => b.date.getTime() - a.date.getTime());

    this.clientHistory = history;

    // Auto-detect membership based on true active status

    if (this.client && this.client.active_memberships && this.client.active_memberships.length > 0) {

      const am = this.client.active_memberships[0];

      const promoId = 'm_' + am.id;

      const promo = this.promotions.find((p: any) => p.id === promoId);

      if (promo) {

        this.selectedPromotion = promo;

        this.applyPromotion();

      }

    }



  }



  setAnonymousClient() {
    this.client = {
      id: null,
      first_name: 'Walk-in',
      last_name: 'Client',
      phone: '',
      email: '',
      gender: 'other',
      is_anonymous: true
    };
    this.searchPhone = '';
    
    // Switch to search tab if currently on a restricted tab
    if (['cards', 'packages', 'memberships', 'advance'].includes(this.activeTab)) {
      this.setActiveTab('search');
    }
  }

  newClient() {

    let defaultCenter = this.selectedCenterId;

    if (!defaultCenter && this.centers && this.centers.length > 0) {

      defaultCenter = this.centers[0].id;

    }

    this.client = {

      phone: this.searchPhone || '',

      app_pin: '',

      first_name: '',

      last_name: '',

      email: '',

      birthday: '',

      gst_number: '',

      notes: '',

      dnd_status: 'NOT ON DND',

      center: defaultCenter,

      gender: 'female'
    };

    // Reset client-specific data
    this.promotions = this.promotions.filter((p: any) => !p.id || !p.id.toString().startsWith('m_'));
    if (this.selectedPromotion && this.selectedPromotion.id && this.selectedPromotion.id.toString().startsWith('m_')) {
      this.selectedPromotion = null;
      this.applyPromotion();
    }
    this.clientAdvanceBalance = 0;
    this.clientCashbackBalance = 0;

  }



  saveClient() {
    if (!this.client || this.isSaving) {
      return;
    }

    if (!this.client.first_name || !this.client.phone) {
      this.showToast('First Name and Phone Number are required to save a client.', 'error');
      return;
    }

    this.isSaving = true;
    if (this.client.id) {
      this.apiService.updateClient(this.client.id, this.client).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.isSaving = false;
          this.showToast('Client updated', 'success');
          this.cdr.detectChanges();
        },
        error: (err: any) => {
          this.isSaving = false;
          this.showToast('Failed to update client.', 'error');
          console.error(err);
          this.cdr.detectChanges();
        }
      });
    } else {
      this.apiService.createClient(this.client).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (res: any) => {
          this.isSaving = false;
          this.client = res;
          this.showToast('Client created', 'success');
          this.cdr.detectChanges();
        },
        error: (err: any) => {
          this.isSaving = false;
          this.showToast('Failed to create client. Please check details.', 'error');
          console.error(err);
          this.cdr.detectChanges();
        }
      });
    }
  }



  // --- UI Tabs ---

  customPackageObj = { name: 'Custom Package', isCustom: true };



  setActiveTab(tab: 'search' | 'cards' | 'packages' | 'memberships' | 'advance') {

    this.activeTab = tab;
    this.cdr.detectChanges();

    if (tab === 'search') {

      this.selectedItemForConfig = null;

      this.configType = null;

    } else if (tab === 'cards') {

      this.configType = 'card';

      this.selectedItemForConfig = this.cards.length > 0 ? this.cards[0] : {};
      this.onConfigSelectionChange();

    } else if (tab === 'packages') {

      this.configType = 'package';

      this.selectedItemForConfig = this.customPackageObj;

      this.onPackageSelectionChange();

    } else if (tab === 'memberships') {

      this.configType = 'membership';

      this.selectedItemForConfig = this.memberships.length > 0 ? this.memberships[0] : {};
      this.onConfigSelectionChange();

    } else if (tab === 'advance') {

      this.configType = 'advance';

      this.selectedItemForConfig = { isAdvance: true };
      this.onConfigSelectionChange();

    }

  }




  onConfigSelectionChange() {
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
    } else {
      this.finalConfigPrice = 0;
    }
  }

  onPackageSelectionChange() {


    this.packageSelectedServices = [];

    this.finalConfigPrice = 0;

    this.packageSearchTerm = '';



    if (this.selectedItemForConfig && this.selectedItemForConfig.id) {

      this.finalConfigPrice = this.selectedItemForConfig.price || 0;

      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {
        this.packageSelectedServices = this.selectedItemForConfig.services_json.map((s: any) => {
          const svcId = s.service_id || s.id;
          let svcPrice = s.price || 0;
          if (!svcPrice && svcId) {
            const matchSvc = this.services.find(svc => svc.id === Number(svcId));
            if (matchSvc) svcPrice = matchSvc.price || matchSvc.default_price || 0;
          }
          return {
            id: svcId,
            name: s.service_name || s.name,
            price: svcPrice,
            pkgQty: s.quantity || s.pkgQty || 1
          };
        });
      }

    }

  }



  get filteredServices() {
    const search = (this.serviceSearchTerm || '').toLowerCase();
    if (!search) return [];
    return this.services.filter((item: any) => item.name?.toLowerCase().includes(search));
  }

  get filteredServicesDropdown() {
    const search = (this.serviceSearchTerm || '').toLowerCase();
    if (!search) return this.services.slice(0, 100);
    return this.services.filter((item: any) => item.name?.toLowerCase().includes(search)).slice(0, 100);
  }

  get filteredProducts() {
    const search = (this.productSearchTerm || '').toLowerCase();
    if (!search) return [];
    return this.products.filter((item: any) => item.name?.toLowerCase().includes(search));
  }

  get filteredProductsDropdown() {
    const search = (this.productSearchTerm || '').toLowerCase();
    if (!search) return this.products.slice(0, 100);
    return this.products.filter((item: any) => item.name?.toLowerCase().includes(search)).slice(0, 100);
  }



  get filteredMemberships() {

    return this.memberships.filter(m => m.is_active !== false);

  }



  get filteredPackages() {

    return this.packages.filter(p => p.is_active !== false);

  }



  get filteredCards() {

    return this.cards.filter(c => c.is_active !== false);

  }



  get filteredPromotions() {

    return this.promotions.filter(p => p.is_active !== false);

  }





  getEffectivePrice(item: any): number {
    if (!item) return 0;

    const parseNum = (val: any) => {
      if (val === undefined || val === null || val === '') return undefined;
      if (typeof val === 'string') {
        const parsed = Number(val.replace(/,/g, ''));
        return isNaN(parsed) ? undefined : parsed;
      }
      const parsed = Number(val);
      return isNaN(parsed) ? undefined : parsed;
    };

    const overridePrice = parseNum(item?.center_override?.price);
    if (overridePrice !== undefined) return overridePrice;

    const candidates = [
      item?.price,
      item?.post_tax_price,
      item?.pre_tax_price,
      item?.default_price,
      item?.selling_price,
      item?.price_amount,
      item?.value
    ];

    for (let c of candidates) {
      const num = parseNum(c);
      if (num !== undefined && num !== null) return num;
    }

    return 0;
  }

  getItemTaxAmount(item: any): number {
    const taxPct = Number(item.tax_percentage) || 0;
    if (taxPct <= 0) return 0;
    
    // total_price includes discount: ((unit_price * qty) - discount)
    const qty = Number(item.quantity) || 1;
    const unitPrice = Number(item.unit_price) || 0;
    const discount = Number(item.discount) || 0;
    
    let total = (unitPrice * qty) - discount;
    if (total < 0) total = 0;
    
    // Exclusive tax: calculate tax on top of the base total
    return total * (taxPct / 100);
  }







  isStaffSelected(id: any): boolean {
    return this.configStaffIds.includes(Number(id));
  }

  toggleStaffSelection(id: any) {
    const numId = Number(id);
    if (this.configStaffIds.includes(numId)) {
      this.configStaffIds = this.configStaffIds.filter(x => x !== numId);
    } else {
      this.configStaffIds = [...this.configStaffIds, numId];
    }
    this.cdr.detectChanges();
  }





  applyPromotion() {
    if (!this.selectedPromotion) {
      this.invoiceDiscount = 0;
      this.calcTaxes();
      return;
    }

    let discount = 0;

    let preTaxSubtotal = 0;
    for (const it of this.cart) {
      const qty = Number(it.quantity) || 1;
      const unitPrice = Number(it.unit_price) || 0;
      preTaxSubtotal += (unitPrice * qty);
    }

    const promo = this.selectedPromotion;
    const config = promo.config || {};

    // Support legacy/root properties for Memberships
    if (promo.id && promo.id.toString().startsWith('m_')) {
      const dPercent = Number(promo.discount_percent) || 0;
      discount = (preTaxSubtotal * dPercent) / 100;
    } 
    else if (promo.promo_type === 'Trigger' && config.trigger_services?.length === 2) {
      const svc1 = config.trigger_services[0];
      const svc2 = config.trigger_services[1];
      const triggerDiscountPct = Number(config.trigger_discount) || 0;

      const hasSvc1 = this.cart.some(c => c.description === svc1 || c.name === svc1);
      const cartSvc2 = this.cart.find(c => c.description === svc2 || c.name === svc2);

      if (hasSvc1 && cartSvc2) {
        discount = (cartSvc2.unit_price * triggerDiscountPct) / 100;
      }
    } 
    else if (promo.promo_type === 'FlatPrice') {
      const flatPrice = Number(config.flat_price) || 0;
      if (config.target === 'Specific Service' && config.specific_service) {
        const targetSvc = this.cart.find(c => c.description === config.specific_service || c.name === config.specific_service);
        if (targetSvc && targetSvc.unit_price > flatPrice) {
           discount = (targetSvc.unit_price - flatPrice) * (Number(targetSvc.quantity) || 1);
        }
      } else {
        // Overall Bill Flat Price
        if (preTaxSubtotal > flatPrice) {
          discount = preTaxSubtotal - flatPrice;
        }
      }
    }
    else if (promo.promo_type === 'Discount') {
      // The DB uses promo.discount_type and promo.discount_value (if set) 
      // but they can also be in config.discount_type / config.discount_value
      const dType = promo.discount_type || config.discount_type;
      const dValue = Number(promo.discount_value || config.discount_value) || 0;
      
      if (config.target === 'Specific Service' && config.specific_service) {
        const targetSvc = this.cart.find(c => c.description === config.specific_service || c.name === config.specific_service);
        if (targetSvc) {
          const itemTotal = targetSvc.unit_price * (Number(targetSvc.quantity) || 1);
          if (dType === 'Percentage') {
             discount = (itemTotal * dValue) / 100;
          } else {
             discount = dValue;
          }
        }
      } else {
        // Overall Bill Discount
        if (dType === 'Percentage') {
          discount = (preTaxSubtotal * dValue) / 100;
        } else {
          discount = dValue;
        }
      }
    }

    // Cap discount at subtotal to avoid negative totals
    if (discount > preTaxSubtotal) {
      discount = preTaxSubtotal;
    }

    this.invoiceDiscount = discount;
    this.calcTaxes();
  }



  openCheckoutModal() {
    if (!this.client || (!this.client.id && !this.client.is_anonymous)) {
      this.showToast('Please select or create a client first.', 'error');
      return;
    }
    
    if (this.client.is_blacklisted) {
      this.showToast('This client is blacklisted and cannot be billed.', 'error');
      return;
    }
    const missingStaff = this.cart.some((c: any) => !c.staff_members || c.staff_members.length === 0);
    if (missingStaff) {
      this.showToast('Please select at least one staff member for each item before finalizing.', 'error');
      return;
    }
    this.applyPromotion(); // Re-apply to ensure exact math

    if (this.client.is_anonymous) {
      this.clientAdvanceBalance = 0;
      this.clientCashbackBalance = 0;
      this.checkoutPayments = [{ method: 'Cash', amount: this.finalTotalAmount }];
      this.showCheckoutModal = true;
      this.calcCheckoutRemaining();
      this.cdr.detectChanges();
      return;
    }

    // Refresh advance balance from server before showing checkout
    this.apiService.get(`clients/api/clients/${this.client.id}/`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (c: any) => {
        if (c && c.advance_balance !== undefined) {
          this.clientAdvanceBalance = c.advance_balance;
          this.clientCashbackBalance = c.cashback_balance;
          this.client.advance_balance = c.advance_balance;
        }
        this.checkoutPayments = [{ method: 'Cash', amount: this.finalTotalAmount }];
        this.showCheckoutModal = true;
        this.calcCheckoutRemaining();
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.showToast('Failed to sync client balances.', 'error');
        // still open it, just assume 0
        this.checkoutPayments = [{ method: 'Cash', amount: this.finalTotalAmount }];
        this.showCheckoutModal = true;
        this.calcCheckoutRemaining();
        this.cdr.detectChanges();
      }
    });
  }


  checkoutTipAmount: number = 0;

  addPaymentRow() {
    this.calcCheckoutRemaining();
    const remaining = this.checkoutRemaining > 0 ? this.checkoutRemaining : 0;
    this.checkoutPayments.push({ method: 'UPI', amount: remaining });
    this.calcCheckoutRemaining();
  }

  removePaymentRow(index: number) {

    this.checkoutPayments.splice(index, 1);

    this.calcCheckoutRemaining();

  }



  calcCheckoutRemaining() {
    let sum = 0;
    this.checkoutPayments.forEach(p => sum += Number(p.amount || 0));
    this.checkoutRemaining = (this.finalTotalAmount + Number(this.checkoutTipAmount || 0)) - sum;
  }

  get canCompleteSale(): boolean {
    if (this.isSaving) return false;
    if (this.client?.is_blacklisted) return false;
    if (this.checkoutRemaining > 0) return false;
    if (this.checkoutRemaining < 0) {
      // Allow negative remaining ONLY if Cash is present and covers the overpayment amount
      const cashPayments = this.checkoutPayments.filter(p => p.method === 'Cash');
      let cashTotal = 0;
      cashPayments.forEach(p => cashTotal += Number(p.amount || 0));
      const overpayment = Math.abs(this.checkoutRemaining);
      if (cashTotal < overpayment) {
        return false;
      }
    }
    return true;
  }



  closeCheckoutModal() {

    this.showCheckoutModal = false;

  }



  // --- Cart & Invoice Logic ---

  openConfig(item: any, type: 'service' | 'product' | 'card' | 'advance' | 'package' | 'membership') {
    if (type === 'product' && item.current_stock !== undefined && item.current_stock <= 0) {
      this.showToast('This product is out of stock and cannot be selected.', 'error');
      return;
    }
    this.selectedItemForConfig = item;
    this.configType = type;
    this.resetConfig();
    this.cdr.detectChanges();
  }

  deleteHeldCart(hc: any) {
    if (!confirm("Are you sure you want to delete this held cart?")) return;
    this.heldCarts = this.heldCarts.filter((c: any) => c.id !== hc.id);
    localStorage.setItem('held_carts', JSON.stringify(this.heldCarts));
    if (this.heldCarts.length === 0) {
      this.showHeldCartsModal = false;
    }
    this.cdr.detectChanges();
  }

  resetConfig() {
    this.managerDiscountPercent = 0;
    this.managerDiscountAmount = 0;
    this.configStaffIds = [];
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {
        this.packageSelectedServices = this.selectedItemForConfig.services_json.map((s: any) => {
          const svcId = s.service_id || s.id;
          let svcPrice = s.price || 0;
          if (!svcPrice && svcId) {
            const matchSvc = this.services.find(svc => svc.id === Number(svcId));
            if (matchSvc) svcPrice = matchSvc.price || matchSvc.default_price || 0;
          }
          return {
            id: svcId,
            name: s.service_name || s.name,
            price: svcPrice,
            pkgQty: s.quantity || s.pkgQty || 1
          };
        });
      } else {
        this.packageSelectedServices = [];
      }
    }
  }

  recalcConfigPrice() {

    if (!this.selectedItemForConfig) return;

    const base = this.getEffectivePrice(this.selectedItemForConfig);

    const afterPct = base - (base * (this.managerDiscountPercent / 100));
    this.finalConfigPrice = Math.max(0, afterPct - this.managerDiscountAmount);

  }



  confirmAddToCart() {
    if (this.configType !== 'advance' && this.configStaffIds.length === 0) {
      this.showToast('Please select at least one staff member before adding to cart.', 'error');
      return;
    }

    if (this.selectedItemForConfig?.name && this.selectedItemForConfig.name.includes('🎁 [Redeem]')) {
      const match = this.selectedItemForConfig.name.match(/\((\d+)\s+left\)/);
      if (match && match[1]) {
        const maxAllowed = parseInt(match[1], 10);
        const existingCount = this.cart.filter(c => c.description === this.selectedItemForConfig.name)
          .reduce((sum, c) => sum + c.quantity, 0);
        if (existingCount + 1 > maxAllowed) {
          this.showToast(`You can only redeem up to ${maxAllowed} of this service.`, 'error');
          return;
        }
      }
    }

    if (this.configType === 'product' && this.selectedItemForConfig?.current_stock !== undefined) {
      const stock = this.selectedItemForConfig.current_stock;
      const existingCount = this.cart.filter(c => c.object_id === this.selectedItemForConfig.id && c.content_type === 'inventory.product')
        .reduce((sum, c) => sum + c.quantity, 0);
      if (existingCount + 1 > stock) {
        this.showToast(`Only ${stock} left in stock.`, 'error');
        return;
      }
    }

    if (this.configType === 'advance') {
      const entry = {
        content_type: 'advance',
        object_id: null,
        description: this.advanceDescription || 'Advance Payment',
        unit_price: this.advanceAmount || 0,
        discount: 0,
        manager_discount: 0,
        quantity: 1,
        staff: this.configStaffIds.length > 0 ? this.configStaffIds[0] : null,
        staff_members: this.configStaffIds
      };

      this.cart.push(entry);

    } else if (this.selectedItemForConfig) {

      // Map frontend configType to backend content_type

      let ct = 'services.servicemaster';

      if (this.configType === 'product') ct = 'inventory.product';

      else if (this.configType === 'card') ct = 'marketing.valuecard';

      else if (this.configType === 'package') ct = 'marketing.package';

      else if (this.configType === 'membership') ct = 'marketing.membership';



      let basePrice = this.getEffectivePrice(this.selectedItemForConfig);
      let discount = basePrice - this.finalConfigPrice;

      // Handle custom packages or when package price is increased
      if (this.configType === 'package') {
        if (!this.selectedItemForConfig.id || discount < 0) {
          basePrice = this.finalConfigPrice;
          discount = 0;
        }
      }

      const entry = {
        content_type: ct,
        object_id: this.selectedItemForConfig.id,
        description: this.selectedItemForConfig.name || this.selectedItemForConfig.title || 'Item',
        unit_price: basePrice,
        discount: discount > 0 ? discount : 0,
        manager_discount: discount > 0 ? discount : 0,
        quantity: 1,
        tax_percentage: ct === 'services.servicemaster' ? (this.selectedItemForConfig.tax_percentage || 0) : 
                        ct === 'inventory.product' ? (this.selectedItemForConfig.gst_percent || 0) : 0,

        staff_members: [...this.configStaffIds],
        custom_package_services: (this.configType === 'package' && !this.selectedItemForConfig.id) ? [...this.packageSelectedServices] : undefined,
        current_stock: this.configType === 'product' ? this.selectedItemForConfig.current_stock : undefined

      };

      this.cart.push(entry);

    }

    this.packageSelectedServices = [];



    // Reset state after adding

    this.selectedItemForConfig = null;
    this.configType = null;
    this.activeTab = 'search';
    this.serviceSearchTerm = '';
    this.productSearchTerm = '';
    this.showServiceDropdown = false;
    this.showProductDropdown = false;

    this.advanceAmount = 0;

    this.advanceDescription = '';
    this.calcTaxes();

  }



  get packageFilteredServices() {

    const term = this.packageSearchTerm.toLowerCase();

    if (!term) return [];

    return this.services.filter(s => s.name?.toLowerCase().includes(term));

  }



  addServiceToPackage(service: any) {

    this.packageSelectedServices.push({ ...service, pkgQty: 1 });

    this.packageSearchTerm = '';

  }



  removeServiceFromPackage(index: number) {

    this.packageSelectedServices.splice(index, 1);

  }



  getStaffName(staffId: number | string): string {

    const st = this.staffMembers.find((s: any) => s.id == staffId);

    return st ? `${st.first_name} ${st.last_name || ''}`.trim() : 'Unknown Staff';

  }

  // Helper to get today's date for template comparisons
  get today(): Date {
    return new Date();
  }

  // Returns service IDs from a ClientPackage's services_remaining map (for *ngFor)
  getPackageServiceKeys(ap: any): string[] {
    if (!ap || !ap.services_remaining) return [];
    return Object.keys(ap.services_remaining);
  }

  // Look up a service name by its numeric ID
  getServiceName(svcId: number): string {
    const svc = this.services.find((s: any) => s.id === svcId);
    return svc ? svc.name : `Service #${svcId}`;
  }

  // Safely check if an expiry date string is in the past
  isExpired(expiryDate: string | null | undefined): boolean {
    if (!expiryDate) return false;
    return new Date(expiryDate) < new Date();
  }

  addRedeemableServiceToCart(svcId: string, ap: any) {
    const remaining = ap.services_remaining[svcId];
    if (remaining <= 0) return;

    const originalSvc = this.services.find(s => s.id === Number(svcId) && s.name && !s.name.includes('🎁'));
    if (!originalSvc) {
      this.showToast('Service not found in master list.', 'error');
      return;
    }

    // Dynamically create the redeem service config to avoid relying on array injection state
    const redeemSvc = { ...originalSvc };
    redeemSvc.name = `🎁 [Redeem] ${originalSvc.name} (${remaining} left)`;
    redeemSvc.price = 0;
    redeemSvc.default_price = 0;
    redeemSvc.center_override = null;

    this.openConfig(redeemSvc, 'service');
  }

  removeFromCart(i: number) {

    this.cart.splice(i, 1);
    this.applyPromotion();
    this.calcTaxes();

  }

  updateQuantity(index: number, change: number) {
    if (this.currentInvoiceStatus !== 'draft') return;
    const item = this.cart[index];

    if (change > 0 && item.description && item.description.includes('🎁 [Redeem]')) {
      const match = item.description.match(/\((\d+)\s+left\)/);
      if (match && match[1]) {
        const maxAllowed = parseInt(match[1], 10);
        if (item.quantity + change > maxAllowed) {
          this.showToast(`You can only redeem up to ${maxAllowed} of this service.`, 'error');
          return;
        }
      }
    }

    if (change > 0 && item.content_type === 'inventory.product') {
      if (item.current_stock !== undefined) {
        const existingCount = this.cart.filter(c => c.object_id === item.object_id && c.content_type === 'inventory.product')
          .reduce((sum, c) => sum + c.quantity, 0);
        if (existingCount + change > item.current_stock) {
          this.showToast(`Only ${item.current_stock} left in stock.`, 'error');
          return;
        }
      }
    }

    if (item.quantity + change >= 1) {
      item.quantity += change;
      this.calcTaxes();
    }
  }

  onQuantityDirectChange(index: number) {
    if (this.currentInvoiceStatus !== 'draft') return;
    const item = this.cart[index];
    if (!item) return;
    
    let parsed = parseInt(item.quantity, 10);
    if (isNaN(parsed) || parsed < 1) {
      parsed = 1;
    }
    if (parsed > 9999) {
      parsed = 9999;
    }
    item.quantity = parsed;
    
    // Redeem validation
    if (item.description && item.description.includes('🎁 [Redeem]')) {
      const match = item.description.match(/\((\d+)\s+left\)/);
      if (match && match[1]) {
        const maxAllowed = parseInt(match[1], 10);
        if (item.quantity > maxAllowed) {
          item.quantity = maxAllowed;
          this.showToast(`You can only redeem up to ${maxAllowed} of this service.`, 'error');
        }
      }
    }

    // Product stock validation
    if (item.content_type === 'inventory.product' && item.current_stock !== undefined) {
      const otherItemsCount = this.cart
        .filter((c, idx) => idx !== index && c.object_id === item.object_id && c.content_type === 'inventory.product')
        .reduce((sum, c) => sum + Number(c.quantity || 0), 0);
      if (otherItemsCount + item.quantity > item.current_stock) {
        item.quantity = Math.max(1, item.current_stock - otherItemsCount);
        this.showToast(`Only ${item.current_stock} left in stock.`, 'error');
      }
    }

    this.calcTaxes();
  }

  extractApiError(err: any, defaultMsg: string = 'Operation failed'): string {
    if (!err) return defaultMsg;
    if (typeof err === 'string') return err;
    const errorData = err.error || err;
    if (typeof errorData === 'string') return errorData;
    if (errorData.detail) return errorData.detail;
    if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors) && errorData.non_field_errors.length > 0) {
      return errorData.non_field_errors.join(', ');
    }
    if (Array.isArray(errorData) && errorData.length > 0) {
      return errorData.map((e: any) => typeof e === 'string' ? e : JSON.stringify(e)).join(', ');
    }
    if (typeof errorData === 'object') {
      const messages: string[] = [];
      for (const [key, val] of Object.entries(errorData)) {
        if (Array.isArray(val)) {
          messages.push(`${key}: ${(val as any[]).join(', ')}`);
        } else if (typeof val === 'string') {
          messages.push(`${key}: ${val}`);
        } else if (typeof val === 'object' && val !== null) {
          messages.push(`${key}: ${JSON.stringify(val)}`);
        }
      }
      if (messages.length > 0) return messages.join(' | ');
    }
    return err.message || defaultMsg;
  }

  get subtotalAmount() {

    return this.cart.reduce((s: any, c: any) => s + ((Number(c.unit_price || 0) * Number(c.quantity || 1)) - Number(c.discount || 0)), 0);

  }



  get totalItemDiscount() {

    return this.cart.reduce((s: any, c: any) => s + Number(c.discount || 0), 0) + Number(this.invoiceDiscount || 0);

  }



  get finalTotalAmount() {
    let sub = this.subtotalAmount - Number(this.invoiceDiscount || 0);
    let totalTax = Number(this.invoiceCGST || 0) + Number(this.invoiceSGST || 0);
    return Math.round(sub + totalTax); // Rounding applied natively
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    if (this.viewMode !== 'new-invoice') return;

    const currentTime = new Date().getTime();

    // Barcode Scanner logic (detect rapid typing ending in Enter)
    if (event.key.length === 1 && !event.ctrlKey && !event.altKey) {
      if (currentTime - this.lastBarcodeKeystrokeTime > 50) {
        this.barcodeBuffer = ''; // reset if typing slowly
      }
      this.barcodeBuffer += event.key;
      this.lastBarcodeKeystrokeTime = currentTime;
    } else if (event.key === 'Enter') {
      if (this.barcodeBuffer.length >= 3 && currentTime - this.lastBarcodeKeystrokeTime <= 50) {
        this.processBarcode(this.barcodeBuffer);
        this.barcodeBuffer = '';
        event.preventDefault();
        return;
      }
      this.barcodeBuffer = '';
    }

    if (event.key === 'F2') {
      event.preventDefault();
      if (this.clientSearchInput) this.clientSearchInput.nativeElement.focus();
    } else if (event.key === 'F4') {
      event.preventDefault();
      if (this.serviceSearchInput) {
        this.serviceSearchInput.nativeElement.focus();
        this.showServiceDropdown = true;
        this.activeTab = 'search';
      }
    } else if (event.key === 'F8' || (event.ctrlKey && event.key === 'Enter')) {
      event.preventDefault();
      if (this.cart.length > 0 && this.client && !this.client.is_anonymous) {
        this.openCheckoutModal();
      }
    } else if (event.key === 'Escape') {
      if (this.showCheckoutModal) {
        this.closeCheckoutModal();
      } else if (this.selectedItemForConfig) {
        this.selectedItemForConfig = null;
        this.configType = null;
        this.activeTab = 'search';
      } else {
        this.cart = [];
        this.cdr.detectChanges();
      }
    }
  }

  processBarcode(code: string) {
    const item = this.services.find(s =>
      (s.barcode && s.barcode === code) ||
      (s.id && s.id.toString() === code)
    );
    if (item) {
      this.openConfig(item, item.price ? 'service' : 'product'); // roughly guessing type
      // Auto confirm if it's a simple item without staff requirements
      setTimeout(() => {
        this.confirmAddToCart();
      }, 100);
    }
  }

  saveDraft() {
    if (this.currentInvoiceStatus !== 'draft') return;
    if (!this.cart || this.cart.length === 0) {
      this.clearDraft();
      return;
    }
    const draft = {
      cart: this.cart,
      client: this.client,
      selectedPromotion: this.selectedPromotion,
      managerDiscountPercent: this.managerDiscountPercent,
      managerDiscountAmount: this.managerDiscountAmount,
      activeTab: this.activeTab,
      configStaffIds: this.configStaffIds
    };
    localStorage.setItem('billing_draft', JSON.stringify(draft));
  }

  loadDraft() {
    // Silent draft restore without blocking browser confirm popups
    const d = localStorage.getItem('billing_draft');
    if (d) {
      try {
        const draft = JSON.parse(d);
        if (draft.cart && draft.cart.length > 0) {
          this.cart = draft.cart;
          this.client = draft.client;
          this.selectedPromotion = draft.selectedPromotion;
          this.managerDiscountPercent = draft.managerDiscountPercent;
          this.managerDiscountAmount = draft.managerDiscountAmount;
          this.activeTab = draft.activeTab;
          this.configStaffIds = draft.configStaffIds;
          this.calcTaxes();
        } else {
          this.clearDraft();
        }
      } catch (e) {
        this.clearDraft();
      }
    }

    // Also load held carts
    const held = localStorage.getItem('held_carts');
    if (held) {
      try {
        this.heldCarts = JSON.parse(held);
      } catch (e) { }
    }
  }

  clearDraft() {
    localStorage.removeItem('billing_draft');
  }

  holdCurrentCart() {
    if (this.cart.length === 0) return;
    this.heldCarts.push({
      id: new Date().getTime(),
      time: new Date(),
      client: this.client,
      cart: [...this.cart],
      total: this.finalTotalAmount
    });
    localStorage.setItem('held_carts', JSON.stringify(this.heldCarts));
    
    // Reset state without changing viewMode
    this.isSaving = false;
    this.cart = [];
    this.client = null;
    this.searchPhone = '';
    this.currentInvoiceId = null;
    this.currentInvoiceStatus = 'draft';
    this.invoiceDiscount = 0;
    this.invoiceCGST = 0;
    this.invoiceSGST = 0;
    this.useAdvancePayment = false;
    this.clearDraft();
    this.showToast('Cart placed on hold. Ready for next customer.', 'success');
  }

  resumeCart(heldCart: any) {
    if (this.cart.length > 0) {
      if (!confirm("Discard current cart to resume held cart?")) return;
    }
    this.setViewMode('new-invoice');
    this.currentInvoiceStatus = 'draft';
    this.client = heldCart.client || { name: 'Walk-in Client', contact_number: '' };
    this.selectedAppointmentId = heldCart.appointment || null;
    this.cart = heldCart.cart || [];
    this.heldCarts = this.heldCarts.filter(c => c.id !== heldCart.id);
    localStorage.setItem('held_carts', JSON.stringify(this.heldCarts));
    this.calcTaxes();
    this.showHeldCartsModal = false;
  }

  calcTaxes() {
    if (!this.cart || this.cart.length === 0) {
      this.invoiceCGST = 0;
      this.invoiceSGST = 0;
      this.invoiceDiscount = 0;
      this.clearDraft();
      return;
    }
    
    let subtotalBase = this.subtotalAmount; 
    let totalTax = 0;
    
    for (const it of this.cart) {
      let taxPct = Number(it.tax_percentage) || 0;
      if (taxPct > 0) {
          let qty = Number(it.quantity) || 1;
          let unitPrice = Number(it.unit_price) || 0;
          let itemDiscount = Number(it.discount) || 0;
          let itemTotal = (unitPrice * qty) - itemDiscount;
          if (itemTotal < 0) itemTotal = 0;
          
          if (subtotalBase > 0 && this.invoiceDiscount > 0) {
              let proportion = itemTotal / subtotalBase;
              let apportionedGlobalDiscount = this.invoiceDiscount * proportion;
              itemTotal -= apportionedGlobalDiscount;
              if (itemTotal < 0) itemTotal = 0;
          }
          
          totalTax += itemTotal * (taxPct / 100);
      }
    }
    
    let totalCGST = totalTax / 2;
    let totalSGST = totalTax / 2;
    
    this.invoiceCGST = parseFloat(totalCGST.toFixed(2));
    this.invoiceSGST = parseFloat(totalSGST.toFixed(2));
    this.saveDraft();
  }

  get roundingAmount() {
    let sub = this.subtotalAmount - Number(this.invoiceDiscount || 0);
    let totalTax = Number(this.invoiceCGST || 0) + Number(this.invoiceSGST || 0);
    let exact = sub + totalTax;
    let diff = Math.round(exact) - exact;
    return Number(diff.toFixed(2));
  }



  isSaving = false;

  saveInvoice(onHold: boolean) {
    if (this.isSaving) return;

    if (!this.client || (!this.client.id && !this.client.is_anonymous)) {

      this.showToast('Please select or create a client first.', 'error');

      return;

    }



    if (!onHold && this.useAdvancePayment) {

      if (this.clientAdvanceBalance < this.finalTotalAmount) {

        this.showToast("Insufficient Advance Balance to cover the total amount.", 'error');

        return;

      }

    }

    if (!onHold) {
      if (this.checkoutRemaining < 0) {
        this.showToast('Payment entered exceeds the total due. Please adjust the payment amount.', 'error');
        return;
      }
      if (this.checkoutRemaining > 0 && !this.useAdvancePayment) {
        this.showToast('Full payment is required to complete the invoice.', 'error');
        return;
      }
      // Do not close the modal here; let the user see the "SAVING..." state until the API returns
    }

    const payload: any = {

      client: this.client.is_anonymous ? null : this.client.id,

      center: this.selectedCenterId,

      notes: this.selectedPromotion ? `Promo Applied: ${this.selectedPromotion.name}` : '',

      subtotal: Number(this.subtotalAmount).toFixed(2),

      discount: Number(this.invoiceDiscount).toFixed(2),

      cgst: Number(this.invoiceCGST).toFixed(2),

      sgst: Number(this.invoiceSGST).toFixed(2),

      rounding: Number(this.roundingAmount).toFixed(2),

      total_amount: Number(this.finalTotalAmount).toFixed(2),

      paid_amount: onHold ? 0 : Number(this.finalTotalAmount + this.checkoutTipAmount).toFixed(2),

      tip_amount: Number(this.checkoutTipAmount).toFixed(2),

      status: onHold ? 'draft' : 'paid',

      promo_id: (this.selectedPromotion && !String(this.selectedPromotion.id).startsWith('m_')) ? this.selectedPromotion.id : null,
      membership_id: (this.selectedPromotion && String(this.selectedPromotion.id).startsWith('m_')) ? parseInt(String(this.selectedPromotion.id).replace('m_', ''), 10) : null,
      appointment: this.selectedAppointmentId,

      payments: onHold ? [] : this.checkoutPayments
        .filter((p: any) => Number(p.amount) > 0)
        .map((p: any) => {
          let method = p.method;
          if (method === 'Card') method = 'Credit Card';
          let vcId = null;
          if (method && method.startsWith('Value Card ')) {
            vcId = parseInt(method.replace('Value Card ', ''), 10);
            method = 'Value Card';
          }
          return { payment_method: method, amount: Number(p.amount), value_card_id: vcId };
        }),

      items: this.cart.map((c: any) => {
        return {
          content_type: c.content_type,
          object_id: c.object_id,
          description: c.description,
          unit_price: Number(c.unit_price).toFixed(2),
          discount: Number(c.discount).toFixed(2),
          manager_discount: Number(c.manager_discount || 0).toFixed(2),
          quantity: c.quantity,
          tax_percentage: Number(c.tax_percentage).toFixed(2),
          staff: c.staff,
          staff_members: c.staff_members,
          custom_package_services: c.custom_package_services
        };
      })

    };





    if (this.currentInvoiceId) {
      this.isSaving = true;
      this.apiService.put(`billing/invoices/${this.currentInvoiceId}/`, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (res: any) => {
          this.handlePostSave(onHold, res);
        },

        error: (err: any) => {
          this.isSaving = false;
          const errMsg = this.extractApiError(err, 'Failed to update invoice');
          this.showToast(errMsg, 'error');
          console.error(err);
        }
      });
    } else {
      this.isSaving = true;
      this.apiService.post(`billing/invoices/`, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (res: any) => {
          this.handlePostSave(onHold, res);
        },

        error: (err: any) => {
          this.isSaving = false;
          const errMsg = this.extractApiError(err, 'Failed to create invoice');
          this.showToast(errMsg, 'error');
          console.error(err);
        }

      });

    }

  }



  handlePostSave(onHold: boolean, invoice: any) {
    try {
      this.clearDraft();
      this.closeCheckoutModal();
      const advanceItem = this.cart.find(it => it.content_type === 'advance');

      const finish = () => {
        if (!onHold) {
          this.completedInvoiceData = invoice;
          this.showSuccessModal = true;
          
          // Clear cart immediately so background looks fresh
          this.cart = [];
          this.client = null;
          this.searchPhone = '';
          this.currentInvoiceId = null;
          this.currentInvoiceStatus = 'draft';
          this.invoiceDiscount = 0;
          this.invoiceCGST = 0;
          this.invoiceSGST = 0;
          this.useAdvancePayment = false;
          this.selectedPromotion = null;
          this.resetConfig();
          this.loadLandingData();
        } else {
          this.showToast('Draft saved successfully', 'success');
          // For save draft, we don't want to actually delete it, we just want to clear the UI.
          // Since discardInvoice now deletes the invoice, we should call finalizeDiscard() here instead!
          this.finalizeDiscard();
        }
        this.isSaving = false;
        setTimeout(() => this.cdr.detectChanges(), 0);
      };

      if (!onHold && advanceItem) {
        this.apiService.post('billing/advances/', {
          client: this.client.id,
          amount: advanceItem.unit_price * advanceItem.quantity,
          notes: advanceItem.description || 'Advance Payment'
        }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: () => finish(),
          error: (e) => { console.error('Advance error:', e); finish(); }
        });
      } else {
        finish();
      }
    } catch (e) {
      console.error('CRITICAL ERROR IN HANDLE POST SAVE:', e);
      this.isSaving = false;
      this.showToast('Error displaying receipt', 'error');
    }
  }





  payInvoice(invoice: any) {
    this.loadInvoice(invoice);
    this.openCheckoutModal();
  }

  loadInvoice(invoice: any) {

    if (invoice.status !== 'draft') {

      this.showToast('Can only load open (draft) invoices.', 'error');

      return;

    }

    this.setViewMode('new-invoice');

    this.currentInvoiceId = invoice.id;
    this.currentInvoiceStatus = invoice.status;





    // Assuming backend returns client details. If just ID, fetch client.
    if (invoice.client) {
      // Just fetch it by ID to be safe and populate all fields
      const clientId = typeof invoice.client === 'object' ? invoice.client.id : invoice.client;
      this.apiService.get(`clients/api/clients/${clientId}/`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((c: any) => {
        if (c && c.id) this.selectClient(c);
      });
    }

    this.cart = [];
    if (invoice.items) {
      invoice.items.forEach((it: any) => {
        let tax_percentage = 0;
        if (it.tax_percentage !== undefined && it.tax_percentage !== null) {
          tax_percentage = Number(it.tax_percentage);
        } else {
          if (it.content_type === 'services.servicemaster') {
            const svc = this.services.find((s: any) => s.id === it.object_id);
            if (svc) tax_percentage = svc.tax_percentage || 0;
          } else if (it.content_type === 'inventory.product') {
            const prod = this.products.find((p: any) => p.id === it.object_id);
            if (prod) tax_percentage = prod.gst_percent || 0;
          }
        }

        this.cart.push({
          content_type: it.content_type,
          object_id: it.object_id,
          id: it.object_id,
          name: it.description,
          description: it.description,
          unit_price: Number(it.unit_price),
          discount: Number(it.discount),
          manager_discount: Number(it.manager_discount || 0),
          quantity: it.quantity,
          tax_percentage: tax_percentage,
          staff: it.staff ? (it.staff.id || it.staff) : null,
          staff_members: (it.staff_members || []).map((s: any) => s.id)
        });
      });
    }

    this.invoiceDiscount = Number(invoice.discount);
    this.invoiceCGST = Number(invoice.cgst);
    this.invoiceSGST = Number(invoice.sgst);

    if (this.promotions && this.promotions.length > 0) {
      // Just let it manually override for now or auto-select if it matches
    }

    this.cdr.detectChanges();
  }

  viewInvoice(invoiceId: number) {
    this.isSaving = true;
    this.cdr.detectChanges();
    this.apiService.get(`billing/invoices/${invoiceId}/`).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (inv: any) => {
        this.completedInvoiceData = inv;
        this.showSuccessModal = true;
        this.isSaving = false;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.isSaving = false;
        this.cdr.detectChanges();
        this.showToast('Failed to load invoice details', 'error');
      }
    });
  }
  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

}
