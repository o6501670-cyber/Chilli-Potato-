
with open('src/app/billing/billing.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Client Search Empty State
text = text.replace(
'''<div *ngIf="!client && (!searchPhone || clients.length === 0)" class="empty-message text-center mt-5">
        Search a client by phone or name to begin.
      </div>''',
'''<div *ngIf="!client && (!searchPhone || clients.length === 0)" class="empty-message text-center mt-5" style="display: flex; flex-direction: column; align-items: center; justify-content: center; opacity: 0.6; padding: 40px 20px;">
        <i class="fa fa-search" style="font-size: 32px; margin-bottom: 12px; color: var(--text-muted);"></i>
        <div style="font-size: 13px; color: var(--text-secondary); font-weight: 600;">Search a client by phone or name to begin.</div>
      </div>''')

# Client History Empty State
text = text.replace(
'''<tr *ngIf="!clientServiceHistory || clientServiceHistory.length === 0">
              <td colspan="4" style="text-align: center; padding: 20px; color: #94a3b8; font-size: 12px;">No history found</td>
            </tr>''',
'''<tr *ngIf="!clientServiceHistory || clientServiceHistory.length === 0">
              <td colspan="4" style="text-align: center; padding: 30px 10px; color: var(--text-muted); font-size: 12px;">
                <i class="fa fa-folder-open-o" style="font-size: 24px; margin-bottom: 8px; display: block; opacity: 0.5;"></i>
                No history found
              </td>
            </tr>''')

with open('src/app/billing/billing.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Empty states enhanced')

