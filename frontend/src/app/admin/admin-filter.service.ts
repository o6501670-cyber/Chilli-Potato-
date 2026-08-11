import { Injectable } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AdminFilterService {
  private today = new Date();
  private thirtyDaysAgo = new Date();
  
  constructor() {
    this.thirtyDaysAgo.setDate(this.today.getDate() - 30);
  }

  // Filter State
  selectedCenterId$ = new BehaviorSubject<number | null>(null);
  fromDate$ = new BehaviorSubject<string>(this.thirtyDaysAgo.toISOString().split('T')[0]);
  toDate$ = new BehaviorSubject<string>(this.today.toISOString().split('T')[0]);
    // Event Triggers
  private applySubject = new Subject<void>();
  apply$ = this.applySubject.asObservable();

  private exportSubject = new Subject<void>();
  export$ = this.exportSubject.asObservable();

  // Getters for current state
  get currentCenterId() { return this.selectedCenterId$.value; }
  get currentFromDate() { return this.fromDate$.value; }
  get currentToDate() { return this.toDate$.value; }
    // Setters
  setCenterId(id: number | null) { this.selectedCenterId$.next(id); }
  setFromDate(date: string) { this.fromDate$.next(date); }
  setToDate(date: string) { this.toDate$.next(date); }
    // Actions
  triggerApply() {
    this.applySubject.next();
  }

  triggerExport() {
    this.exportSubject.next();
  }
}
