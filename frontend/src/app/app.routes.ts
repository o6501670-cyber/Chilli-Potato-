import { Routes } from '@angular/router';
import { authGuard, roleGuard } from './auth.guard';

export const routes: Routes = [
    { path: '', redirectTo: '/login', pathMatch: 'full' },
    { 
        path: 'login', 
        loadComponent: () => import('./login/login').then(m => m.LoginComponent) 
    },
    {
        path: 'admin',
        loadComponent: () => import('./admin/admin').then(m => m.AdminComponent),
        canActivate: [authGuard],
        canActivateChild: [roleGuard],
        children: [
            { path: '', redirectTo: 'home', pathMatch: 'full' },
            { path: 'home', loadComponent: () => import('./home/home').then(m => m.HomeComponent) },
            { path: 'dashboard', loadComponent: () => import('./dashboard/dashboard').then(m => m.DashboardComponent) },
            { path: 'centers', loadComponent: () => import('./centers/centers').then(m => m.CentersComponent) },
            { path: 'users', loadComponent: () => import('./users/users').then(m => m.UsersComponent) },
            { path: 'roles', loadComponent: () => import('./roles/roles').then(m => m.RolesComponent) },
            { path: 'inventory', loadComponent: () => import('./inventory/inventory').then(m => m.InventoryComponent) },
            { path: 'marketing', loadComponent: () => import('./marketing/marketing').then(m => m.MarketingComponent) },
            { path: 'staff', loadComponent: () => import('./staff/staff').then(m => m.StaffComponent) },
            { path: 'appointments', loadComponent: () => import('./appointments/appointments').then(m => m.AppointmentsComponent) },
            { path: 'clients', loadComponent: () => import('./clients/clients').then(m => m.ClientsComponent) },
            { path: 'services', loadComponent: () => import('./services/services').then(m => m.ServicesComponent) },
            { path: 'billing', loadComponent: () => import('./billing/billing').then(m => m.BillingComponent) },
            { path: 'finance', loadComponent: () => import('./finance/finance').then(m => m.FinanceComponent) },
            { path: 'logs', loadComponent: () => import('./admin/logs/logs').then(m => m.LogsComponent) },

            { path: 'bills', loadComponent: () => import('./admin/admin-bills/admin-bills').then(m => m.AdminBillsComponent) },
            { path: 'changes', loadComponent: () => import('./admin/admin-changes/admin-changes').then(m => m.AdminChangesComponent) },
            { path: 'manager-discounts', loadComponent: () => import('./admin/admin-manager-discounts/admin-manager-discounts').then(m => m.AdminManagerDiscountsComponent) }
        ]
    }
];
