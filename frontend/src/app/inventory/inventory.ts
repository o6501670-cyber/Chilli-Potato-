import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';
import { CsvService } from '../services/csv.service';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';

@Component({
  selector: 'app-inventory',
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './inventory.html',
  styleUrl: './inventory.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class InventoryComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  apiService = inject(ApiService);
  toastService = inject(ToastService);
  csvService = inject(CsvService);
  cdr = inject(ChangeDetectorRef);

  activeTab = 'Product Master';
  tabs = ['Checkout', 'Stock History', 'Purchase Orders', 'Product Master', 'Vendor Master', 'PO History', 'Audit'];

  isOwner = false;
  hasGlobalAccess = false;
  permissions: any = {};
  centers: any[] = [];
  selectedCenterId: number | null = null;

  products: any[] = [];
  topLowStock: any[] = [];
  fastMovers: any[] = [];
  totalValue: number = 0;
  vendors: any[] = [];
  purchaseOrders: any[] = [];

  newProduct: any = {
    product_id_str: '',
    product_code: '',
    name: '',
    brand: '',
    category: '',
    sub_category: '',
    vendor_name: '',
    is_active: true,
    price: null,
    gst_percent: 0,
    barcode: '',
    sac_code: '',
    reorder_level: 0,
    reorder_quantity: 0
  };

  newVendor: any = {
    vendor_code: '',
    name: '',
    short_name: '',
    phone: '',
    email: '',
    cst_number: '',
    pan_number: '',
    address: '',
    city: '',
    state: '',
    pin_code: '',
    mapped_products: []
  };

  showMappedVendorsOnly = false;
  selectedProduct: any = null;
  newLot: any = { lot_number: '', net_price: 0, mrp: 0, expiry_date: '' };

  newPO: any = {
    vendor_id: null,
    invoice_number: '',
    items: []
  };
  
  selectedPO: any = null;

  // Checkout Data
  checkoutSearchTerm: string = '';
  checkoutCurrentPage: number = 1;
  checkoutPageSize: number = 100;
  showInStockOnly: boolean = false;
  todayCheckouts: any[] = [];
  checkoutQuantities: { [key: number]: number } = {};

  // Audit Data
  auditSearchTerm: string = '';
  auditCurrentPage: number = 1;
  auditPageSize: number = 100;
  auditQuantities: { [key: number]: number } = {};

  // Product Master Data
  productMasterSearchTerm: string = '';
  productMasterCurrentPage: number = 1;
  productMasterPageSize: number = 100;
  
  // Stock History Data
  stockHistoryDates: string[] = [];
  selectedHistoryDate: string | null = null;
  selectedHistoryRecords: any[] = [];
  isLoadingHistory: boolean = false;
  isSaving: boolean = false;

  selectPO(po: any) {
    this.selectedPO = po;
    // Populate vendor details for display if missing
    if (po && po.vendor && !po.vendor_details) {
      const v = this.vendors.find(v => v.id === po.vendor);
      if (v) po.vendor_details = v;
    }
  }

  poStatuses = ['Draft', 'Finalized', 'Approved', 'Ordered', 'Shipped', 'Delivered'];

  updatePOStatus(newStatus: string) {
    if (!this.selectedPO || this.isSaving) return;

    const currentIndex = this.poStatuses.indexOf(this.selectedPO.status);
    const newIndex = this.poStatuses.indexOf(newStatus);
    
    // Prevent reverting to a previous status
    if (newIndex < currentIndex) {
      this.toastService.showError('Cannot revert to a previous status.');
      return;
    }

    // Already at this status
    if (newIndex === currentIndex) return;

    this.isSaving = true;
    this.apiService.updatePurchaseOrder(this.selectedPO.id, { status: newStatus }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
         this.selectedPO.status = newStatus;
         const po = this.purchaseOrders.find(p => p.id === this.selectedPO.id);
         if (po) po.status = newStatus;
         
         if (newStatus === 'Delivered') {
             this.loadData(); // Refresh stock instantly
         } else {
             this.cdr.detectChanges();
         }
         this.isSaving = false;
         this.toastService.showSuccess(`Purchase Order status updated to ${newStatus}`);
      },
      error: (err) => {
          this.toastService.showError('Failed to update status: ' + JSON.stringify(err.error));
          this.isSaving = false;
      }
    });
  }

  isStatusCompleted(status: string): boolean {
    if (!this.selectedPO) return false;
    const currentIndex = this.poStatuses.indexOf(this.selectedPO.status);
    const targetIndex = this.poStatuses.indexOf(status);
    return currentIndex >= targetIndex;
  }

  selectedVendor: any = null;
  activeCenterDetails: any = null;

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
      this.toastService.showError(String('Failed to parse user from localStorage') + ((e) ? ' ' + JSON.stringify(e) : ''));
    }
  }

  const availableTabs = [];
  if (this.isOwner || this.permissions.inventory?.checkout?.read) availableTabs.push('Checkout');
  if (this.isOwner || this.permissions.inventory?.stock_history?.read) availableTabs.push('Stock History');
  if (this.isOwner || this.permissions.inventory?.purchase_orders?.read) availableTabs.push('Purchase Orders');
  if (this.isOwner || this.permissions.inventory?.products?.read) availableTabs.push('Product Master');
  if (this.isOwner || this.permissions.inventory?.vendors?.read) availableTabs.push('Vendor Master');
  if (this.isOwner || this.permissions.inventory?.po_history?.read) availableTabs.push('PO History');
  if (this.isOwner || this.permissions.inventory?.audit?.read) availableTabs.push('Audit');

  this.tabs = availableTabs;
  if (this.tabs.length > 0 && !this.tabs.includes(this.activeTab)) {
    this.activeTab = this.tabs[0];
  }

  this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
    this.centers = data || [];
    if (this.isOwner) {
      if (this.centers.length > 0 && !this.selectedCenterId) {
        this.selectedCenterId = this.centers[0].id;
      }
    } else {
      this.selectedCenterId = user?.center_id || null;
      if (this.centers.length > 0 && !this.centers.some(c => c.id == this.selectedCenterId)) {
        this.selectedCenterId = this.centers[0].id;
      }
    }
    this.loadData();
  });
}

  onCenterChange() {
    this.loadData();
  }

  setTab(tab: string) {
    this.activeTab = tab;
  }

  loadData() {
    const cid = this.selectedCenterId ? this.selectedCenterId : undefined;
    
    // Load Fast Movers
    this.apiService.getUsageReport().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res: any) => {
          if (res && res.breakdown) {
              this.fastMovers = res.breakdown.filter((item: any) => item.service_type === 'Product');
              this.cdr.detectChanges();
          }
      },
      error: (err: any) => console.error('Failed to load breakdown:', err)
    });

    this.apiService.getProducts(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      // When "All Locations" selected (no cid), deduplicate by name/code so the same
      // product uploaded to multiple centers shows only once in the Product Master list.
      if (!cid) {
        const seen = new Set<string>();
        this.products = data.filter((p: any) => {
          const key = (p.product_code || p.product_id_str || p.name || '').toString().toLowerCase();
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      } else {
        this.products = data;
      }

      // Calculate Smart Metrics
      this.totalValue = this.products.reduce((sum, p) => sum + ((parseFloat(p.price) || 0) * (p.current_stock || 0)), 0);

      this.topLowStock = [...this.products]
          .filter(p => p.current_stock <= p.reorder_level)
          .map(p => ({ ...p, deficit: p.reorder_level - p.current_stock }))
          .sort((a, b) => b.deficit - a.deficit);

      this.cdr.detectChanges();
    });
    this.apiService.getVendors(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.vendors = data;
      this.cdr.detectChanges();
    });
    this.apiService.getPurchaseOrders(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.purchaseOrders = data;
      this.cdr.detectChanges();
    });
    this.apiService.getStockTransactions(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      // Filter for today's checkouts
      const today = new Date().toISOString().split('T')[0];
      this.todayCheckouts = data.filter(t => t.transaction_type === 'CHECKOUT' && t.created_at.startsWith(today));
      this.cdr.detectChanges();
    });

    this.generateStockHistoryDates();
    
    // Set active center details for the PO view
    if (cid && this.centers) {
      this.activeCenterDetails = this.centers.find(c => c.id == cid) || { center_name: `Center (ID: ${cid})`, address: '', phone: '', cst_number: '' };
    } else {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const u = JSON.parse(userStr);
        this.activeCenterDetails = { center_name: `Assigned Center (ID: ${u.center_id})`, address: '', phone: '', cst_number: '' };
      }
    }
  }

  onVendorSelect() {
    if (this.newPO.vendor_id) {
      this.selectedVendor = this.vendors.find(v => v.id == this.newPO.vendor_id);
    } else {
      this.selectedVendor = null;
    }
  }

  addPOItem() {
    this.newPO.items.push({
      product_id: null,
      quantity: 1,
      rate: 0,
      discount_percent: 0,
      tax_percent: 0
    });
  }

  removePOItem(index: number) {
    this.newPO.items.splice(index, 1);
  }

  onProductSelect(item: any) {
    if (item.product_id) {
      const prod = this.products.find(p => p.id == item.product_id);
      if (prod) {
        item.rate = prod.price;
      }
    }
  }

  getVendorProducts() {
    if (!this.selectedVendor || !this.selectedVendor.mapped_products || this.selectedVendor.mapped_products.length === 0) {
      return this.products; // Fallback to all if none mapped
    }
    return this.products.filter(p => this.selectedVendor.mapped_products.includes(p.id));
  }

  getProductName(productId: number): string {
    const prod = this.products.find(p => p.id === productId);
    return prod ? prod.name : 'Unknown';
  }

  getProductProperty(productId: number, prop: string): any {
    const prod = this.products.find(p => p.id === productId);
    return prod && prod[prop] ? prod[prop] : '-';
  }

  get masterFilteredProducts() {
    let filtered = this.products;
    if (this.productMasterSearchTerm) {
      const s = this.productMasterSearchTerm.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(s) || (p.product_code && p.product_code.toLowerCase().includes(s)) || (p.barcode && p.barcode.toLowerCase().includes(s)));
    }
    return filtered;
  }

  get masterPaginatedProducts() {
     const filtered = this.masterFilteredProducts;
     const startIndex = (this.productMasterCurrentPage - 1) * this.productMasterPageSize;
     return filtered.slice(startIndex, startIndex + this.productMasterPageSize);
  }

  get productMasterTotalPages() {
     return Math.max(1, Math.ceil(this.masterFilteredProducts.length / this.productMasterPageSize));
  }

  nextProductMasterPage() {
    if (this.productMasterCurrentPage < this.productMasterTotalPages) {
      this.productMasterCurrentPage++;
    }
  }

  prevProductMasterPage() {
    if (this.productMasterCurrentPage > 1) {
      this.productMasterCurrentPage--;
    }
  }

  onProductMasterSearch() {
    this.productMasterCurrentPage = 1;
  }

  calculateItemTotal(item: any): number {
    const base = item.quantity * item.rate;
    const discountAmount = base * (item.discount_percent / 100);
    const subtotal = base - discountAmount;
    const taxAmount = subtotal * (item.tax_percent / 100);
    return subtotal + taxAmount;
  }

  calculatePOTotal(): number {
    let total = 0;
    for (let item of this.newPO.items) {
      total += this.calculateItemTotal(item);
    }
    return total;
  }

  createPurchaseOrder() {
    if (this.isSaving) return;
    if (!this.newPO.vendor_id) {
      this.toastService.showError('Please select a vendor');
      return;
    }
    if (this.newPO.items.length === 0) {
      this.toastService.showError('Please add at least one product');
      return;
    }

    this.isSaving = true;
    const payload = {
      vendor: this.newPO.vendor_id,
      invoice_number: this.newPO.invoice_number,
      total_amount: this.calculatePOTotal(),
      status: 'Draft',
      items: this.newPO.items.map((i: any) => ({
        product: i.product_id,
        quantity: i.quantity,
        rate: i.rate,
        discount_percent: i.discount_percent,
        tax_percent: i.tax_percent,
        total_price: this.calculateItemTotal(i)
      }))
    } as any;

    if (this.selectedCenterId) {
      payload.center = Number(this.selectedCenterId);
    }

    if (this.newPO.id) {
      this.apiService.updatePurchaseOrder(this.newPO.id, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newPO = { vendor_id: null, invoice_number: '', items: [] };
          this.selectedVendor = null;
          this.isSaving = false;
          this.toastService.showSuccess('Purchase Order Updated Successfully!');
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to update Purchase Order: ' + JSON.stringify(err.error));
        }
      });
    } else {
      this.apiService.createPurchaseOrder(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newPO = { vendor_id: null, invoice_number: '', items: [] };
          this.selectedVendor = null;
          this.isSaving = false;
          this.toastService.showSuccess('Purchase Order Created Successfully!');
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to create Purchase Order: ' + JSON.stringify(err.error));
        }
      });
    }
  }

  editPO() {
    if (!this.selectedPO) return;
    this.newPO = {
      id: this.selectedPO.id,
      vendor_id: this.selectedPO.vendor,
      invoice_number: this.selectedPO.invoice_number,
      items: this.selectedPO.items.map((i: any) => ({
        product_id: i.product,
        quantity: i.quantity,
        rate: i.rate,
        discount_percent: i.discount_percent,
        tax_percent: i.tax_percent
      }))
    };
    this.onVendorSelect();
    this.selectedPO = null;
  }

  deletePO(id: number) {
    if (!confirm('Are you sure you want to delete this Purchase Order?')) return;
    this.apiService.deletePurchaseOrder(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.loadData();
        if (this.selectedPO?.id === id) this.selectedPO = null;
      },
      error: (err) => this.toastService.showError('Failed to delete Purchase Order: ' + JSON.stringify(err.error))
    });
  }

  editProduct(p: any) {
    this.newProduct = { ...p };
    this.selectedProduct = p;
  }

  deleteProduct(id: number) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    this.apiService.deleteProduct(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.loadData();
        if (this.selectedProduct?.id === id) this.selectedProduct = null;
      },
      error: (err) => this.toastService.showError('Failed to delete: ' + JSON.stringify(err.error))
    });
  }

  addProductLot() {
    if (!this.selectedProduct || this.isSaving) return;
    this.isSaving = true;
    const lotPayload = { ...this.newLot, product: this.selectedProduct.id };
    if (!lotPayload.expiry_date) lotPayload.expiry_date = null;
    this.apiService.createProductLot(lotPayload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.loadData(); // Re-fetches products to update selectedProduct's lots
        this.newLot = { lot_number: '', net_price: 0, mrp: 0, expiry_date: '' };
        this.isSaving = false;
        this.toastService.showSuccess('Lot added successfully');
      },
      error: (err) => {
          this.toastService.showError('Failed to add lot: ' + JSON.stringify(err.error));
          this.isSaving = false;
      }
    });
  }

  deleteLot(id: number) {
    if (!confirm('Delete this lot?')) return;
    this.apiService.deleteProductLot(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.loadData(),
      error: (err) => this.toastService.showError('Failed to delete lot: ' + JSON.stringify(err.error))
    });
  }

  addProduct() {
    if (this.isSaving) return;
    const payload = { ...this.newProduct };
    if (this.selectedCenterId) {
      payload.center = Number(this.selectedCenterId);
    } else {
      payload.create_all_centers = true;
    }
    
    this.isSaving = true;
    if (this.newProduct.id) {
      const updateAllCenters = !this.selectedCenterId;
      this.apiService.updateProduct(this.newProduct.id, payload, updateAllCenters).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newProduct = { product_id_str: '', product_code: '', name: '', brand: '', category: '', sub_category: '', vendor_name: '', is_active: true, price: null, gst_percent: 0, barcode: '', sac_code: '', reorder_level: 0, reorder_quantity: 0 };
          this.isSaving = false;
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to update product: ' + JSON.stringify(err.error));
        }
      });
    } else {
      this.apiService.createProduct(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newProduct = { product_id_str: '', product_code: '', name: '', brand: '', category: '', sub_category: '', vendor_name: '', is_active: true, price: null, gst_percent: 0, barcode: '', sac_code: '', reorder_level: 0, reorder_quantity: 0 };
          this.isSaving = false;
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to create product: ' + JSON.stringify(err.error));
        }
      });
    }
  }

  get filteredVendors() {
    if (this.showMappedVendorsOnly) {
      return this.vendors.filter(v => v.mapped_products && v.mapped_products.length > 0);
    }
    return this.vendors;
  }

  editVendor(v: any) {
    this.newVendor = { ...v, mapped_products: v.mapped_products || [] };
    this.selectedVendor = v;
  }

  toggleVendorMapping(productId: number) {
    if (!this.newVendor) return;
    if (!this.newVendor.mapped_products) this.newVendor.mapped_products = [];
    
    const index = this.newVendor.mapped_products.indexOf(productId);
    if (index > -1) {
      this.newVendor.mapped_products.splice(index, 1);
    } else {
      this.newVendor.mapped_products.push(productId);
    }
  }

  deleteVendor(id: number) {
    if (!confirm('Are you sure you want to delete this vendor?')) return;
    this.apiService.deleteVendor(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.loadData(),
      error: (err) => this.toastService.showError('Failed to delete: ' + JSON.stringify(err.error))
    });
  }

  addVendor() {
    if (this.isSaving) return;
    const payload = { ...this.newVendor };
    if (this.selectedCenterId) {
      payload.center = Number(this.selectedCenterId);
    } else if (this.centers && this.centers.length > 0) {
      payload.center = this.centers[0].id;
    } else {
      this.toastService.showError('Error: A center must be selected to add a vendor.');
      return;
    }
    
    this.isSaving = true;
    if (this.newVendor.id) {
      this.apiService.updateVendor(this.newVendor.id, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newVendor = { vendor_code: '', name: '', short_name: '', phone: '', email: '', cst_number: '', pan_number: '', address: '', city: '', state: '', pin_code: '', mapped_products: [] };
          this.isSaving = false;
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to update vendor: ' + JSON.stringify(err.error));
        }
      });
    } else {
      this.apiService.createVendor(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadData();
          this.newVendor = { vendor_code: '', name: '', short_name: '', phone: '', email: '', cst_number: '', pan_number: '', address: '', city: '', state: '', pin_code: '', mapped_products: [] };
          this.isSaving = false;
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError('Failed to create vendor: ' + JSON.stringify(err.error));
        }
      });
    }
  }

  // Checkout Logic
  get checkoutFilteredProducts() {
    let filtered = this.products;
    if (this.showInStockOnly) {
      filtered = filtered.filter(p => p.current_stock > 0);
    }
    if (this.checkoutSearchTerm) {
      const s = this.checkoutSearchTerm.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(s) || (p.barcode && p.barcode.toLowerCase().includes(s)));
    }
    return filtered;
  }

  get checkoutPaginatedProducts() {
     const filtered = this.checkoutFilteredProducts;
     const startIndex = (this.checkoutCurrentPage - 1) * this.checkoutPageSize;
     return filtered.slice(startIndex, startIndex + this.checkoutPageSize);
  }

  get checkoutTotalPages() {
     return Math.max(1, Math.ceil(this.checkoutFilteredProducts.length / this.checkoutPageSize));
  }

  nextCheckoutPage() {
    if (this.checkoutCurrentPage < this.checkoutTotalPages) {
      this.checkoutCurrentPage++;
    }
  }

  prevCheckoutPage() {
    if (this.checkoutCurrentPage > 1) {
      this.checkoutCurrentPage--;
    }
  }

  onCheckoutSearch() {
    this.checkoutCurrentPage = 1;
  }

  processCheckout(product: any) {
    if (this.isSaving) return;
    const qty = this.checkoutQuantities[product.id];
    if (!qty || qty <= 0) return;
    if (qty > product.current_stock) {
      this.toastService.showError(`Error: You cannot checkout more items (${qty}) than currently in stock (${product.current_stock}).`);
      return;
    }

    this.isSaving = true;
    const payload = {
      center_id: this.selectedCenterId,
      items: [{ product_id: product.id, quantity: qty }]
    };

    this.apiService.inventoryCheckout(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.checkoutQuantities[product.id] = 0; // reset
        this.isSaving = false;
        this.loadData();
      },
      error: (err) => {
        this.isSaving = false;
        this.toastService.showError('Checkout failed: ' + JSON.stringify(err.error));
      }
    });
  }

  isDownloadingVendorTemplate = false;

  downloadVendorTemplate() {
    if (this.isDownloadingVendorTemplate) return;
    this.isDownloadingVendorTemplate = true;
    this.apiService.downloadVendorsTemplate().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (blob: any) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'vendors_import_template.xlsx';
        a.click();
        window.URL.revokeObjectURL(url);
        this.isDownloadingVendorTemplate = false;
      },
      error: (err: any) => {
        this.toastService.showError('Failed to download template.');
        this.isDownloadingVendorTemplate = false;
      }
    });
  }

  uploadVendors(event: any) {
    const file = event.target.files[0];
    if (!file) return;

    this.isSaving = true;
    this.apiService.uploadFile('inventory/api/vendors/bulk_upload/', file, this.selectedCenterId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.toastService.showSuccess('Vendors uploaded successfully.');
        this.loadData();
        event.target.value = '';
      },
      error: (e) => {
        this.isSaving = false;
        const errMsg = e.error?.error || e.error?.detail || e.message || 'Unknown error';
        this.toastService.showError('Failed to upload: ' + errMsg);
        event.target.value = '';
      }
    });
  }

  // --- Purchase Orders ---Logic
  // Audit Logic
  get auditFilteredProducts() {
    let filtered = this.products;
    if (this.auditSearchTerm) {
      const s = this.auditSearchTerm.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(s) || (p.barcode && p.barcode.toLowerCase().includes(s)));
    }
    return filtered;
  }

  get auditPaginatedProducts() {
     const filtered = this.auditFilteredProducts;
     const startIndex = (this.auditCurrentPage - 1) * this.auditPageSize;
     return filtered.slice(startIndex, startIndex + this.auditPageSize);
  }

  get auditTotalPages() {
     return Math.max(1, Math.ceil(this.auditFilteredProducts.length / this.auditPageSize));
  }

  nextAuditPage() {
    if (this.auditCurrentPage < this.auditTotalPages) {
      this.auditCurrentPage++;
    }
  }

  prevAuditPage() {
    if (this.auditCurrentPage > 1) {
      this.auditCurrentPage--;
    }
  }

  onAuditSearch() {
    this.auditCurrentPage = 1;
  }

  processAudit() {
    if (this.isSaving) return;
    const items = [];
    for (const [productId, qty] of Object.entries(this.auditQuantities)) {
      if (qty !== null && qty !== undefined && String(qty).trim() !== '') { // allow 0
        items.push({ product_id: Number(productId), quantity: Number(qty) });
      }
    }
    
    if (items.length === 0) {
      this.toastService.showError("No quantities entered for audit.");
      return;
    }

    this.isSaving = true;
    const payload = {
      center_id: this.selectedCenterId,
      items: items
    };

    this.apiService.inventoryAudit(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.toastService.showSuccess(res.message || "Audit completed successfully.");
        this.auditQuantities = {};
        this.isSaving = false;
        this.loadData();
      },
      error: (err) => {
        this.isSaving = false;
        this.toastService.showError('Audit failed: ' + JSON.stringify(err.error));
      }
    });
  }

  // Stock History Logic
  generateStockHistoryDates() {
    this.stockHistoryDates = [];
    const today = new Date();
    for (let i = 0; i < 20; i++) {
      const d = new Date();
      d.setDate(today.getDate() - i);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      this.stockHistoryDates.push(`${year}-${month}-${day}`);
    }
  }

  formatDisplayDate(dateStr: string): string {
    const d = new Date(dateStr);
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${String(d.getDate()).padStart(2, '0')}-${months[d.getMonth()]}-${d.getFullYear()}`;
  }

  downloadStockHistoryExcel(dateStr: string) {
    if (this.isLoadingHistory) return;
    this.isLoadingHistory = true;
    const cid = this.selectedCenterId ? this.selectedCenterId : undefined;
    this.apiService.getStockHistory(dateStr, cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.generateCSV(data, dateStr);
        this.isLoadingHistory = false;
      },
      error: (err) => {
          this.toastService.showError("Failed to fetch history: " + JSON.stringify(err.error));
          this.isLoadingHistory = false;
      }
    });
  }

  viewStockHistoryForDate(dateStr: string) {
    this.selectedHistoryDate = dateStr;
    this.isLoadingHistory = true;
    this.selectedHistoryRecords = [];
    const cid = this.selectedCenterId ? this.selectedCenterId : undefined;
    this.apiService.getStockHistory(dateStr, cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.selectedHistoryRecords = data;
        this.isLoadingHistory = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.toastService.showError("Failed to fetch history: " + JSON.stringify(err.error));
        this.isLoadingHistory = false;
        this.cdr.detectChanges();
      }
    });
  }

  generateCSV(data: any[], dateStr: string) {
    if (data.length === 0) {
      this.toastService.showError("No data available for this date.");
      return;
    }
    const headers = ['Product', 'Brand', 'Type', 'Price', 'Count', 'Value'];
    const rows = data.map((item: any) => {
      const val = (parseFloat(item.price) || 0) * (item.historical_stock || 0);
      return [
        item.name || '',
        item.brand || '',
        item.category || '',
        item.price || 0,
        item.historical_stock || 0,
        val.toFixed(2)
      ];
    });
    this.csvService.exportToCsv(`Stock_History_${dateStr}.csv`, headers, rows);
  }

  exportLowStockExcel() {
    const lowStockItems = this.products.filter(p => p.current_stock <= p.reorder_level);
    if (lowStockItems.length === 0) {
      this.toastService.showError("No low stock items to export.");
      return;
    }
    const headers = ['Product Name', 'Brand', 'Current Stock', 'Reorder Level', 'Deficit', 'Vendor Name', 'Vendor Phone'];
    const rows = lowStockItems.map(p => {
      const deficit = (p.reorder_level || 0) - (p.current_stock || 0);
      // Attempt to find mapped vendor for info (optional, helps with reordering)
      const vendor = this.vendors.find(v => v.mapped_products?.includes(p.id));
      return [
        p.name || '',
        p.brand || '',
        p.current_stock || 0,
        p.reorder_level || 0,
        deficit,
        vendor ? vendor.name : 'Unmapped',
        vendor ? vendor.phone : ''
      ];
    });
    this.csvService.exportToCsv('Low_Stock_Alerts.csv', headers, rows);
  }

  get deliveredPurchaseOrders() {
    return this.purchaseOrders.filter(po => po.status === 'Delivered');
  }


  uploadProducts(event: any) {
    const file = event.target.files[0];
    if (!file) return;
    this.isSaving = true;

    // Bulk upload is center-aware — passes center_id if a center is selected, or null for ALL centers
    this.apiService.uploadFile('inventory/api/products/bulk_upload/', file, this.selectedCenterId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.isSaving = false;
        const msg = res.message || 'File uploaded successfully';
        this.toastService.showSuccess(msg);
        if (res.warnings && res.warnings.length > 0) {
          console.warn('Bulk upload warnings:', res.warnings);
        }
        // Reload data — if on All Locations, show all; otherwise show current center
        this.loadData();
        event.target.value = '';
      },
      error: (e) => {
        this.isSaving = false;
        const errMsg = e.error?.error || e.error?.detail || e.message || 'Unknown error';
        this.toastService.showError('Failed to upload: ' + errMsg);
        event.target.value = '';
      }
    });
  }

  isDownloadingTemplate = false;

  downloadTemplate() {
    if (this.isDownloadingTemplate) return;
    this.isDownloadingTemplate = true;
    this.apiService.downloadProductsTemplate().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (blob: any) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'products_import_template.xlsx';
        a.click();
        window.URL.revokeObjectURL(url);
        this.isDownloadingTemplate = false;
      },
      error: (err: any) => {
        this.toastService.showError('Failed to download template.');
        this.isDownloadingTemplate = false;
      }
    });
  }

  exportExcel() {
    const headers = ['SKU', 'Name', 'Category', 'Brand', 'Supplier', 'Base Price', 'Sale Price', 'Stock Qty', 'Reorder Lvl', 'Reorder Qty'];
    const rows = this.products.map(p => [
      p.sku || '',
      p.name || '',
      p.category || '',
      p.brand || '',
      p.supplier_name || '',
      p.base_price || 0,
      p.sale_price || 0,
      p.stock_quantity || 0,
      p.reorder_level || 0,
      p.reorder_quantity || 0
    ]);
    this.csvService.exportToCsv('Inventory_Report', headers, rows);
  }
  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

}
