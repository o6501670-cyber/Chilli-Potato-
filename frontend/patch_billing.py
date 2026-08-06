
import re
with open('src/app/billing/billing.ts', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: openNewInvoice
text = text.replace('''  openNewInvoice() {

    this.viewMode = \\'new-invoice\\';

  }''', '''  openNewInvoice() {
    this.cart = [];
    this.client = null;
    this.resetConfig();
    this.searchClientTerm = \\'\\';
    this.clientHistory = [];
    this.calculateTotals();
    this.viewMode = \\'new-invoice\\';
  }''')

# Fix 2: Advance staff
old_adv = '''    if (this.configType === \\'advance\\') {

      const entry = {

        content_type: \\'advance\\',

        object_id: null,

        description: this.advanceDescription || \\'Advance Payment\\',

        unit_price: this.advanceAmount || 0,

        discount: 0,

        quantity: 1,

        staff: null

      };'''
new_adv = '''    if (this.configType === \\'advance\\') {
      const entry = {
        content_type: \\'advance\\',
        object_id: null,
        description: this.advanceDescription || \\'Advance Payment\\',
        unit_price: this.advanceAmount || 0,
        discount: 0,
        quantity: 1,
        staff: this.configStaffIds.length > 0 ? this.configStaffIds[0] : null,
        staff_members: this.configStaffIds
      };'''
text = re.sub(re.escape(old_adv).replace(r'\n', r'\s*'), new_adv, text)

# Fix 3: Remove old injected services before injecting new ones
old_inject = '''    // Inject Active Packages into Services (Redeem for Rs. 0)

    if (this.client.active_packages && this.client.active_packages.length > 0) {'''
new_inject = '''    // Inject Active Packages into Services (Redeem for Rs. 0)
    this.services = this.services.filter((s: any) => !(s.name && s.name.startsWith('?? [Redeem]')));
    if (this.client.active_packages && this.client.active_packages.length > 0) {'''
text = re.sub(re.escape(old_inject).replace(r'\n', r'\s*'), new_inject, text)

# Fix 4: Auto-apply membership
old_reset = '''    this.configStaffIds = [];
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {'''
new_reset = '''    this.configStaffIds = [];
    this.configMembershipId = null;
    if (this.selectedItemForConfig) {
      this.finalConfigPrice = this.getEffectivePrice(this.selectedItemForConfig);
      if (this.client?.active_memberships?.length > 0) {
         this.configMembershipId = this.client.active_memberships[0].membership_detail.id;
         this.applyConfigMembership();
      }
      if (this.selectedItemForConfig.services_json && Array.isArray(this.selectedItemForConfig.services_json)) {'''
text = text.replace(old_reset, new_reset)

with open('src/app/billing/billing.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('Billing TS patched successfully.')

