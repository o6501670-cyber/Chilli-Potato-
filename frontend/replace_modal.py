import sys

html_file = r'c:\Users\Dell\OneDrive - CINNTRA INFO TECH SOLUTIONS PRIVATE LIMITED\Desktop\chowmein\chowmein\chowmein\properback\properback\frontend\src\app\centers\centers.html'

with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('<!-- Modal -->')

new_modals = """<!-- Modal -->
<div class="modal-overlay" *ngIf="showModal">
  <div class="center-modal">
    <div class="modal-header">
      <h2 class="modal-title">{{ isEditing ? 'Edit Center' : 'Add New Center' }}</h2>
      <button (click)="closeModal()" class="modal-close">&times;</button>
    </div>
    
    <form (ngSubmit)="onSubmit()" ngNativeValidate>
      <h4 class="section-heading" style="margin-top: 0;">Center Details</h4>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Center Name *</label>
          <input type="text" [(ngModel)]="newCenter.center_name" name="center_name" required class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Display Name</label>
          <input type="text" [(ngModel)]="newCenter.display_name" name="display_name" class="form-input">
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Address</label>
          <input type="text" [(ngModel)]="newCenter.address" name="address" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">GST Number</label>
          <input type="text" [(ngModel)]="newCenter.gst_number" name="gst_number" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Pan Number</label>
          <input type="text" [(ngModel)]="newCenter.pan_number" name="pan_number" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Phone</label>
          <input type="text" [(ngModel)]="newCenter.phone" name="phone" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Phone 2</label>
          <input type="text" [(ngModel)]="newCenter.phone_2" name="phone_2" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Region</label>
          <input type="text" [(ngModel)]="newCenter.region" name="region" class="form-input">
        </div>
        <div class="form-group">
          <label class="form-label">Monthly Target</label>
          <input type="number" [(ngModel)]="newCenter.monthly_target" name="monthly_target" class="form-input">
        </div>
      </div>
      
      <h4 class="section-heading">Owners</h4>
      <div class="form-grid">
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Owner 1</label>
          <div class="multi-input-grid">
            <input type="text" [(ngModel)]="newCenter.owner_name" name="owner_name" placeholder="Full Name" class="form-input">
            <input type="text" [(ngModel)]="newCenter.owner_phone" name="owner_phone" placeholder="Mobile" class="form-input">
            <input type="email" [(ngModel)]="newCenter.owner_email_1" name="owner_email_1" placeholder="Email" class="form-input">
          </div>
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Owner 2</label>
          <div class="multi-input-grid">
            <input type="text" [(ngModel)]="newCenter.owner_name_2" name="owner_name_2" placeholder="Full Name" class="form-input">
            <input type="text" [(ngModel)]="newCenter.owner_phone_2" name="owner_phone_2" placeholder="Mobile" class="form-input">
            <input type="email" [(ngModel)]="newCenter.owner_email_2" name="owner_email_2" placeholder="Email" class="form-input">
          </div>
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Owner 3</label>
          <div class="multi-input-grid">
            <input type="text" [(ngModel)]="newCenter.owner_name_3" name="owner_name_3" placeholder="Full Name" class="form-input">
            <input type="text" [(ngModel)]="newCenter.owner_phone_3" name="owner_phone_3" placeholder="Mobile" class="form-input">
            <input type="email" [(ngModel)]="newCenter.owner_email_3" name="owner_email_3" placeholder="Email" class="form-input">
          </div>
        </div>
      </div>
      
      <h4 class="section-heading">Accountants</h4>
      <div class="form-grid">
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Accountant 1</label>
          <div class="multi-input-grid">
            <input type="text" [(ngModel)]="newCenter.accountant_name_1" name="accountant_name_1" placeholder="Full Name" class="form-input">
            <input type="text" [(ngModel)]="newCenter.accountant_phone_1" name="accountant_phone_1" placeholder="Mobile" class="form-input">
            <input type="email" [(ngModel)]="newCenter.accountant_email_1" name="accountant_email_1" placeholder="Email" class="form-input">
          </div>
        </div>
        <div class="form-group" style="grid-column: 1 / -1;">
          <label class="form-label">Accountant 2</label>
          <div class="multi-input-grid">
            <input type="text" [(ngModel)]="newCenter.accountant_name_2" name="accountant_name_2" placeholder="Full Name" class="form-input">
            <input type="text" [(ngModel)]="newCenter.accountant_phone_2" name="accountant_phone_2" placeholder="Mobile" class="form-input">
            <input type="email" [(ngModel)]="newCenter.accountant_email_2" name="accountant_email_2" placeholder="Email" class="form-input">
          </div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end;">
        <button type="submit" class="btn-submit">
          {{ isEditing ? 'Save Changes' : 'Create Center' }}
        </button>
      </div>
    </form>
  </div>
</div>

<!-- Detail Modal -->
<div class="modal-overlay" *ngIf="showDetailModal">
  <div class="center-modal detail-modal">
    
    <div class="modal-header">
      <h2 class="modal-title">{{ detailCenter.center_name }}</h2>
      <button (click)="closeDetail()" class="modal-close">&times;</button>
    </div>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem;">
      
      <!-- Target -->
      <div class="detail-card" style="text-align: center;">
        <div class="section-heading" style="margin-top:0;">Monthly Target</div>
        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem;">Update this salon's monthly target.</div>
        <select [(ngModel)]="selectedMonth" (change)="onMonthSelect()" class="form-input" style="width: 150px; text-align: center; margin-bottom: 0.5rem; margin-left: auto; margin-right: auto; display: block;">
          <option *ngFor="let m of monthOptions" [value]="m">{{m}}</option>
        </select>
        <input type="number" [(ngModel)]="currentTargetInput" class="form-input" style="width: 150px; text-align: center; margin-bottom: 1rem; margin-left: auto; margin-right: auto; display: block;">
        <button (click)="updateTarget()" class="btn btn-primary" style="padding: 6px 16px; font-size: 0.75rem;">Update</button>
      </div>
      
      <!-- SMS -->
      <div class="detail-card" style="text-align: center;">
        <div class="section-heading" style="margin-top:0;">Closing SMS</div>
        <div style="display: flex; justify-content: center; gap: 8px;">
          <input type="text" [(ngModel)]="newSmsNumber" placeholder="Mobile (10 digits)" class="form-input" style="width: 150px;">
          <button (click)="addSms()" class="btn btn-primary" style="padding: 6px 16px; font-size: 0.75rem;">Add</button>
        </div>
        <div style="margin-top: 1rem; border: 1px solid var(--border-color); border-radius: 8px; min-height: 80px; max-width: 250px; margin-left: auto; margin-right: auto; background: white; overflow: hidden;">
          <div *ngFor="let num of detailCenter.closing_sms_recipients; let i = index" style="padding: 0.5rem 0.75rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;">
            <span>{{num}}</span>
            <button (click)="removeSms(i)" style="background: none; border: none; cursor: pointer; color: #999; font-size: 1.25rem; padding: 0;">&times;</button>
          </div>
        </div>
      </div>
    </div>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem;">
      <!-- Credit Limit -->
      <div class="detail-card" style="text-align: center;">
        <div class="section-heading" style="margin-top:0;">Credit Limit / Client</div>
        <div style="display: flex; justify-content: center; gap: 8px;">
          <input type="number" [(ngModel)]="detailCenter.credit_limit" class="form-input" style="width: 100px; text-align: center;">
          <button (click)="updateCreditLimit()" class="btn btn-primary" style="padding: 6px 16px; font-size: 0.75rem;">Update</button>
        </div>
      </div>
      
      <!-- GST Setting -->
      <div class="detail-card" style="text-align: center;">
        <div class="section-heading" style="margin-top:0;">GST Setting</div>
        <div style="font-weight: 700; cursor: pointer; font-size: 0.95rem; color: var(--primary-color);" (click)="toggleGst()">
          {{ detailCenter.gst_enabled ? 'Enabled' : 'Disabled' }}
        </div>
      </div>
    </div>

    <!-- Center Details View -->
    <div class="detail-card">
      <h4 class="section-heading" style="margin-top:0;">Center Details</h4>
      
      <div style="margin-bottom: 1rem; font-size: 0.85rem;">
        Launched on <span style="font-weight: 600; color: var(--primary-color);">{{ detailCenter.launched_on || 'Not Set' }}</span>
      </div>

      <div style="display: grid; grid-template-columns: 120px 1fr; gap: 0.5rem 1rem; font-size: 0.8rem; align-items: center;">
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Display Name:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.display_name }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Address:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.address }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Region:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.region }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">GST Number:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.gst_number }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Pan Number:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.pan_number }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Phone:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.phone }}</div>
        
        <div style="text-align: right; color: var(--text-secondary); font-weight: 600;">Owner Name:</div>
        <div style="background: var(--input-bg); padding: 0.4rem 0.6rem; border-radius: 6px;">{{ detailCenter.owner_name }}</div>
      </div>
    </div>
    
  </div>
</div>
"""

new_content = parts[0] + new_modals
with open(html_file, 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done replacing HTML.')
