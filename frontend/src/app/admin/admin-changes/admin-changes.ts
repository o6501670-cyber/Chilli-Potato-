import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { CsvService } from '../../services/csv.service';
import { LocationSelectorComponent } from '../../components/location-selector/location-selector';

@Component({
  selector: 'app-admin-changes',
  standalone: true,
  imports: [CommonModule, FormsModule, LocationSelectorComponent],
  templateUrl: './admin-changes.html',
  styleUrl: './admin-changes.css'
})
export class AdminChangesComponent implements OnInit {
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;

  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  csvService = inject(CsvService);

  centers: any[] = [];
  selectedCenterId: number | null = null;
  changeLogs: any[] = [];
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
    start.setMonth(start.getMonth() - 1);
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
        this.getChangeLogs();
      },
      error: err => {
        console.error('Failed to load centers', err);
        this.getChangeLogs();
      }
    });
  }

  getChangeLogs() {
    this.isLoading = true;
    let url = `billing/change-logs/?center_id=${this.selectedCenterId || ''}`;
    if (this.fromDate) url += `&start_date=${this.fromDate}`;
    if (this.toDate) url += `&end_date=${this.toDate}`;
    this.apiService.get(url).subscribe({
      next: (data: any) => {
        this.changeLogs = Array.isArray(data) ? data : (data.results || []);
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: err => {
        console.error('Failed to get change logs', err);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  exportExcel() {
    const headers = ['Bill Date', 'Salon', 'Bill-No', 'Bill Amount', 'User', 'Changed On', 'Action'];
    const rows = this.changeLogs.map(log => [
      log.bill_date ? log.bill_date.replace('T', ' ').substring(0, 16) : '-',
      log.center_name || '',
      log.invoice || '',
      log.bill_amount || 0,
      log.user_name || 'System',
      log.created_at ? log.created_at.replace('T', ' ').substring(0, 16) : '-',
      log.action || ''
    ]);
    this.csvService.exportToCsv('Admin_Changes_Log.csv', headers, rows);
  }

  getCancelRefundCount(): number {
    return this.changeLogs.filter(log => log.action === 'Cancel Bill' || log.action === 'Refund').length;
  }

  getLostValue(): number {
    return this.changeLogs
      .filter(log => log.action === 'Cancel Bill' || log.action === 'Refund')
      .reduce((sum, log) => sum + (parseFloat(log.bill_amount) || 0), 0);
  }
}
