import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnDestroy, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { Subject } from 'rxjs';
import { takeUntil, finalize } from 'rxjs/operators';

const MODULE_KEYS = [
  'USERS', 'CLIENTS', 'STAFF', 'CENTRES', 'BILLING',
  'APPOINTMENTS', 'SERVICES', 'INVENTORY', 'MARKETING', 'FINANCE', 'ROLES',
];
const MODULE_LABELS: Record<string, string> = {
  USERS: 'Users', CLIENTS: 'Clients', STAFF: 'Staff', CENTRES: 'Centres',
  BILLING: 'Billing', APPOINTMENTS: 'Appointments', SERVICES: 'Services',
  INVENTORY: 'Inventory', MARKETING: 'Marketing', FINANCE: 'Finance',
  ROLES: 'Roles', DASHBOARD: 'Dashboard', SYSTEM: 'System',
};

const CRITICAL = new Set(['DELETE', 'CANCEL', 'REFUND']);
const WARNING  = new Set(['LOGIN', 'LOGOUT', 'LOCK', 'CLOSE_SHIFT', 'MARK_PAID']);
const FLAG_FALLBACK = '🌐';

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './logs.html',
  styleUrl: './logs.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LogsComponent implements OnInit, OnDestroy {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  logs: any[] = [];
  loading = false;

  selectedAction = '';
  selectedModule = '';

  // Pending values — bound to date inputs, not sent to API until Apply is clicked
  pendingStartDate = '';
  pendingEndDate   = '';

  // Active values — only committed on Apply
  startDate = '';
  endDate   = '';
  searchQuery = '';

  totalCount = 0;
  hasNext  = false;
  hasPrev  = false;
  currentPage = 1;

  readonly MODULE_KEYS = MODULE_KEYS;
  readonly MODULE_LABELS = MODULE_LABELS;

  private destroy$ = new Subject<void>();

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    // Default to last 7 days so we don't load all-time logs on open
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const toLocalDate = (d: Date) => {
      const offset = d.getTimezoneOffset() * 60000;
      return new Date(d.getTime() - offset).toISOString().split('T')[0];
    };
    this.pendingEndDate = toLocalDate(today);
    this.pendingStartDate = toLocalDate(sevenDaysAgo);
    this.startDate = this.pendingStartDate;
    this.endDate = this.pendingEndDate;
    this.fetchLogs();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  fetchLogs() {
    // Cancel any in-flight request before starting a new one
    this.destroy$.next();

    this.loading = true;
    this.cdr.detectChanges();

    const params: Record<string, any> = { page: this.currentPage };
    if (this.selectedAction) params['action']     = this.selectedAction;
    if (this.selectedModule) params['module']     = this.selectedModule;
    if (this.startDate)      params['start_date'] = this.startDate;
    if (this.endDate)        params['end_date']   = this.endDate;
    if (this.searchQuery)    params['search']     = this.searchQuery;

    this.api.get('audit_logs/logs/', params)
      .pipe(
        takeUntil(this.destroy$),
        finalize(() => {
          this.loading = false;
          this.cdr.detectChanges();
        })
      )
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (data: any) => {
          const rows = Array.isArray(data) ? data : (data.results ?? []);

          this.logs = rows.map((row: any) => {
            const log = {
              ...row,
              _actionClass:  this.getActionClass(row.action),
              _moduleClass:  this.getModuleClass(row.module),
              _isCritical:   CRITICAL.has(row.action),
              _isWarning:    WARNING.has(row.action),
              _deviceIcon:   this.getDeviceIcon(row.device_type),
              _countryFlag:  this.countryFlag(row.geo_country_code),
              _payloadText:  this.formatPayload(row.description)
            };
            
            if (!log.geo_country && log.ip_address && !this.isPrivateIp(log.ip_address)) {
              log.geo_country = 'Resolving...';
              this.resolveLocation(log);
            }
            return log;
          });

          this.totalCount = Array.isArray(data) ? rows.length : (data.count ?? 0);
          this.hasNext    = !Array.isArray(data) && !!data.next;
          this.hasPrev    = !Array.isArray(data) && !!data.previous;
        },
        error: () => {
          this.logs = [];
          this.totalCount = 0;
          this.hasNext = false;
          this.hasPrev = false;
        }
      });
  }

  // Commit pending dates and refetch from page 1
  onFilterChange() {
    this.startDate = this.pendingStartDate;
    this.endDate   = this.pendingEndDate;
    this.currentPage = 1;
    this.fetchLogs();
  }

  // Pill filters: apply immediately (no date pending state involved)
  onPillChange(module: string) {
    this.selectedModule = module;
    this.currentPage = 1;
    this.fetchLogs();
  }

  selectedLog: any = null;
  selectLog(log: any) { this.selectedLog = log; }

  clearFilters() {
    this.selectedAction   = '';
    this.selectedModule   = '';
    this.startDate        = '';
    this.endDate          = '';
    this.pendingStartDate = '';
    this.pendingEndDate   = '';
    this.searchQuery      = '';
    this.currentPage      = 1;
    this.fetchLogs();
  }

  get hasActiveFilters(): boolean {
    return !!(this.selectedAction || this.selectedModule || this.startDate || this.endDate || this.searchQuery);
  }

  goNext() {
    if (this.hasNext && !this.loading) {
      this.currentPage++;
      this.fetchLogs();
    }
  }

  goPrev() {
    if (this.hasPrev && !this.loading) {
      this.currentPage--;
      this.fetchLogs();
    }
  }

  private getActionClass(a: string) {
    if (CRITICAL.has(a)) return 'badge-red';
    if (WARNING.has(a))  return 'badge-orange';
    if (a === 'CREATE')   return 'badge-green';
    if (a === 'UPDATE')   return 'badge-blue';
    return 'badge-grey';
  }

  private getModuleClass(m: string) {
    const map: Record<string, string> = {
      USERS:'badge-blue', CLIENTS:'badge-green', STAFF:'badge-blue',
      BILLING:'badge-orange', FINANCE:'badge-orange', INVENTORY:'badge-grey',
      APPOINTMENTS:'badge-green', MARKETING:'badge-blue', SERVICES:'badge-grey',
      CENTRES:'badge-blue', ROLES:'badge-grey',
    };
    return map[m] || 'badge-grey';
  }

  private getDeviceIcon(deviceType: string): string {
    if (!deviceType) return '❓';
    const d = deviceType.toLowerCase();
    if (d.includes('mobile'))  return '📱';
    if (d.includes('tablet'))  return '📟';
    if (d.includes('desktop') || d.includes('laptop')) return '💻';
    if (d.includes('bot'))     return '🤖';
    return '🖥️';
  }

  private countryFlag(code: string): string {
    if (!code || code.length !== 2) return FLAG_FALLBACK;
    const offset = 0x1F1E6 - 0x41;
    return String.fromCodePoint(code.charCodeAt(0) + offset) +
           String.fromCodePoint(code.charCodeAt(1) + offset);
  }

  private isPrivateIp(ip: string): boolean {
    if (!ip) return true;
    return /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|127\.|localhost)/.test(ip);
  }

  private ipCache: Record<string, any> = {};

  private resolveLocation(log: any) {
    // Rely strictly on backend geolocation to prevent CORS blocks in HTTPS environments
    if (log.geo_country_code) {
      log._countryFlag = this.countryFlag(log.geo_country_code);
    } else if (!log.geo_country) {
      log.geo_country = 'Local/Unknown';
    }
  }

  private applyLocationData(log: any, loc: any) {
    log.geo_city = loc.geo_city;
    log.geo_country = loc.geo_country;
    log.geo_country_code = loc.geo_country_code;
    log.geo_region = loc.geo_region;
    log._countryFlag = this.countryFlag(loc.geo_country_code);
  }

  private formatPayload(raw: string): string {
    if (!raw) return '—';
    try {
      const obj = JSON.parse(raw);
      if (typeof obj !== 'object' || Array.isArray(obj)) return String(raw).substring(0, 80);
      const clean = { ...obj };
      for (const k of ['password', 'pin', 'token', 'auth_token']) delete clean[k];
      const str = JSON.stringify(clean);
      return Object.keys(clean).length === 0 ? '—' : (str.length > 80 ? str.substring(0, 80) + '…' : str);
    } catch {
      return String(raw).substring(0, 80);
    }
  }

  moduleLabel(k: string) { return MODULE_LABELS[k] || k; }
  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

}
