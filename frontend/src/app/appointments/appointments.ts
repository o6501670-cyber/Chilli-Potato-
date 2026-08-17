import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectorRef, Component, DestroyRef, OnInit, OnDestroy, inject } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { AuthService } from '../services/auth';
import { ToastService } from '../services/toast.service';
import { DragDropModule } from '@angular/cdk/drag-drop';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';

function extractErrorMessage(err: any): string {
  const data = err?.error;
  if (!data) return err?.message || 'An unexpected error occurred.';
  if (typeof data === 'string') return data;
  // DRF often returns { detail: '...' } or { non_field_errors: [...] } or array
  if (data.detail) return data.detail;
  if (Array.isArray(data)) return data.join(' ');
  const msgs: string[] = [];
  for (const key of Object.keys(data)) {
    const v = data[key];
    msgs.push(Array.isArray(v) ? v.join(' ') : String(v));
  }
  return msgs.join(' ') || JSON.stringify(data);
}

@Component({
  selector: 'app-appointments',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule, LocationSelectorComponent],
  templateUrl: './appointments.html',
  styleUrls: ['./appointments.css']
})
export class AppointmentsComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  centers: any[] = [];
  selectedCenterId: any = null;
  selectedDate: string = new Date().toISOString().split('T')[0];
  showCancelled: boolean = true;
  
  isOwner: boolean = false;
  hasGlobalAccess: boolean = false;
  permissions: any = {};

  appointments: any[] = [];
  staffMembers: any[] = [];
  activeStaffMembers: any[] = [];

  // KPIs
  totalAppointments = 0;
  unallocatedServices = 0;
  cancelledAppointments = 0;
  expectedRevenue = 0;

  // Time Slots (9 AM to 9 PM)
  timeSlots: string[] = [
    '09:00', '10:00', '11:00', '12:00', '13:00', '14:00',
    '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00'
  ];

  servicesList: any[] = [];

  // Modal
  showModal = false;
  isEdit = false;
  isSaving = false;
  currentAppointment: any = {
    client_phone: '',
    client_name: '',
    date: '',
    start_time: '09:00',
    notes: '',
    status: 'Scheduled',
    services: []
  };
  recentVisits: any[] = [];
  
  // Search
  searchQuery: string = '';
  clientSearchResults: any[] = [];
  selectedClient: any = null;
  searchTimeout: any;
  
  newServiceForm = {
    service_name: '',
    time: '09:00',
    duration: 45,
    staff: null
  };

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private toastService: ToastService,
    private cdr: ChangeDetectorRef,
    private router: Router
  ) {}

  ngOnInit(): void {
    let user: any = null;
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try { user = JSON.parse(userStr); } catch (e) {}
    }
    this.isOwner = user?.role === 'Owner' || user?.is_superuser;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
    this.permissions = user?.permissions || {};
    
    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.centers = data || [];
      if (this.isOwner) {
        if (this.centers.length > 0 && !this.selectedCenterId) {
          this.selectedCenterId = this.centers[0].id;
        }
      } else {
        // Ensure numeric ID
        const cid = user?.center_id;
        this.selectedCenterId = cid ? Number(cid) : (this.centers[0]?.id || null);
      }
      this.loadData();
    });
  }

  setToday() {
    this.selectedDate = new Date().toISOString().split('T')[0];
    this.loadAppointments();
  }

  prevDay() {
    const d = new Date(this.selectedDate);
    d.setDate(d.getDate() - 1);
    this.selectedDate = d.toISOString().split('T')[0];
    this.loadAppointments();
  }

  nextDay() {
    const d = new Date(this.selectedDate);
    d.setDate(d.getDate() + 1);
    this.selectedDate = d.toISOString().split('T')[0];
    this.loadAppointments();
  }


  loadData() {
    this.loadStaff();
    this.loadAppointments();
    this.loadServices();
  }

  loadServices() {
    const cid = this.selectedCenterId ?? undefined;
    this.apiService.getServices(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.servicesList = data || [];
      this.cdr.detectChanges();
    });
  }

  onDateChange(event: any) {
    this.selectedDate = event.target.value;
    this.loadAppointments();
  }

  loadStaff() {
    const cid = this.selectedCenterId ?? undefined;
    this.apiService.getStaffMembers(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.staffMembers = data;
      this.activeStaffMembers = data.filter(s => s.is_active);
      this.cdr.detectChanges();
    });
  }

  loadAppointments() {
    const cid = this.selectedCenterId ?? undefined;
    this.apiService.getAppointments(cid, this.selectedDate).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.appointments = data;
      this.calculateKPIs();
      this.buildAppointmentsMap();  // pre-build cache after data loads
      this.cdr.detectChanges();
    });
  }

  calculateKPIs() {
    this.totalAppointments = 0;
    this.unallocatedServices = 0;
    this.cancelledAppointments = 0;
    this.expectedRevenue = 0;

    for (let appt of this.appointments) {
      if (appt.status === 'Cancelled') {
        this.cancelledAppointments++;
        continue; // skip other stats if cancelled
      }
      this.totalAppointments++;
      for (let s of appt.services) {
        if (!s.staff) this.unallocatedServices++;
        this.expectedRevenue += parseFloat(s.price || 0);
      }
    }
  }

  // Memoized map: staffId (or 'null') -> appointment+service pairs
  private _appointmentsMap: Map<string, any[]> = new Map();

  buildAppointmentsMap() {
    this._appointmentsMap.clear();
    for (let appt of this.appointments) {
      if (!this.showCancelled && appt.status === 'Cancelled') continue;
      for (let s of appt.services) {
        const key = String(s.staff ?? 'null');
        if (!this._appointmentsMap.has(key)) this._appointmentsMap.set(key, []);
        this._appointmentsMap.get(key)!.push({ appointment: appt, service: s });
      }
    }
  }

  getAppointmentsForStaff(staffId: number | null): any[] {
    const key = String(staffId ?? 'null');
    return this._appointmentsMap.get(key) ?? [];
  }

  // Calculate left percentage based on time (9am is 0%, 9pm is 100% of 12 slots, but 13 columns means we divide by 13)
  calculateLeftStyle(time: string): string {
    if (!time) return '0%';
    const parts = time.split(':');
    const hours = parseInt(parts[0], 10);
    const mins = parseInt(parts[1], 10);
    const startMins = 9 * 60; // 9am
    const currentMins = hours * 60 + mins;
    const diff = currentMins - startMins;
    const percent = (diff / (13 * 60)) * 100;
    return `${Math.max(0, Math.min(100, percent))}%`;
  }

  // Calculate width based on duration and ensure it doesn't overflow the timeline
  calculateWidthStyle(duration: number, time: string): string {
    let safeDuration = Number(duration) || 45; // fallback to 45 mins if invalid
    
    // If duration is suspiciously large (e.g., > 12 hours), it might have been saved in seconds
    if (safeDuration > 720) {
      safeDuration = Math.round(safeDuration / 60);
    }
    // Cap any remaining erroneously large durations to 8 hours max (480 mins)
    if (safeDuration > 480) {
      safeDuration = 480;
    }
    
    const widthPercent = (safeDuration / (13 * 60)) * 100;
    
    let leftPercent = 0;
    if (time) {
      const parts = time.split(':');
      const hours = parseInt(parts[0], 10) || 0;
      const mins = parseInt(parts[1], 10) || 0;
      const startMins = 9 * 60; // 9am
      const currentMins = hours * 60 + mins;
      const diff = currentMins - startMins;
      leftPercent = (diff / (13 * 60)) * 100;
    }
    
    // Cap width so it doesn't go beyond 100% of the timeline
    const maxAllowedWidth = 100 - Math.max(0, leftPercent);
    const finalWidth = Math.min(widthPercent, maxAllowedWidth);
    
    return `${Math.max(0, finalWidth)}%`;
  }

  // Modal logic
  openNewModal() {
    this.isEdit = false;
    this.searchQuery = '';
    this.selectedClient = null;
    this.clientSearchResults = [];
    this.currentAppointment = {
      client_phone: '',
      client_name: '',
      date: this.selectedDate,
      start_time: '09:00',
      notes: '',
      status: 'Scheduled',
      services: [],
      center: this.selectedCenterId
    };
    this.recentVisits = [];
    this.showModal = true;
  }

  openEditModal(appt: any) {
    this.isEdit = true;
    this.searchQuery = appt.client_name;
    this.selectedClient = null;
    this.clientSearchResults = [];
    this.currentAppointment = JSON.parse(JSON.stringify(appt));
    this.showModal = true;
    this.searchRecentVisits();
  }

  onSearchInput(event: any) {
    const val = event.target.value;
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
    if (!val || val.length < 2) {
      this.clientSearchResults = [];
      return;
    }
    this.searchTimeout = setTimeout(() => {
      this.apiService.getClients(val).pipe(takeUntilDestroyed(this.destroyRef)).subscribe((res: any) => {
        const data = res && res.results ? res.results : res;
        this.clientSearchResults = data || [];
        this.cdr.detectChanges();
      });
    }, 300);
  }

  selectClient(c: any) {
    if (c.is_blacklisted) {
      alert('This client is blacklisted and cannot book appointments.');
      this.searchQuery = '';
      this.clientSearchResults = [];
      return;
    }
    this.selectedClient = c;
    this.currentAppointment.client_phone = c.phone;
    this.currentAppointment.client_name = c.name || `${c.first_name || ''} ${c.last_name || ''}`.trim();
    this.clientSearchResults = [];
    this.searchQuery = this.currentAppointment.client_name;
    this.searchRecentVisits();
  }

  sendToBilling() {
    if (this.currentAppointment.id) {
      this.showModal = false;
      this.router.navigate(['/admin/billing'], { queryParams: { appointment_id: this.currentAppointment.id } });
    } else {
      alert("Please save this appointment first before creating an invoice.");
    }
  }

  searchRecentVisits() {
    if (this.currentAppointment.client_phone.length >= 10) {
      this.apiService.getAppointments(this.selectedCenterId, undefined, this.currentAppointment.client_phone)
        .pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
          // Exclude current appt
          this.recentVisits = data.filter(a => a.id !== this.currentAppointment.id);
        });
    }
  }

  addService() {
    if (this.newServiceForm.service_name) {
      // Find selected service to get its price and duration
      const selected = this.servicesList.find(s => s.name === this.newServiceForm.service_name);
      let price = 100;
      let duration = 45;
      
      if (selected) {
        price = selected.center_override?.price ?? selected.default_price ?? 0;
        duration = selected.duration_mins || 45;
      }
      
      // Calculate start time based on existing services
      let nextStartTime = this.currentAppointment.start_time;
      if (this.currentAppointment.services.length > 0) {
        const lastService = this.currentAppointment.services[this.currentAppointment.services.length - 1];
        nextStartTime = this.addMinutesToTime(lastService.time, lastService.duration);
      }
      this.newServiceForm.time = nextStartTime;

      this.currentAppointment.services.push({...this.newServiceForm, price, duration});
      this.newServiceForm = {
        service_name: '',
        time: this.addMinutesToTime(nextStartTime, duration),
        duration: 45,
        staff: null
      };
    }
  }

  removeService(index: number) {
    this.currentAppointment.services.splice(index, 1);
    this.recalculateTimes();
  }

  onStartTimeChange() {
    if (this.currentAppointment.services.length > 0) {
      this.currentAppointment.services[0].time = this.currentAppointment.start_time;
      this.recalculateTimes();
    } else {
      this.newServiceForm.time = this.currentAppointment.start_time;
    }
  }

  recalculateTimes() {
    if (!this.currentAppointment.services || this.currentAppointment.services.length === 0) return;
    for (let i = 1; i < this.currentAppointment.services.length; i++) {
      const prev = this.currentAppointment.services[i - 1];
      this.currentAppointment.services[i].time = this.addMinutesToTime(prev.time, prev.duration);
    }
    // Update the form's default time for the next added service
    const lastService = this.currentAppointment.services[this.currentAppointment.services.length - 1];
    this.newServiceForm.time = this.addMinutesToTime(lastService.time, lastService.duration);
  }

  addMinutesToTime(timeStr: string, minutesToAdd: number): string {
    if (!timeStr) return '09:00';
    const parts = timeStr.split(':');
    let hours = parseInt(parts[0], 10);
    let mins = parseInt(parts[1], 10);
    
    mins += (minutesToAdd || 0);
    hours += Math.floor(mins / 60);
    mins = mins % 60;
    
    const hStr = hours.toString().padStart(2, '0');
    const mStr = mins.toString().padStart(2, '0');
    return `${hStr}:${mStr}`;
  }

  saveAppointment() {
    if (this.isSaving) return;
    this.isSaving = true;
    
    if (!this.currentAppointment.client_name || !this.currentAppointment.client_phone || this.currentAppointment.services.length === 0) {
      alert("Please fill in client name, phone number, and add at least one service!");
      this.isSaving = false;
      return;
    }

    if (this.selectedClient && this.selectedClient.is_blacklisted) {
      alert("This client is blacklisted and cannot book appointments.");
      this.isSaving = false;
      return;
    }

    if (!this.currentAppointment.center) {
      this.currentAppointment.center = this.selectedCenterId;
    }

    if (this.isEdit) {
      this.apiService.updateAppointment(this.currentAppointment.id, this.currentAppointment).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.showModal = false;
          this.isSaving = false;
          this.toastService.showSuccess('Appointment updated successfully!');
          this.loadAppointments();
        },
        error: (err) => {
          this.toastService.showError(extractErrorMessage(err));
          this.isSaving = false;
        }
      });
    } else {
      this.apiService.createAppointment(this.currentAppointment).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.showModal = false;
          this.isSaving = false;
          this.toastService.showSuccess('Appointment created successfully!');
          this.loadAppointments();
        },
        error: (err) => {
          this.toastService.showError(extractErrorMessage(err));
          this.isSaving = false;
        }
      });
    }
  }

  cancelAppointment() {
    if (this.isEdit && !this.isSaving) {
      this.isSaving = true;
      this.apiService.updateAppointment(this.currentAppointment.id, {status: 'Cancelled'}).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.isSaving = false;
          this.showModal = false;
          this.toastService.showSuccess('Appointment cancelled.');
          this.loadAppointments();
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError(extractErrorMessage(err));
        }
      });
    }
  }

  restoreAppointment() {
    if (this.isEdit && !this.isSaving) {
      this.isSaving = true;
      this.apiService.updateAppointment(this.currentAppointment.id, {status: 'Scheduled'}).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.isSaving = false;
          this.showModal = false;
          this.toastService.showSuccess('Appointment restored to scheduled.');
          this.loadAppointments();
        },
        error: (err) => {
          this.isSaving = false;
          this.toastService.showError(extractErrorMessage(err));
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
