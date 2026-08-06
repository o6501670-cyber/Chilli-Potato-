
with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()

toast_html = '''
<!-- Toast Notification -->
<div class="toast-notification" [class.show]="toastVisible" [ngClass]="toastType">
  <i class="fa" [ngClass]="{'fa-check-circle': toastType === 'success', 'fa-exclamation-circle': toastType === 'error', 'fa-info-circle': toastType === 'info'}" style="margin-right: 8px;"></i>
  {{ toastMessage }}
</div>
'''

if 'toast-notification' not in text:
    text = text.replace('<!-- force reload html -->', toast_html + '\n<!-- force reload html -->')
    with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
        f.write(text)

with open('src/app/billing/billing.css', 'r', encoding='utf-8') as f:
    css = f.read()

toast_css = '''
/* Toast Notification */
.toast-notification {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 20px;
  border-radius: var(--radius-sm);
  background: var(--ink);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  display: flex;
  align-items: center;
  z-index: 9999;
  opacity: 0;
  transform: translateY(20px);
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-notification.show {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
.toast-notification.success { border-left: 4px solid #10b981; }
.toast-notification.error { border-left: 4px solid #ef4444; }
.toast-notification.info { border-left: 4px solid #3b82f6; }
'''

if 'toast-notification' not in css:
    with open('src/app/billing/billing.css', 'a', encoding='utf-8') as f:
        f.write(toast_css)

print('Toast UI added')

