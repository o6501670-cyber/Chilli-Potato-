import { AdminFilterService } from '../admin-filter.service';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { CsvService } from '../../services/csv.service';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-admin-bills',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin-bills.html',
  styleUrl: './admin-bills.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminBillsComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;

  apiService = inject(ApiService);
  adminFilterService = inject(AdminFilterService);
  cdr = inject(ChangeDetectorRef);
  csvService = inject(CsvService);

  centers: any[] = [];
  searchInvoiceNo: string = '';
  
  
  
  
  
  currentPage: number = 1;
  totalPages: number = 1;
  
  invoices: any[] = [];
  isLoading = false;

  // Modal State
  selectedInvoice: any = null;
  showModal = false;
  paymentMethodChange: string = 'Cash';

  ngOnInit() {
    this.adminFilterService.apply$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.getInvoices();
    });
    this.adminFilterService.export$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.exportExcel();
    });

    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.permissions = user.permissions || {};
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
      } catch (e) {}
    }
    this.setDefaultDates();
    this.getInvoices();
  }

  setDefaultDates() {
    const today = new Date();
    this.adminFilterService.setToDate(today.toISOString().split('T')[0]);
    
    // Default from date = 30 days ago
    
    
    
  }

  loadCenters() {
    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        this.centers = Array.isArray(data) ? data : (data.results || []);
        this.getInvoices();
      },
      error: err => {
        console.error('Failed to load centers', err);
        this.getInvoices();
      }
    });
  }

  resetAndGetInvoices() {
    this.searchInvoiceNo = '';

    this.currentPage = 1;
    this.getInvoices();
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.getInvoices();
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.getInvoices();
    }
  }

  getInvoices() {
    this.isLoading = true;
    this.cdr.detectChanges();
    let url = `billing/invoices/?center_id=${this.adminFilterService.currentCenterId || ''}&start_date=${this.adminFilterService.currentFromDate || ''}&end_date=${this.adminFilterService.currentToDate || ''}&invoice_number=${this.searchInvoiceNo || ''}&exclude_drafts=true&page_size=500&page=${this.currentPage}`;
    this.apiService.get(url).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        let rawInvoices = Array.isArray(data) ? data : (data.results || []);
        if (!Array.isArray(data) && data.count) {
          this.totalPages = Math.ceil(data.count / 500);
        }
        
        // Pre-compute template values to dramatically improve performance
        this.invoices = rawInvoices.map((inv: any) => {
           inv.clientNameStr = this.getClientName(inv);
           inv.billerNameStr = this.getBiller(inv);
           inv.taxVal = this.getTax(inv);
           inv.statusStr = inv.status || 'paid';
           inv.serviceCount = this.getServiceCount(inv);
           inv.productCount = this.getProductCount(inv);
           inv.membCount = this.getMembershipCount(inv);
           inv.othersCount = this.getOthersCount(inv);
           inv.redemptionVal = this.getRedemption(inv);
           return inv;
        });

        this.isLoading = false;
        this.cdr.detectChanges();
        this.cdr.detectChanges();
      },
      error: err => {
        console.error('Failed to get invoices', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }



  openInvoiceModal(invoice: any) {
    this.selectedInvoice = invoice;
    this.showModal = true;
  }

  actionConfirmType: 'cancel' | 'refund' | 'change_payment' | null = null;
  backdateValue: string = '';

  closeInvoiceModal() {
    this.showModal = false;
    this.selectedInvoice = null;
    this.actionConfirmType = null;
  }

  confirmAction(type: 'cancel' | 'refund' | 'change_payment') {
    this.actionConfirmType = type;
  }

  cancelActionConfirm() {
    this.actionConfirmType = null;
  }

  executeAction() {
    if (!this.selectedInvoice || !this.actionConfirmType) return;
    this.isLoading = true;
    
    if (this.actionConfirmType === 'cancel') {
      this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/cancel/`, {}).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.actionConfirmType = null;
          this.closeInvoiceModal();
          this.getInvoices();
        },
        error: (err: any) => {
          this.isLoading = false;
          console.error(err);
          alert('Failed to cancel invoice.');
        }
      });
    } else if (this.actionConfirmType === 'refund') {
      this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/refund/`, {}).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.actionConfirmType = null;
          this.closeInvoiceModal();
          this.getInvoices();
        },
        error: (err: any) => {
          this.isLoading = false;
          console.error(err);
          alert('Failed to refund invoice.');
        }
      });
    }
  }

  updatePaymentMethod() {
    if (!this.selectedInvoice || !this.paymentMethodChange) return;
    this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/change_payment/`, { payment_method: this.paymentMethodChange }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        alert('Payment method updated successfully.');
        this.closeInvoiceModal();
        this.getInvoices();
      },
      error: (err: any) => {
        console.error(err);
        alert('Failed to update payment method.');
      }
    });
  }

  // Formatting helpers
  getBiller(invoice: any): string {
    return invoice.staff ? `Staff #${invoice.staff}` : 'Admin'; // Update if we can fetch staff details
  }

  getClientName(invoice: any): string {
    if (invoice.client && invoice.client.first_name) {
      return `${invoice.client.first_name} ${invoice.client.last_name || ''}`.trim();
    }
    return 'Unknown';
  }

  getClientPhone(invoice: any): string {
    return invoice.client?.phone || '';
  }

  getServiceCount(invoice: any): number {
    return invoice.items?.filter((i: any) => {
      if (!i.content_type) return false;
      const ct = typeof i.content_type === 'string' ? i.content_type.toLowerCase() : (i.content_type.app_label || '').toLowerCase();
      return !ct.includes('inventory') && !ct.includes('marketing');
    }).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }

  getProductCount(invoice: any): number {
    return invoice.items?.filter((i: any) => {
      if (!i.content_type) return false;
      const ct = typeof i.content_type === 'string' ? i.content_type.toLowerCase() : (i.content_type.app_label || '').toLowerCase();
      return ct.includes('inventory');
    }).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }

  getMembershipCount(invoice: any): number {
    return invoice.items?.filter((i: any) => {
      if (!i.content_type) return false;
      const ct = typeof i.content_type === 'string' ? i.content_type.toLowerCase() : (i.content_type.app_label || '').toLowerCase();
      return ct.includes('membership') || ct.includes('package') || ct.includes('valuecard');
    }).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }

  getOthersCount(invoice: any): number {
    return invoice.items?.filter((i: any) => !i.content_type).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }
  
  getTax(invoice: any): number {
      return (parseFloat(invoice.cgst) || 0) + (parseFloat(invoice.sgst) || 0);
  }

  getRedemption(invoice: any): number {
      if (!invoice || !invoice.payments) return 0;
      let total = 0;
      for (const p of invoice.payments) {
          if (p.payment_method && (p.payment_method.toLowerCase().includes('card') || p.payment_method.toLowerCase().includes('redeem') || p.payment_method.toLowerCase() === 'membership')) {
              // Only count actual value card / gift card redemptions if defined
              if (p.payment_method.toLowerCase().includes('value') || p.payment_method.toLowerCase().includes('gift') || p.payment_method.toLowerCase().includes('membership')) {
                 total += parseFloat(p.amount) || 0;
              }
          }
      }
      return total;
  }
  
  getGross(invoice: any): number {
      return parseFloat(invoice.total_amount) || 0;
  }
  
  getTotalPaidByMethod(method: string, invoice: any): number {
      return invoice.payments?.filter((p: any) => {
          return (p.payment_method || '').toLowerCase().includes(method.toLowerCase());
      }).reduce((acc: number, p: any) => acc + parseFloat(p.amount), 0) || 0;
  }

  getPaidAmount(invoice: any): number {
      return parseFloat(invoice.paid_amount) || 0;
  }

  getTotalValue() {
    return this.invoices.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);
  }

  getPaidCount() {
    return this.invoices.filter(inv => !inv.status || inv.status === 'paid').length;
  }

  getCancelledCount() {
    return this.invoices.filter(inv => inv.status === 'cancelled').length;
  }

  getRefundedCount() {
    return this.invoices.filter(inv => inv.status === 'refunded').length;
  }

  exportExcel() {
    const headers = ['Bill No', 'Date', 'Biller', 'Client', 'Services', 'Products', 'Memb.', 'Others', 'Subtotal', 'Discount', 'Tax', 'Total', 'Redemption', 'Status'];
    const rows = this.invoices.map(inv => [
      inv.id,
      inv.created_at ? inv.created_at.split('T')[0] : '',
      this.getBiller(inv),
      this.getClientName(inv),
      this.getServiceCount(inv),
      this.getProductCount(inv),
      this.getMembershipCount(inv),
      this.getOthersCount(inv),
      inv.subtotal || 0,
      inv.discount || 0,
      this.getTax(inv),
      inv.total_amount || 0,
      this.getRedemption(inv),
      inv.status || ''
    ]);
    this.csvService.exportToCsv('Admin_Bills_Report', headers, rows);
  }

  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }
}
