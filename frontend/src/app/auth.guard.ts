import { inject } from '@angular/core';
import { Router, CanActivateFn, ActivatedRouteSnapshot } from '@angular/router';

export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  const token = localStorage.getItem('token');
  const userStr = localStorage.getItem('user');

  if (token && token.length > 0 && userStr) {
    try {
      JSON.parse(userStr);
      return true;
    } catch {
      // JSON parsing failed, invalid state
    }
  }

  router.navigate(['/login']);
  return false;
};

export const roleGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const router = inject(Router);
  const userStr = localStorage.getItem('user');

  // FIXED: If no user data at all, deny access (was falling through to return true)
  if (!userStr) {
    router.navigate(['/login']);
    return false;
  }

  try {
    const user = JSON.parse(userStr);
    const isOwner = (user.is_superuser === true) || (
      typeof user.role === 'string'
        ? user.role.toLowerCase() === 'owner'
        : user.role?.name?.toLowerCase() === 'owner'
    );

    // Owners/superusers bypass all permission checks
    if (isOwner) return true;

    // FIXED: If user has no role and is not owner, block access to protected routes
    const permissions = user.permissions;
    if (!permissions || typeof permissions !== 'object') {
      router.navigate(['/admin/home']);
      return false;
    }

    const hasModuleReadAccess = (modName: string) => {
      const mod = permissions[modName];
      if (!mod || typeof mod !== 'object') return false;
      return Object.values(mod).some((sub: any) => sub && sub.read === true);
    };

    const path = route.routeConfig?.path;

    // Admin sub-module routes
    const adminSubModules: { [key: string]: string } = {
      'centers': 'centers',
      'users': 'users',
      'roles': 'roles',
      'services': 'services',
      'clients': 'clients',
      'bills': 'bills',
      'changes': 'changes',
      'manager-discounts': 'manager_discounts',
    };

    if (path && adminSubModules[path]) {
      if (!permissions.admin || !permissions.admin[adminSubModules[path]]?.read) {
        router.navigate(['/admin/home']);
        return false;
      }
    }

    // Module-level routes
    const moduleRoutes: { path: string; module: string }[] = [
      { path: 'dashboard', module: 'dashboard' },
      { path: 'billing', module: 'billing' },
      { path: 'staff', module: 'staff' },
      { path: 'inventory', module: 'inventory' },
      { path: 'marketing', module: 'marketing' },
      { path: 'finance', module: 'finance' },
    ];

    for (const { path: routePath, module } of moduleRoutes) {
      if (path === routePath && !hasModuleReadAccess(module)) {
        router.navigate(['/admin/home']);
        return false;
      }
    }

    if (path === 'home' && !hasModuleReadAccess('overview')) {
      // Find first accessible module to redirect to
      for (const { path: fallbackPath, module } of moduleRoutes) {
        if (hasModuleReadAccess(module)) {
          router.navigate(['/admin/' + fallbackPath]);
          return false;
        }
      }
      // If no modules accessible, they might only have some admin submodules
      if (permissions.admin && Object.values(permissions.admin).some((s: any) => s.read)) {
        router.navigate(['/admin/clients']); // Just an example admin module they might have
        return false;
      }
      // If nothing is accessible, force logout
      router.navigate(['/login']);
      return false;
    }

    // Appointments has two possible permission key names (legacy support)
    if (path === 'appointments') {
      if (!hasModuleReadAccess('appointment') && !hasModuleReadAccess('appointments')) {
        router.navigate(['/admin/home']);
        return false;
      }
    }

    return true;

  } catch (e) {
    console.error('Error parsing user permissions', e);
    // Corrupt user data — kick back to login
    router.navigate(['/login']);
    return false;
  }
};
