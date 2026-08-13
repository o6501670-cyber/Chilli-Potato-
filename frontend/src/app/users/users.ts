import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, DestroyRef, OnInit, inject } from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api';
import { ToastService } from '../services/toast.service';

@Component({
  selector: 'app-users',
  imports: [CommonModule, FormsModule],
  templateUrl: './users.html',
  styleUrl: './users.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersComponent implements OnInit {
  todayDate: string = new Date().toISOString().split('T')[0];
  private destroyRef = inject(DestroyRef);
  toastService = inject(ToastService);

  apiService = inject(ApiService);
  cdr = inject(ChangeDetectorRef);
  users: any[] = [];
  currentPage: number = 1;
  pageSize: number = 500;

  get paginatedItems() {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    return this.users.slice(startIndex, startIndex + this.pageSize);
  }

  get totalPages() {
    return Math.ceil(this.users.length / this.pageSize) || 1;
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
  roles: any[] = [];
  centers: any[] = [];
  showModal = false;
  isEditing = false;
  editingId: number | null = null;
  isSaving = false;
  
  newUser: any = {
    email: '',
    full_name: '',
    phone: '',
    designation: '',
    password: '',
    role: null,
    center: null,
    centers: []
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
    this.loadUsers();
    this.loadRoles();
    this.loadCenters();
  }

  loadUsers() {
    this.apiService.getUsers().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data: any) => {
      this.users = Array.isArray(data) ? data : (data.results || []);
        this.currentPage = 1;
      this.cdr.detectChanges();
    });
  }

  loadRoles() {
    this.apiService.getRoles().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.roles = data;
      this.cdr.detectChanges();
    });
  }

  loadCenters() {
    this.apiService.getCenters().pipe(takeUntilDestroyed(this.destroyRef)).subscribe(data => {
      this.centers = data;
      this.cdr.detectChanges();
    });
  }

  openModal() {
    this.showModal = true;
    this.isEditing = false;
    this.resetForm();
  }

  editUser(user: any) {
    this.isEditing = true;
    this.editingId = user.id;
    this.newUser = { ...user, password: '', centers: user.centers ? [...user.centers] : (user.center ? [user.center] : []) }; 
    this.showModal = true;
  }

  closeModal() {
    this.showModal = false;
    this.resetForm();
  }

  resetForm() {
    this.newUser = {
      email: '',
      full_name: '',
      phone: '',
      designation: '',
      password: '',
      role: null,
      center: null,
      centers: []
    };
    this.isEditing = false;
    this.editingId = null;
  }

  addCenterFromSelect(value: string) {
    if (!value) return;
    if (!this.newUser.centers) this.newUser.centers = [];

    if (value === 'all') {
      this.newUser.centers = this.centers.map(c => c.id);
      return;
    }

    const centerId = parseInt(value, 10);
    if (!isNaN(centerId) && !this.newUser.centers.includes(centerId)) {
      this.newUser.centers.push(centerId);
    }
  }

  removeCenter(centerId: number) {
    if (!this.newUser.centers) return;
    this.newUser.centers = this.newUser.centers.filter((id: number) => id !== centerId);
  }

  getCenterName(id: number): string {
    const center = this.centers.find(c => c.id === id);
    return center ? center.center_name : 'Unknown Center';
  }

  getRoleName(id: number): string {
    if (!id) return 'No Role';
    const role = this.roles.find(r => r.id === id);
    return role ? role.name : `Role ID: ${id}`;
  }

  onSubmit() {
    if (this.isSaving) return;
    this.isSaving = true;
    
    const payload: any = { ...this.newUser };
    if (this.isEditing && !payload.password) {
      delete payload.password;
    }
    
    if (this.isEditing && this.editingId) {
      this.apiService.updateUser(this.editingId, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadUsers();
          this.closeModal();
          this.isSaving = false;
        },
        error: (err) => {
          let errMsg = 'Failed to update user';
          if (err.error) {
             if (typeof err.error === 'string') errMsg = err.error;
             else if (typeof err.error === 'object') {
                const msgs: string[] = [];
                for (const key in err.error) {
                   const val = err.error[key];
                   msgs.push(`${key}: ${Array.isArray(val) ? val.join(' ') : val}`);
                }
                errMsg = msgs.join(' | ');
             }
          }
          this.toastService.showError(errMsg);
          this.isSaving = false;
        }
      });
    } else {
      this.apiService.createUser(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.loadUsers();
          this.closeModal();
          this.isSaving = false;
        },
        error: (err) => {
          let errMsg = 'Failed to create user';
          if (err.error) {
             if (typeof err.error === 'string') errMsg = err.error;
             else if (typeof err.error === 'object') {
                const msgs: string[] = [];
                for (const key in err.error) {
                   const val = err.error[key];
                   msgs.push(`${key}: ${Array.isArray(val) ? val.join(' ') : val}`);
                }
                errMsg = msgs.join(' | ');
             }
          }
          this.toastService.showError(errMsg);
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
