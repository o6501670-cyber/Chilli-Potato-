import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { CsvService } from '../../services/csv.service';
import { ToastService } from '../../services/toast.service';
import { LocationSelectorComponent } from '../../components/location-selector/location-selector';

@Component({
  selector: 'app-admin-bills',
  standalone: true,
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './admin-bills.html',
  styleUrl: './admin-bills.css'
})
export class AdminBillsComponent implements OnInit {
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;

  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  csvService = inject(CsvService);

  centers: any[] = [];
  selectedCenterId: number | null = null;
  
  fromDate: string = '';
  toDate: string = '';
  searchInvoiceNo: string = '';
  
  invoices: any[] = [];
  isLoading = false;

  // Modal State
  selectedInvoice: any = null;
  showModal = false;
  paymentMethodChange: string = 'Cash';

  ngOnInit() {
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
    this.loadCenters();
  }

  setDefaultDates() {
    const today = new Date();
    this.toDate = today.toISOString().split('T')[0];
    
    // Default from date = 30 days ago
    const from = new Date();
    from.setDate(from.getDate() - 30);
    this.fromDate = from.toISOString().split('T')[0];
  }

  loadCenters() {
    this.apiService.getCenters().subscribe({
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

  getInvoices() {
    this.isLoading = true;
    let url = `billing/invoices/?center_id=${this.selectedCenterId || ''}&start_date=${this.fromDate || ''}&end_date=${this.toDate || ''}&exclude_drafts=true`;
    this.apiService.get(url).subscribe({
      next: (data: any) => {
        let rawInvoices = Array.isArray(data) ? data : (data.results || []);
        
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
      this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/cancel/`, {}).subscribe({
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
      this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/refund/`, {}).subscribe({
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
    this.apiService.post(`billing/invoices/${this.selectedInvoice.id}/change_payment/`, { payment_method: this.paymentMethodChange }).subscribe({
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
       return !['inventory', 'marketing'].includes(i.content_type.split('.')[0] || i.content_type.app_label);
    }).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }

  getProductCount(invoice: any): number {
    return invoice.items?.filter((i: any) => {
       if (!i.content_type) return false;
       return (i.content_type.split('.')[0] || i.content_type.app_label) === 'inventory';
    }).reduce((acc: number, item: any) => acc + item.quantity, 0) || 0;
  }

  getMembershipCount(invoice: any): number {
    return invoice.items?.filter((i: any) => {
       if (!i.content_type) return false;
       const ct = i.content_type;
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
}
