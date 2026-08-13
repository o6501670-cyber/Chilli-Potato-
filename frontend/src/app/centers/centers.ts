import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';

@Component({
  selector: 'app-centers',
  imports: [CommonModule, FormsModule],
  templateUrl: './centers.html',
  styleUrl: './centers.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CentersComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  toastService = inject(ToastService);
  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  centers: any[] = [];
  currentPage: number = 1;
  pageSize: number = 500;

  get paginatedItems() {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    return this.centers.slice(startIndex, startIndex + this.pageSize);
  }

  get totalPages() {
    return Math.ceil(this.centers.length / this.pageSize) || 1;
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }
  showModal = false;
  isEditing = false;
  editingId: number | null = null;
  isListView = false;
  isSaving = false;

  // Excel Bulk Import
  showImportModal = false;
  isImporting = false;
  importResult: any = null;
  importFile: File | null = null;

  newCenter = {
    center_name: '',
    display_name: '',
    address: '',
    region: '',
    phone: '',
    landline_1: '',
    landline_2: '',
    center_email: '',
    gst_number: '',
    pan_number: '',
    monthly_target: null,

    owner_name: '',
    owner_phone: '',
    owner_email_1: '',

    owner_name_2: '',
    owner_phone_2: '',
    owner_email_2: '',

    owner_name_3: '',
    owner_phone_3: '',
    owner_email_3: '',

    accountant_name_1: '',
    accountant_phone_1: '',
    accountant_email_1: '',

    accountant_name_2: '',
    accountant_phone_2: '',
    accountant_email_2: ''
  };

  isOwner = false;
  hasGlobalAccess = false;
  permissions: any = {};

  ngOnInit() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.permissions = user.permissions || {};
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
      } catch (e) { }
    }
    this.loadCenters();
  }

  loadCenters() {
    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.centers = data;
        this.currentPage = 1;
      this.cdr.detectChanges();
    });
  }

  openModal() {
    this.showModal = true;
    this.isEditing = false;
    this.resetForm();
  }

  toggleView() {
    this.isListView = !this.isListView;
  }

  editCenter(center: any) {
    this.isEditing = true;
    this.editingId = center.id;
    this.newCenter = { ...center };
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
    this.resetForm();
  }

  resetForm() {
    this.newCenter = {
      center_name: '',
      display_name: '',
      address: '',
      region: '',
      phone: '',
      landline_1: '',
      landline_2: '',
      center_email: '',
      gst_number: '',
      pan_number: '',
      monthly_target: null,

      owner_name: '',
      owner_phone: '',
      owner_email_1: '',

      owner_name_2: '',
      owner_phone_2: '',
      owner_email_2: '',

      owner_name_3: '',
      owner_phone_3: '',
      owner_email_3: '',

      accountant_name_1: '',
      accountant_phone_1: '',
      accountant_email_1: '',

      accountant_name_2: '',
      accountant_phone_2: '',
      accountant_email_2: ''
    };
    this.isEditing = false;
    this.editingId = null;
  }

  showDetailModal = false;
  detailCenter: any = null;

  monthOptions: string[] = [];
  selectedMonth: string = '';
  currentTargetInput: number = 0;
  newSmsNumber: string = '';

  generateMonths() {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const d = new Date();
    let currMonth = d.getMonth();
    let currYear = d.getFullYear();

    this.monthOptions = [];
    for (let i = 0; i < 12; i++) {
      this.monthOptions.push(`${months[currMonth]}-${currYear}`);
      currMonth++;
      if (currMonth > 11) {
        currMonth = 0;
        currYear++;
      }
    }
    if (this.monthOptions.length) {
      this.selectedMonth = this.monthOptions[0];
    }
  }

  openDetail(center: any) {
    this.detailCenter = JSON.parse(JSON.stringify(center)); // Deep copy
    if (!this.detailCenter.monthly_targets_history) this.detailCenter.monthly_targets_history = {};
    if (!this.detailCenter.closing_sms_recipients) this.detailCenter.closing_sms_recipients = [];
    if (this.detailCenter.credit_limit === null || this.detailCenter.credit_limit === undefined) this.detailCenter.credit_limit = 0;
    if (this.detailCenter.gst_enabled === null || this.detailCenter.gst_enabled === undefined) this.detailCenter.gst_enabled = true;

    this.generateMonths();
    this.onMonthSelect();
    this.showDetailModal = true;
  }

  closeDetail() {
    this.showDetailModal = false;
    this.detailCenter = null;
  }

  onMonthSelect() {
    if (this.detailCenter && this.detailCenter.monthly_targets_history[this.selectedMonth]) {
      this.currentTargetInput = this.detailCenter.monthly_targets_history[this.selectedMonth];
    } else {
      this.currentTargetInput = 0;
    }
  }

  updateTarget() {
    if (!this.detailCenter) return;
    this.detailCenter.monthly_targets_history[this.selectedMonth] = this.currentTargetInput;
    this.saveDetailSettings('Monthly Target updated');
  }

  addSms() {
    if (!this.detailCenter || !this.newSmsNumber || this.newSmsNumber.length !== 10) {
      alert('Please enter a valid 10-digit mobile number.');
      return;
    }
    this.detailCenter.closing_sms_recipients.push(this.newSmsNumber);
    this.newSmsNumber = '';
    this.saveDetailSettings('SMS Recipient added');
  }

  removeSms(index: number) {
    if (!this.detailCenter) return;
    this.detailCenter.closing_sms_recipients.splice(index, 1);
    this.saveDetailSettings('SMS Recipient removed');
  }

  updateCreditLimit() {
    this.saveDetailSettings('Credit Limit updated');
  }

  toggleGst() {
    if (!this.detailCenter) return;
    this.detailCenter.gst_enabled = !this.detailCenter.gst_enabled;
    this.saveDetailSettings('GST Setting updated');
  }

  saveDetailSettings(successMessage: string) {
    if (!this.detailCenter || this.isSaving) return;
    this.isSaving = true;
    this.apiService.updateCenter(this.detailCenter.id, this.detailCenter).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        const idx = this.centers.findIndex(c => c.id === res.id);
        if (idx > -1) this.centers[idx] = res;
        this.detailCenter = JSON.parse(JSON.stringify(res));
        this.toastService.showSuccess(successMessage);
        this.isSaving = false;
      },
      error: (err) => {
        this.toastService.showError('Failed to save settings: ' + JSON.stringify(err.error));
        this.isSaving = false;
      }
    });
  }

  openImportModal() {
    this.showImportModal = true;
    this.importResult = null;
    this.importFile = null;
  }

  closeImportModal() {
    this.showImportModal = false;
    this.importResult = null;
    this.importFile = null;
  }

  onImportFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.importFile = input.files[0];
    }
  }

  runImport() {
    if (!this.importFile) {
      this.toastService.showError('Please select an Excel file first.');
      return;
    }
    this.isImporting = true;
    this.importResult = null;
    this.apiService.bulkImportCenters(this.importFile).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.importResult = res;
        this.isImporting = false;
        this.loadCenters();
        this.toastService.showSuccess(`Import complete: ${res.summary.created} created, ${res.summary.updated} updated`);
      },
      error: (err) => {
        this.isImporting = false;
        this.importResult = { error: err.error?.error || 'Import failed. Check console for details.', hint: err.error?.hint, found_headers: err.error?.found_headers };
        this.toastService.showError('Import failed: ' + (err.error?.error || 'Unknown error'));
      }
    });
  }

  isDownloading = false;

  downloadTemplate() {
    if (this.isDownloading) return;
    this.isDownloading = true;
    this.apiService.downloadCentersTemplate().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (blob: any) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'centres_import_template.xlsx';
        a.click();
        window.URL.revokeObjectURL(url);
        this.isDownloading = false;
      },
      error: (err: any) => {
        this.toastService.showError('Failed to download template.');
        this.isDownloading = false;
      }
    });
  }

  onSubmit() {
    if (this.isSaving) return;
    this.isSaving = true;
    if (this.isEditing && this.editingId) {
      this.apiService.updateCenter(this.editingId, this.newCenter).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadCenters();
          this.closeModal();
          this.toastService.showSuccess('Center updated successfully');
          this.isSaving = false;
        },
        error: (err) => {
          this.toastService.showError('Failed to update center: ' + JSON.stringify(err.error));
          this.isSaving = false;
        }
      });
    } else {
      this.apiService.createCenter(this.newCenter).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadCenters();
          this.closeModal();
          this.toastService.showSuccess('Center created successfully');
          this.isSaving = false;
        },
        error: (err) => {
          this.toastService.showError('Failed to create center: ' + JSON.stringify(err.error));
          this.isSaving = false;
        }
      });
    }
  }
  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

}
