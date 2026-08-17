import { AdminFilterService } from './admin-filter.service';
import { LocationSelectorComponent } from '../components/location-selector/location-selector';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnDestroy, OnInit, ViewChild, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../services/auth';
import { ApiService } from '../services/api';

import { ChatComponent } from '../components/chat/chat.component';

@Component({
  selector: 'app-admin',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule, FormsModule, LocationSelectorComponent, ChatComponent],
  templateUrl: './admin.html',
  styleUrl: './admin.css',
})
export class AdminComponent implements OnInit, OnDestroy {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  authService = inject(AuthService);
  apiService = inject(ApiService);
  router = inject(Router);
  adminFilterService = inject(AdminFilterService);
  centers: any[] = [];
  
  loadCenters() {
    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data: any) => {
        this.centers = Array.isArray(data) ? data : (data.results || []);
        this.cdr.detectChanges();
      },
      error: err => console.error('Failed to load centers', err)
    });
  }

  cdr = inject(ChangeDetectorRef);
  permissions: any = {};
  isOwner = false;
  hasGlobalAccess = false;
  displayName = 'User';
  displayRole = 'Staff';
  displayInitials = 'U';
  displayFirstName = 'User';

  get greeting(): string {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 17) return 'afternoon';
    return 'evening';
  }

  ngOnInit() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        this.permissions = user.permissions || {};
        this.isOwner = (user.role && user.role.toLowerCase() === 'owner') || user.is_superuser === true;
        this.hasGlobalAccess = this.isOwner || (user?.permissions?.all_centers === true) || (user?.role?.permissions?.all_centers === true);
        this.displayName = user.full_name || user.email || 'User';
        this.displayRole = user.designation || user.role || (user.is_superuser ? 'Super Admin' : 'Staff');
        this.displayFirstName = this.displayName.trim().split(' ')[0];
        const parts = this.displayName.trim().split(' ');
        this.displayInitials = parts.length >= 2
          ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
          : this.displayName.slice(0, 2).toUpperCase();
      } catch (e) {
        console.error('Failed to parse user from localStorage', e);
      }
    }
    
    // Theme logic
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.currentTheme = (savedTheme === 'default' || savedTheme === 'light') ? 'light' : savedTheme;
    this.applyTheme();

    this.loadCenters();
    this.startGlobalPolling();
  }

  currentTheme = 'light';

  toggleTheme() {
    if (this.currentTheme === 'light') {
      this.currentTheme = 'dark';
    } else if (this.currentTheme === 'dark') {
      this.currentTheme = 'colorful';
    } else {
      this.currentTheme = 'light';
    }
    this.applyTheme();
    localStorage.setItem('theme', this.currentTheme);
  }

  applyTheme() {
    if (this.currentTheme === 'light' || this.currentTheme === 'default') {
      document.body.removeAttribute('data-theme');
    } else {
      document.body.setAttribute('data-theme', this.currentTheme);
    }
  }

  hasModuleReadAccess(modName: string): boolean {
    const mod = this.permissions[modName];
    if (!mod || typeof mod !== 'object') return false;
    return Object.values(mod).some((sub: any) => sub && sub.read === true);
  }

  logout() {
    this.authService.logout();
  }

  get isAdminPage(): boolean {
    const url = this.router.url;
    return url.includes('/admin/centers') || 
           url.includes('/admin/users') || 
           url.includes('/admin/roles') ||
           url.includes('/admin/services') ||
           url.includes('/admin/clients') ||
           url.includes('/admin/bills') ||
           url.includes('/admin/changes') ||
           url.includes('/admin/manager-discounts');
  }

  get isInventoryPage(): boolean {
    return this.router.url.includes('/admin/inventory');
  }

  get isBillingPage(): boolean {
    return this.router.url.includes('/admin/billing');
  }

  get isMarketingPage(): boolean {
    return this.router.url.includes('/admin/marketing');
  }

  get isStaffPage(): boolean {
    return this.router.url.includes('/admin/staff');
  }

  get isAppointmentsPage(): boolean {
    return this.router.url.includes('/admin/appointments');
  }

  get isDashboardPage(): boolean {
    return this.router.url.includes('/admin/dashboard');
  }

  get isHomePage(): boolean {
    return this.router.url.includes('/admin/home');
  }

  get isFinancePage(): boolean {
    return this.router.url.includes('/admin/finance');
  }

  get isLogsPage(): boolean {
    return this.router.url.includes('/admin/logs');
  }

  get hideAdminHeader(): boolean {
    return this.isInventoryPage || this.isMarketingPage || this.isStaffPage || this.isAppointmentsPage || this.isBillingPage || this.isDashboardPage || this.isHomePage || this.isFinancePage || this.isLogsPage;
  }

  // --- Global State ---
  unreadChatCount = 0;
  lowStockCount = 0;
  private globalPollingInterval: any;
  consecutiveGlobalErrors = 0;

  startGlobalPolling() {
    this.consecutiveGlobalErrors = 0;
    this.fetchUnreadChatCount();
    this.fetchLowStockCount();
    this.globalPollingInterval = setInterval(() => {
      this.fetchUnreadChatCount();
      this.fetchLowStockCount();
    }, 30000); // check unread every 30 seconds
  }

  stopGlobalPolling() {
    if (this.globalPollingInterval) {
      clearInterval(this.globalPollingInterval);
      this.globalPollingInterval = null;
    }
  }

  fetchUnreadChatCount() {
    this.apiService.get("accounts/api/chat/unread/", undefined, { headers: { "X-Background-Request": "true" } }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res: any) => {
        this.consecutiveGlobalErrors = 0;
        this.unreadChatCount = res.count || 0;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.handleGlobalError(err);
      }
    });
  }

  fetchLowStockCount() {
    this.apiService.get("inventory/api/low_stock/", undefined, { headers: { "X-Background-Request": "true" } }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res: any[]) => {
        this.consecutiveGlobalErrors = 0;
        this.lowStockCount = res ? res.length : 0;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.handleGlobalError(err);
      }
    });
  }

  handleGlobalError(err: any) {
    this.consecutiveGlobalErrors++;
    if (this.consecutiveGlobalErrors > 5) {
      console.error('Global polling failed repeatedly. Stopping.', err);
      this.stopGlobalPolling();
    }
  }

  ngOnDestroy() {
    this.stopGlobalPolling();
  }
  trackById(index: number, item: any): any {
    return item?.id ?? index;
  }

  trackByIndex(index: number, item: any): number {
    return index;
  }

}
