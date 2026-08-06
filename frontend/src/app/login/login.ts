import { Component, inject, HostListener, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth';

@Component({
  selector: 'app-login',
  imports: [FormsModule, CommonModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class LoginComponent implements OnInit {
  authService = inject(AuthService);

  credentials = {
    username: '',
    password: ''
  };

  error = '';
  isLoading = false;
  currentDate = new Date();
  
  static hasLoaded = false;
  isInitialLoad = !LoginComponent.hasLoaded;

  constructor() {}

  ngOnInit() {
    LoginComponent.hasLoaded = true;
  }

  @HostListener('window:resize')
  onResize() {
    // Resize handled by CSS
  }

  onMouseMove(event: MouseEvent) {
    // Removed particle interaction
  }

  onSubmit() {
    this.error = '';
    this.isLoading = true;
    this.authService.login(this.credentials).subscribe({
      next: () => {
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 400 || err.status === 401) {
          this.error = 'Invalid email or password';
        } else {
          this.error = `Network Error (${err.status}): Could not connect to backend`;
        }
      }
    });
  }
}
