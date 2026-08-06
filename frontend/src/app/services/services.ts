import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';
import { CsvService } from '../services/csv.service';

@Component({
  selector: 'app-services',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './services.html',
  styleUrls: ['./services.css']
})
export class ServicesComponent implements OnInit {
  toastService = inject(ToastService);

  api = inject(ApiService);
  csvService = inject(CsvService);
  cdr = inject(ChangeDetectorRef);
  centers: any[] = [];
  selectedCenter: number | null = null;
  services: any[] = [];
  showAddModal: boolean = false;
  isEditing = false;
  editingId: number | null = null;
  newService: any = {
    service_code: '',
    name: '',
    brand: '',
    category: '',
    sub_category: '',
    sac_code: '',
    hsn_code: '',
    default_price: 0,
    tax_percentage: 5,
    duration_mins: 0,
    level: 'Organisation',
    centers: []
  };

  isOwner = false;
  hasGlobalAccess = false;
  permissions: any = {};
  isSaving = false;

  ngOnInit(): void {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.permissions = user.permissions || {};
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
      } catch (e) {}
    }

    this.api.getCenters().subscribe(data => {
      this.centers = data || [];
      if (this.centers.length) {
        this.selectedCenter = this.centers[0].id;
      }
      this.loadServices();
    });
  }

  loadServices() {
    const cid = this.selectedCenter ?? undefined;
    this.api.getServices(cid).subscribe(data => {
      this.services = data || [];
      this.cdr.detectChanges();
    });
  }

  onCenterChange() {
    this.loadServices();
  }

  saveOverride(s: any) {
    if (!this.selectedCenter) {
      this.toastService.showError('Please select a center first');
      return;
    }
    const price = s.center_override ? s.center_override.price : s.default_price;
    const isActive = s.center_override ? s.center_override.is_active : true;
    this.api.overrideCenterService(this.selectedCenter, s.id, price, isActive).subscribe({
      next: () => {
        this.toastService.showSuccess('Override saved');
        this.loadServices();
      },
      error: (err) => {
        this.toastService.showError(String('Override failed') + ((err) ? ' ' + JSON.stringify(err) : ''));
        this.toastService.showError('Failed to save override: ' + (err?.error ? JSON.stringify(err.error) : err?.message || JSON.stringify(err)));
      }
    });
  }

  openAddModal() {
    this.showAddModal = true;
    this.isEditing = false;
    this.editingId = null;
    this.newService = { service_code: '', name: '', brand: '', category: '', sub_category: '', sac_code: '', hsn_code: '', default_price: 0, tax_percentage: 5, duration_mins: 0, level: 'Organisation', centers: [] };
  }

  editService(s: any) {
    this.showAddModal = true;
    this.isEditing = true;
    this.editingId = s.id;
    this.newService = { 
      ...s, 
      level: s.level || 'Organisation',
      centers: s.centers ? [...s.centers] : []
    };
  }

  deleteService(s: any) {
    if (confirm('Are you sure you want to delete this service?')) {
      this.api.deleteService(s.id).subscribe({
        next: () => {
          this.loadServices();
        },
        error: (err) => {
          this.toastService.showError('Failed to delete service: ' + (err?.error ? JSON.stringify(err.error) : err));
        }
      });
    }
  }

  addCenterFromSelect(value: string) {
    if (!value) return;
    if (!this.newService.centers) this.newService.centers = [];

    if (value === 'all') {
      this.newService.centers = this.centers.map(c => c.id);
      return;
    }

    const centerId = parseInt(value, 10);
    if (!isNaN(centerId) && !this.newService.centers.includes(centerId)) {
      this.newService.centers.push(centerId);
    }
  }

  removeCenter(centerId: number) {
    if (!this.newService.centers) return;
    this.newService.centers = this.newService.centers.filter((id: number) => id !== centerId);
  }

  getCenterName(id: number): string {
    const center = this.centers.find(c => c.id === id);
    return center ? center.center_name || center.display_name : 'Unknown Center';
  }

  addService() {
    if (!this.newService.name) {
      this.toastService.showError('Service name is required');
      return;
    }
    const payload: any = {
      service_code: this.newService.service_code,
      name: this.newService.name,
      brand: this.newService.brand,
      category: this.newService.category,
      sub_category: this.newService.sub_category,
      sac_code: this.newService.sac_code,
      hsn_code: this.newService.hsn_code,
      default_price: this.newService.default_price,
      tax_percentage: this.newService.tax_percentage,
      duration_mins: this.newService.duration_mins,
      level: this.newService.level,
      centers: this.newService.centers
    };

    if (this.isEditing && this.editingId) {
      this.api.updateService(this.editingId, payload, this.selectedCenter).subscribe({
        next: () => {
          this.toastService.showSuccess('Service updated');
          this.showAddModal = false;
          this.loadServices();
        },
        error: (err) => {
          this.toastService.showError(String('Update service failed') + ((err) ? ' ' + JSON.stringify(err) : ''));
          const body = err?.error ? JSON.stringify(err.error) : (err?.message || JSON.stringify(err));
          this.toastService.showError('Failed to update service: ' + body);
        }
      });
    } else {
      this.api.createService(payload).subscribe({
        next: () => {
          this.toastService.showSuccess('Service created');
          this.showAddModal = false;
          this.loadServices();
        },
        error: (err) => {
          this.toastService.showError(String('Create service failed') + ((err) ? ' ' + JSON.stringify(err) : ''));
          const body = err?.error ? JSON.stringify(err.error) : (err?.message || JSON.stringify(err));
          this.toastService.showError('Failed to create service: ' + body);
        }
      });
    }
  }

  onPriceChange(s: any, value: any) {
    if (!s.center_override) s.center_override = { price: null, is_active: true };
    s.center_override.price = value === '' || value === null ? null : Number(value);
  }

  uploadServices(event: any) {
    const file = event.target.files[0];
    if (!file) return;
    this.isSaving = true;
    // Center-aware upload
    this.api.uploadFile('services/api/master/bulk_upload/', file, this.selectedCenter).subscribe({
      next: (res: any) => {
        this.isSaving = false;
        const msg = res.message || 'File uploaded successfully';
        this.toastService.showSuccess(msg);
        if (res.warnings && res.warnings.length > 0) {
          console.warn('Bulk upload warnings:', res.warnings);
        }
        this.loadServices();
        event.target.value = '';
      },
      error: (e: any) => {
        this.isSaving = false;
        const errMsg = e.error?.error || e.error?.detail || e.message || 'Unknown error';
        this.toastService.showError('Failed to upload: ' + errMsg);
        event.target.value = '';
      }
    });
  }

  downloadTemplate() {
    // Column headers exactly matching the expected upload template format
    const headers = [
      'S.No',
      'Brand',
      'Category',
      'Sub Category',
      'Service Name',
      'Price',
      'HSN Code',
      'Tax'
    ];
    // Example row to guide the user
    const exampleRow = [
      'GS1',          // S.No
      'Other',        // Brand
      'Hair',         // Category
      'Hair Cut',     // Sub Category
      'Sample Service Name', // Service Name (REQUIRED)
      '500',          // Price
      '999721',       // HSN Code
      '5%'            // Tax
    ];
    this.csvService.exportToCsv('service_upload_template.csv', headers, [exampleRow]);
  }

  exportExcel() {
    const headers = ['Category', 'Name', 'Duration (mins)', 'Price (Rs)', 'Member Price', 'Description'];
    const rows = this.services.map(s => [
      s.category || '',
      s.name || '',
      s.duration_minutes || 0,
      s.price || 0,
      s.member_price || 0,
      s.description || ''
    ]);
    this.csvService.exportToCsv('Services_Report', headers, rows);
  }
}
