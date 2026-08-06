
import re
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: openNewInvoice
old_new = '''  openNewInvoice() {
    this.cart = [];
    this.client = null;
    this.resetConfig();
    this.searchClientTerm = \\'\\';
    this.clientHistory = [];
    this.calculateTotals();
    this.viewMode = \\'new-invoice\\';
  }'''
new_new = '''  openNewInvoice() {
    this.cart = [];
    this.client = null;
    this.resetConfig();
    this.searchPhone = \\'\\';
    this.clientHistory = [];
    this.viewMode = \\'new-invoice\\';
  }'''
text = text.replace(old_new, new_new)

# Fix 2: resetConfig
old_reset = '''  resetConfig() {
    this.managerDiscountPercent = 0;
    this.managerDiscountAmount = 0;
    this.configStaffIds = [];
    this.configMembershipId = null;
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
      if (this.client?.active_memberships?.length > 0) {
         this.configMembershipId = this.client.active_memberships[0].membership_detail.id;
         this.applyConfigMembership();
      }
      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {'''

new_reset = '''  resetConfig() {
    this.managerDiscountPercent = 0;
    this.managerDiscountAmount = 0;
    this.configStaffIds = [];
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {'''
text = text.replace(old_reset, new_reset)

# Fix 3: auto-select membership in selectClient
old_client = '''                    this.promotions.push({
                        id: 'm_' + am.id,
                        name: '?? ' + am.membership_detail.name,
                        discount_percent: am.membership_detail.discount_percent,
                        discount_type: 'Percentage'
                    });
                }
            }
        });
    }'''
new_client = '''                    this.promotions.push({
                        id: 'm_' + am.id,
                        name: '?? ' + am.membership_detail.name,
                        discount_percent: am.membership_detail.discount_percent,
                        discount_type: 'Percentage'
                    });
                }
            }
        });
        // Auto-select the first membership to apply discount automatically
        this.selectedPromotion = this.promotions.find(p => p.id === 'm_' + this.client.active_memberships[0].id);
        this.applyPromotion();
    }'''
text = text.replace(old_client, new_client)

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('Billing TS patched to fix compiler errors')

