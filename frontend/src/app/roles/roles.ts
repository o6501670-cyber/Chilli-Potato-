import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';

@Component({
  selector: 'app-roles',
  imports: [CommonModule, FormsModule],
  templateUrl: './roles.html',
  styleUrl: './roles.css'
})
export class RolesComponent implements OnInit {
  toastService = inject(ToastService);

  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  roles: any[] = [];
  selectedRole: any = null;
  isSaving = false;

  defaultPermissions = {
    all_centers: false,
    overview: {
      home: { read: false, create: false, update: false, delete: false }
    },
    dashboard: {
      analytics: { read: false, create: false, update: false, delete: false }
    },
    admin: {
      centers: { read: false, create: false, update: false, delete: false },
      users: { read: false, create: false, update: false, delete: false },
      roles: { read: false, create: false, update: false, delete: false },
      services: { read: false, create: false, update: false, delete: false },
      clients: { read: false, create: false, update: false, delete: false },
      bills: { read: false, create: false, update: false, delete: false },
      changes: { read: false, create: false, update: false, delete: false },
      manager_discounts: { read: false, create: false, update: false, delete: false }
    },
    billing: {
      invoices: { read: false, create: false, update: false, delete: false },
      new_invoice: { read: false, create: false, update: false, delete: false }
    },
    appointments: {
      calendar: { read: false, create: false, update: false, delete: false }
    },
    staff: {
      directory: { read: false, create: false, update: false, delete: false },
      logs: { read: false, create: false, update: false, delete: false },
      reports: { read: false, create: false, update: false, delete: false },
      management: { read: false, create: false, update: false, delete: false },
      payrolls: { read: false, create: false, update: false, delete: false }
    },
    inventory: {
      products: { read: false, create: false, update: false, delete: false },
      vendors: { read: false, create: false, update: false, delete: false },
      purchase_orders: { read: false, create: false, update: false, delete: false },
      checkout: { read: false, create: false, update: false, delete: false },
      stock_history: { read: false, create: false, update: false, delete: false },
      po_history: { read: false, create: false, update: false, delete: false },
      audit: { read: false, create: false, update: false, delete: false }
    },
    marketing: {
      campaigns: { read: false, create: false, update: false, delete: false },
      whatsapp: { read: false, create: false, update: false, delete: false },
      usage: { read: false, create: false, update: false, delete: false }
    },
    finance: {
      register_summary: { read: false, create: false, update: false, delete: false },
      monthly_sales: { read: false, create: false, update: false, delete: false },
      detailed_revenues: { read: false, create: false, update: false, delete: false },
      refunds: { read: false, create: false, update: false, delete: false },
      procurement: { read: false, create: false, update: false, delete: false },
      multi_salon: { read: false, create: false, update: false, delete: false },
      incentives: { read: false, create: false, update: false, delete: false },
      pettycash: { read: false, create: false, update: false, delete: false },
      manage: { read: false, create: false, update: false, delete: false }
    }
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
      } catch (e) {}
    }
    this.loadRoles();
  }

  loadRoles() {
    this.apiService.getRoles().subscribe(data => {
      this.roles = data;
      if (this.roles.length > 0) {
        this.selectRole(this.roles[0]);
      } else {
        this.newRole();
      }
      this.cdr.detectChanges();
    });
  }

  selectRole(role: any) {
    this.selectedRole = { ...role };
    const defaultPerms = JSON.parse(JSON.stringify(this.defaultPermissions));
    if (!this.selectedRole.permissions || typeof this.selectedRole.permissions !== 'object') {
      this.selectedRole.permissions = defaultPerms;
    } else {
      for (const key of Object.keys(this.selectedRole.permissions)) {
        const mod = this.selectedRole.permissions[key];
        if (mod && typeof mod === 'object') {
           const isOldFormat = mod.access !== undefined || mod.read !== undefined;
           if (isOldFormat && (typeof mod.read === 'boolean' || typeof mod.access === 'boolean')) {
               const hasAccess = mod.access === true || mod.read === true;
               const newSubmodules = defaultPerms[key as keyof typeof defaultPerms] as any;
               if (newSubmodules) {
                   for (const subKey of Object.keys(newSubmodules)) {
                       mod[subKey] = { read: hasAccess, create: false, update: false, delete: false };
                   }
               }
               delete mod.access; delete mod.read; delete mod.create; delete mod.update; delete mod.delete;
               delete mod.summary; delete mod.reports; delete mod.sales_overview; delete mod.performance;
               delete mod.invoices; delete mod.job_cards; delete mod.client_billing; delete mod.campaigns; delete mod.leads;
           }
        }
      }
      for (const key of Object.keys(defaultPerms)) {
        if (this.selectedRole.permissions[key] === undefined) {
          this.selectedRole.permissions[key] = (defaultPerms as any)[key];
        } else {
          for (const subKey of Object.keys((defaultPerms as any)[key])) {
             if (this.selectedRole.permissions[key][subKey] === undefined) {
                 this.selectedRole.permissions[key][subKey] = (defaultPerms as any)[key][subKey];
             } else {
                 for (const action of ['read', 'create', 'update', 'delete']) {
                     if (this.selectedRole.permissions[key][subKey][action] === undefined) {
                         this.selectedRole.permissions[key][subKey][action] = false;
                     }
                 }
             }
          }
        }
      }
    }
  }

  newRole() {
    this.selectedRole = { 
      name: '', 
      description: '', 
      permissions: JSON.parse(JSON.stringify(this.defaultPermissions)) 
    };
  }

  saveRole() {
    if (this.selectedRole && !this.isSaving) {
      this.isSaving = true;
      if (this.selectedRole.id) {
        this.apiService.updateRole(this.selectedRole.id, this.selectedRole).subscribe({
          next: () => {
            this.apiService.getRoles().subscribe(data => {
              this.roles = data;
              const foundRole = this.roles.find(r => r.id === this.selectedRole.id) || this.roles[0];
              if (foundRole) this.selectRole(foundRole);
              this.cdr.detectChanges();
              this.toastService.showSuccess('Role updated successfully');
              this.isSaving = false;
            });
          },
          error: (err) => {
            this.toastService.showError('Failed to update role: ' + JSON.stringify(err.error));
            this.isSaving = false;
          }
        });
      } else {
        this.apiService.createRole(this.selectedRole).subscribe({
          next: (createdRole) => {
            this.apiService.getRoles().subscribe(data => {
              this.roles = data;
              const foundRole = this.roles.find(r => r.id === createdRole.id) || this.roles[0];
              if (foundRole) this.selectRole(foundRole);
              this.cdr.detectChanges();
              this.toastService.showSuccess('Role created successfully');
              this.isSaving = false;
            });
          },
          error: (err) => {
            this.toastService.showError('Failed to create role: ' + JSON.stringify(err.error));
            this.isSaving = false;
          }
        });
      }
    }
  }

  deleteRole() {
    if (this.selectedRole && this.selectedRole.id && !this.isSaving) {
      if (!confirm('Are you sure you want to delete this role? This action cannot be undone.')) return;
      this.isSaving = true;
      this.apiService.deleteRole(this.selectedRole.id).subscribe({
        next: () => {
          this.toastService.showSuccess('Role deleted successfully');
          this.isSaving = false;
          this.selectedRole = null;
          this.loadRoles();
        },
        error: (err) => {
          this.toastService.showError('Failed to delete role: ' + (err.error?.detail || JSON.stringify(err.error)));
          this.isSaving = false;
        }
      });
    }
  }

  getModuleKeys(): string[] {
    if (!this.selectedRole || !this.selectedRole.permissions) return [];
    return Object.keys(this.selectedRole.permissions).filter(k => k !== 'all_centers');
  }

  getSubModuleKeys(modName: string): string[] {
    if (!this.selectedRole || !this.selectedRole.permissions[modName]) return [];
    return Object.keys(this.selectedRole.permissions[modName]);
  }

  isModuleFullyChecked(modName: string): boolean {
    const subkeys = this.getSubModuleKeys(modName);
    if (subkeys.length === 0) return false;
    for (const sub of subkeys) {
      const perms = this.selectedRole.permissions[modName][sub];
      if (!perms.read || !perms.create || !perms.update || !perms.delete) {
        return false;
      }
    }
    return true;
  }

  isModuleIndeterminate(modName: string): boolean {
    const subkeys = this.getSubModuleKeys(modName);
    if (subkeys.length === 0) return false;
    let hasChecked = false;
    let hasUnchecked = false;
    for (const sub of subkeys) {
      const perms = this.selectedRole.permissions[modName][sub];
      if (perms.read || perms.create || perms.update || perms.delete) hasChecked = true;
      if (!perms.read || !perms.create || !perms.update || !perms.delete) hasUnchecked = true;
    }
    return hasChecked && hasUnchecked;
  }

  onPermissionChange(modName: string, subName: string, action: string, checked: boolean) {
    this.selectedRole.permissions[modName][subName][action] = checked;
    
    // Auto-enforce logical permission rules
    if (checked && (action === 'create' || action === 'update' || action === 'delete')) {
      // If granting write/delete access, must grant read access
      this.selectedRole.permissions[modName][subName].read = true;
    } else if (!checked && action === 'read') {
      // If revoking read access, must revoke write/delete access
      this.selectedRole.permissions[modName][subName].create = false;
      this.selectedRole.permissions[modName][subName].update = false;
      this.selectedRole.permissions[modName][subName].delete = false;
    }
  }

  toggleModule(modName: string, event: any) {
    const checked = event.target.checked;
    const subkeys = this.getSubModuleKeys(modName);
    for (const sub of subkeys) {
      this.selectedRole.permissions[modName][sub].read = checked;
      this.selectedRole.permissions[modName][sub].create = checked;
      this.selectedRole.permissions[modName][sub].update = checked;
      this.selectedRole.permissions[modName][sub].delete = checked;
    }
  }
}
