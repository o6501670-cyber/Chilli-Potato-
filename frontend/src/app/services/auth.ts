import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  // FIXED: was hardcoded to 'http://localhost:8000', now uses environment config
  private apiUrl = `${environment.apiUrl}/accounts/api/login/`;

  login(credentials: any) {
    return this.http.post<any>(this.apiUrl, credentials).pipe(
      tap(res => {
        if (res.token) {
          localStorage.setItem('token', res.token);
          localStorage.setItem('user', JSON.stringify(res));
          // Smart redirect: owners → home, staff → first permitted module
          const isOwner = res.role === 'Owner' || res.is_superuser === true;
          if (isOwner) {
            this.router.navigate(['/admin/home']);
          } else {
            // Find first accessible module
            const perms = res.permissions || {};
            const modules = ['billing', 'staff', 'inventory', 'marketing', 'finance', 'appointments'];
            let redirected = false;
            for (const mod of modules) {
              const modPerms = perms[mod];
              if (modPerms && typeof modPerms === 'object') {
                const hasRead = Object.values(modPerms).some((s: any) => s && s.read === true);
                if (hasRead) {
                  this.router.navigate(['/admin/' + mod]);
                  redirected = true;
                  break;
                }
              }
            }
            if (!redirected) {
              this.router.navigate(['/admin/home']);
            }
          }
        }
      })
    );
  }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.router.navigate(['/login']);
  }

  isLoggedIn() {
    return !!localStorage.getItem('token');
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getCurrentUser(): any | null {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
}
