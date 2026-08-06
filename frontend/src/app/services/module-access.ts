import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ModuleAccessService {
  private getCurrentUser(): any {
    const userStr = localStorage.getItem('user');
    if (!userStr) {
      return null;
    }

    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  isOwner(user: any = null): boolean {
    const currentUser = user ?? this.getCurrentUser();
    return currentUser?.role === 'Owner' || currentUser?.is_superuser === true;
  }

  getPermissions(user: any = null): any {
    const currentUser = user ?? this.getCurrentUser();
    return currentUser?.permissions || {};
  }

  canAccessModule(moduleKey: string, user: any = null): boolean {
    if (this.isOwner(user)) {
      return true;
    }

    const permissions = this.getPermissions(user);

    switch (moduleKey) {
      case 'home':
      case 'overview':
        return true;
      case 'dashboard':
        return !!permissions.dashboard?.access;
      case 'billing':
        return !!permissions.billing?.access;
      case 'appointment':
      case 'appointments':
        return !!permissions.appointment?.access;
      case 'staff':
        return !!permissions.staff?.access;
      case 'inventory':
        return !!permissions.inventory?.access;
      case 'marketing':
        return !!permissions.marketing?.access;
      case 'admin':
      case 'centers':
      case 'users':
      case 'roles':
      case 'services':
      case 'clients':
        return false;
      default:
        return false;
    }
  }

  canAccessRoute(routePath: string | null | undefined, user: any = null): boolean {
    const normalized = (routePath || '').replace(/^\/+|\/+$/g, '');

    if (!normalized || normalized === 'admin') {
      return true;
    }

    const pathWithoutAdmin = normalized.replace(/^admin\//, '');
    switch (pathWithoutAdmin) {
      case 'home':
        return true;
      case 'dashboard':
        return this.canAccessModule('dashboard', user);
      case 'billing':
        return this.canAccessModule('billing', user);
      case 'appointments':
        return this.canAccessModule('appointment', user);
      case 'staff':
        return this.canAccessModule('staff', user);
      case 'inventory':
        return this.canAccessModule('inventory', user);
      case 'marketing':
        return this.canAccessModule('marketing', user);
      case 'centers':
      case 'users':
      case 'roles':
      case 'services':
      case 'clients':
        return this.canAccessModule('admin', user);
      default:
        return true;
    }
  }
}
