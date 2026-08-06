import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

@Injectable({
  providedIn: 'root'
})
export class ToastService {
  toasts = signal<Toast[]>([]);
  private idCounter = 0;

  show(message: string, type: ToastType = 'info', duration: number = 4000) {
    const id = this.idCounter++;
    this.toasts.update(current => [...current, { id, message, type }]);

    // Auto dismiss
    setTimeout(() => {
      this.remove(id);
    }, duration);
  }

  showError(message: string) {
    this.show(message, 'error', 5000); // Errors stay slightly longer
  }

  showSuccess(message: string) {
    this.show(message, 'success');
  }

  remove(id: number) {
    this.toasts.update(current => current.filter(t => t.id !== id));
  }
}
