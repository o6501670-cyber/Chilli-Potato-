import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';

@Component({
  selector: 'app-billing-landing',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './billing-landing.component.html',
  styleUrls: ['../../billing.css'],
  styles: [`
    :host {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: var(--gap-lg, 24px);
      width: 100%;
      height: 100%;
      padding: 24px;
    }
    
    .landing-col {
      background: #ffffff;
      border-radius: 16px;
      border: 1px solid #e2e8f0;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      display: flex;
      flex-direction: column;
      padding: 24px;
      height: 100%;
      overflow: hidden;
    }
    
    .landing-list {
      flex: 1;
      overflow-y: auto;
      padding-right: 8px;
    }
    
    /* custom scrollbar for landing-list */
    .landing-list::-webkit-scrollbar {
      width: 6px;
    }
    .landing-list::-webkit-scrollbar-thumb {
      background-color: #cbd5e1;
      border-radius: 10px;
    }
    
    .landing-col:hover {
      box-shadow: var(--shadow-md);
      border-color: var(--border-strong);
    }
    
    .landing-header-new {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      font-size: 16px;
      font-weight: 700;
      color: #1e293b;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 12px;
      background: transparent;
    }
    
    .header-icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-size: 14px;
    }
    
    .icon-invoice { background: var(--blue, #2563eb); }
    .icon-appt { background: var(--orange, #c2410c); }
    .icon-staff { background: var(--green, #15803d); }
    
    .landing-list {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    .landing-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      transition: var(--transition);
      box-shadow: var(--shadow-xs);
      cursor: pointer;
    }
    
    .landing-item:hover {
      border-color: var(--border-strong);
      background: var(--bg);
    }
    
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex: 1;
      color: var(--text-tertiary);
      font-weight: 500;
      gap: 12px;
    }
    .empty-state i {
      font-size: 32px;
      color: var(--border-strong);
    }
  `]
})
export class BillingLandingComponent {
  @Input() globalInvoices: any[] = [];
  @Input() appointments: any[] = [];
  @Input() staffActivity: any[] = [];
  @Input() activityFeed: any[] = [];
  @Input() staffMembers: any[] = [];
  
  @Output() onInvoiceClick = new EventEmitter<any>();
  @Output() onDeleteInvoice = new EventEmitter<any>();

  getStaffName(staffId: number | string): string {
    const s = this.staffMembers.find(x => x.id === Number(staffId));
    return s ? `${s.first_name} ${s.last_name}` : 'Unknown';
  }
}
