"""Server-side permissions matching the Roles & Permissions JSON in the UI."""

from rest_framework.permissions import BasePermission

from .access import has_action_permission, has_global_access


def _target(path: str):
    p = path.lower().split('?', 1)[0].rstrip('/')
    rules = (
        ('/accounts/api/users', 'admin', 'users'),
        ('/salon_admin/api/roles', 'admin', 'roles'),
        ('/salon_admin/api/centers', 'admin', 'centers'),
        ('/salon_admin/api/dashboard', 'dashboard', 'analytics'),
        ('/audit_logs', 'admin', 'changes'),
        ('/clients/api/clients', 'admin', 'clients'),
        ('/services/api', 'admin', 'services'),
        ('/appointments/api/appointments', 'appointments', 'calendar'),
        ('/billing/invoices', 'billing', 'invoices'),
        ('/billing/advances', 'billing', 'invoices'),
        ('/billing/change-logs', 'admin', 'changes'),
        ('/inventory/api/products/checkout', 'inventory', 'checkout'),
        ('/inventory/api/products/audit', 'inventory', 'audit'),
        ('/inventory/api/products/stock_history', 'inventory', 'stock_history'),
        ('/inventory/api/products', 'inventory', 'products'),
        ('/inventory/api/vendors', 'inventory', 'vendors'),
        ('/inventory/api/purchase-orders', 'inventory', 'purchase_orders'),
        ('/inventory/api/lots', 'inventory', 'products'),
        ('/inventory/api/stock-transactions', 'inventory', 'audit'),
        ('/inventory/api/low_stock', 'inventory', 'products'),
        ('/marketing/api/promotions/usage_report', 'marketing', 'usage'),
        ('/marketing/api/promotions', 'marketing', 'campaigns'),
        ('/marketing/api/cards', 'marketing', 'campaigns'),
        ('/marketing/api/memberships', 'marketing', 'campaigns'),
        ('/marketing/api/packages', 'marketing', 'campaigns'),
        ('/marketing/api/whatsapp', 'marketing', 'whatsapp'),
        ('/staff/api/reports', 'staff', 'reports'),
        ('/staff/api/members', 'staff', 'directory'),
        ('/staff/api/logs', 'staff', 'logs'),
        ('/staff/api/consumptions', 'staff', 'logs'),
        ('/staff/api/transfers', 'staff', 'management'),
        ('/staff/api/tools', 'staff', 'management'),
        ('/staff/api/payrolls', 'staff', 'payrolls'),
        ('/staff/api/designations', 'staff', 'management'),
        ('/finance/api/reports', 'finance', 'detailed_revenues'),
        ('/finance/api/register_summary', 'finance', 'register_summary'),
        ('/finance/api/monthly_sales', 'finance', 'monthly_sales'),
        ('/finance/api/detailed_revenues', 'finance', 'detailed_revenues'),
        ('/finance/api/refunds', 'finance', 'refunds'),
        ('/finance/api/procurement', 'finance', 'procurement'),
        ('/finance/api/petty-cash', 'finance', 'pettycash'),
        ('/finance/api/daily-closing', 'finance', 'pettycash'),
        ('/finance/api/shifts', 'finance', 'pettycash'),
        ('/finance/api/incentives', 'finance', 'incentives'),
        ('/finance/api/rules', 'finance', 'incentives'),
    )
    for prefix, module, submodule in rules:
        if p.startswith(prefix):
            return module, submodule
    return None, None


def _action(request):
    path = request.path.lower()
    if request.method == 'GET':
        return 'read'
    if request.method == 'DELETE':
        return 'delete'
    # Detail actions mutate a business state but are not ordinary record edits.
    if any(f'/{name}' in path for name in (
        'pay', 'refund', 'cancel', 'close_shift', 'mark_paid', 'lock',
        'toggle-status', 'apply_promo', 'change_payment', 'duplicate',
    )):
        return 'update'
    return 'create' if request.method == 'POST' else 'update'


class RoleActionPermission(BasePermission):
    """Require the authenticated user's explicit module/action permission."""

    message = 'You do not have permission to perform this action.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if has_global_access(user):
            return True
        module, submodule = _target(request.path)
        if not module:
            return False
        action = _action(request)
        if module == 'billing' and has_action_permission(user, 'admin', 'bills', action):
            return True
        if module == 'admin' and submodule == 'changes' and has_action_permission(user, 'admin', 'changes', action):
            return True
        if action == 'read' and module == 'admin' and submodule == 'centers':
            if getattr(user, 'center_id', None) or user.centers.exists():
                return True
        if action == 'read':
            # POS screens need read-only master data (centres, clients, staff,
            # services, products and perks) even when the operator is not an
            # administrator for that master-data screen.
            read_dependencies = {
                ('admin', 'centers'): [('admin', 'centers')],
                ('admin', 'clients'): [('admin', 'clients'), ('billing', 'invoices'), ('billing', 'new_invoice'), ('appointments', 'calendar')],
                ('admin', 'services'): [('admin', 'services'), ('billing', 'invoices'), ('appointments', 'calendar')],
                ('staff', 'directory'): [('staff', 'directory'), ('billing', 'invoices'), ('appointments', 'calendar')],
                ('inventory', 'products'): [('inventory', 'products'), ('billing', 'invoices')],
                ('marketing', 'campaigns'): [('marketing', 'campaigns'), ('billing', 'invoices')],
            }
            dependencies = read_dependencies.get((module, submodule), [(module, submodule)])
            if any(has_action_permission(user, mod, sub, 'read') for mod, sub in dependencies):
                return True
        candidates = [(module, submodule)]
        if module == 'billing':
            candidates.append(('billing', 'new_invoice'))
        if module == 'appointments':
            candidates.append(('appointments', 'calendar'))
        return any(has_action_permission(user, mod, sub, action) for mod, sub in candidates)
