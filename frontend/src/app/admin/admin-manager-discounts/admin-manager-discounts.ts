import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { CsvService } from '../../services/csv.service';
import { LocationSelectorComponent } from '../../components/location-selector/location-selector';

@Component({
  selector: 'app-admin-manager-discounts',
  standalone: true,
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './admin-manager-discounts.html',
  styleUrl: './admin-manager-discounts.css'
})
export class AdminManagerDiscountsComponent implements OnInit {
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;

  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  csvService = inject(CsvService);

  centers: any[] = [];
  selectedCenterId: number | null = null;
  invoices: any[] = [];
  isLoading = false;
  fromDate: string = '';
  toDate: string = '';

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
    const today = new Date();
    this.toDate = this.formatDate(today);
    const start = new Date();
    start.setDate(start.getDate() - 30);
    this.fromDate = this.formatDate(start);

    this.loadCenters();
  }

  formatDate(date: Date): string {
    const d = new Date(date);
    let month = '' + (d.getMonth() + 1);
    let day = '' + d.getDate();
    const year = d.getFullYear();
    if (month.length < 2) month = '0' + month;
    if (day.length < 2) day = '0' + day;
    return [year, month, day].join('-');
  }

  loadCenters() {
    this.apiService.getCenters().subscribe({
      next: (data: any) => {
        this.centers = Array.isArray(data) ? data : (data.results || []);
        if (this.centers.length && !this.selectedCenterId) {
          this.selectedCenterId = this.centers[0].id;
        }
        this.getDiscountedInvoices();
      },
      error: err => {
        console.error('Failed to load centers', err);
        this.getDiscountedInvoices();
      }
    });
  }

  getDiscountedInvoices() {
    this.isLoading = true;
    
    let url = `billing/invoices/?center_id=${this.selectedCenterId || ''}&manager_discount=true`;
    if (this.fromDate) url += `&start_date=${this.fromDate}`;
    if (this.toDate) url += `&end_date=${this.toDate}`;
    
    this.apiService.get(url).subscribe({
      next: (data: any) => {
        this.invoices = Array.isArray(data) ? data : (data.results || []);
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: err => {
        console.error('Failed to get discounted invoices', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
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

  getGross(invoice: any): number {
      return parseFloat(invoice.total_amount) || 0;
  }

  exportExcel() {
    const headers = ['Invoice No', 'Date/Time', 'Client', 'Phone', 'Type', 'Item', 'Billed By', 'Price', 'Discount', 'Discount %', 'Net Price'];
    const rows: any[][] = [];
    
    this.invoices.forEach(inv => {
      // Invoice level discount
      if (inv.discount > 0) {
        rows.push([
          inv.id,
          inv.created_at ? inv.created_at.replace('T', ' ').substring(0, 16) : '',
          this.getClientName(inv),
          this.getClientPhone(inv),
          'Overall Bill',
          'Full Invoice',
          inv.staff || 'Admin',
          inv.subtotal || 0,
          inv.discount || 0,
          (inv.subtotal ? ((inv.discount / inv.subtotal) * 100).toFixed(0) : 0) + '%',
          inv.total_amount || 0
        ]);
      }
      
      // Item Level Discounts
      if (inv.items && inv.items.length) {
        inv.items.forEach((item: any) => {
          if (item.discount > 0) {
            rows.push([
              inv.id,
              inv.created_at ? inv.created_at.replace('T', ' ').substring(0, 16) : '-',
              this.getClientName(inv),
              this.getClientPhone(inv),
              item.content_type?.split('.')?.[1] || 'Service',
              item.description || 'Item',
              inv.staff || 'Admin',
              item.unit_price || 0,
              item.discount || 0,
              item.unit_price ? Math.round((item.discount / item.unit_price) * 100) + '%' : '0%',
              item.total_price || 0
            ]);
          }
        });
      }
    });
    
    this.csvService.exportToCsv('Manager_Discounts.csv', headers, rows);
  }

  getTotalDiscountsCount(): number {
    return this.invoices.length;
  }

  getTotalDiscountValue(): number {
    let sum = 0;
    this.invoices.forEach(inv => {
      if (inv.discount > 0) sum += parseFloat(inv.discount) || 0;
      if (inv.items && inv.items.length) {
        inv.items.forEach((item: any) => {
          if (item.discount > 0) sum += parseFloat(item.discount) || 0;
        });
      }
    });
    return sum;
  }
}
