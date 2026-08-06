# POS application audit and hardening report

Date: 2026-08-06

## Verdict

The repository is now in a much safer, testable state for continued staging. The critical data-integrity and cross-centre issues found during the audit were implemented and covered with regression tests. It should still be deployed first to a staging database with realistic data and payment-provider tests; no software can honestly be guaranteed “without any errors” without exercising the exact production MySQL, reverse proxy, printers, scanners, payment devices, backups, and real business data.

## Scope inspected

- Angular frontend: routing, guards, interceptors, API service, all major modules, report screens, billing checkout, responsive/style assets, production bundle, and unit tests.
- Django backend: models, migrations, serializers, viewsets, custom actions, billing finalization, inventory movement, promotions/perks, appointments, staff/payroll, finance reports, audit middleware, token app endpoints, and deployment settings.
- Business areas: centres, users/roles, clients, appointments, services, staff, inventory, purchase orders, billing, payments, refunds, promotions, cards, memberships, packages, cash register, shifts, payroll, audit logs, and dashboard/report APIs.

## Critical hardening implemented

### Security and multi-centre isolation

- Added server-side role/action permissions matching the Roles screen; UI route guards are no longer the only protection.
- Blocked cross-centre invoice/client/product/service/marketing/staff operations.
- Protected role, user, centre, service, inventory, finance, staff, billing, report, and audit endpoints with server permissions.
- Prevented unauthorised users from assigning Owner roles or users to inaccessible centres.
- Made stock transactions read-only so audit history cannot be rewritten through the API.
- Added expiring DRF tokens with a 30-day default lifetime.
- Added stricter app-login throttling for staff/client PIN endpoints.
- Staff/client app PINs are hashed, token-bound, invalidated after PIN changes, and never returned in API responses.
- Audit request-body sanitisation now redacts sensitive keys recursively, including nested invoice/payment data.

### Billing and money integrity

- Added invoice idempotency keys to prevent duplicate bills on retries/double submissions.
- Added `finalized_at` and transactional, one-time invoice finalization.
- Finalization now fails closed: stock, wallets, perks, service logs, promotion ledgers, and appointment completion roll back together on failure.
- Server recalculates invoice line totals and tax amounts; it no longer trusts frontend `total_price` values.
- Payment endpoint now validates status, outstanding amount, tender type, client ownership, value-card ownership/expiry/balance, advance balance, and cashback balance under row locks.
- Negative/over-payments and payment against cancelled/refunded bills are blocked.
- Draft invoices can be cancelled; finalized bills cannot be deleted or edited through the generic update endpoint.
- Added an `InvoiceRefund` ledger and full-refund flow with stock, tender liability, package, entitlement, cashback, and promotion reversal.
- Partial refunds are explicitly rejected until tender-level proportional reversal is implemented rather than silently producing wrong balances.

### Promotions, perks, and package accounting

- Promotions use Decimal arithmetic and validate dates, limits, centre scope, member-only status, and discount values.
- Promotion preview does not write usage/cashback; ledger entries are written only after payment finalization.
- Promotion usage is linked to its invoice and is idempotent.
- Memberships, packages, and value cards now carry their source invoice for exact refund reversal.
- Package redemptions have an immutable allocation ledger so refunds restore the exact package balance instead of guessing the latest matching package.

### Inventory, appointments, finance, and staff

- Inventory lot listing no longer raises a `FieldError` for non-owner users.
- Negative stock checkout/audits are blocked; insufficient retail stock fails the sale instead of flooring stock to zero.
- Purchase order line totals are recalculated server-side; invalid quantities/rates/taxes are rejected; delivered receipt updates are locked against duplicate receipt.
- Appointment writes lock the centre during double-booking validation to close the check-then-insert race.
- Invalid/inactive appointment staff and cross-centre staff assignments are rejected.
- Shift opening is locked per centre to prevent two open registers; shift closing uses Decimal values and a locked row.
- Petty cash/daily closing negative values are rejected.
- Payroll transitions now require Draft → Locked → Paid.
- Staff transfer/tool/payroll bulk endpoints were replaced with handlers for their actual models; they no longer silently create `StaffMember` rows.
- Staff transfer/tool reads no longer run a database-writing synchronisation routine on every GET.
- Refund reports now use actual refund ledger amounts rather than the face value of every cancelled invoice.

### Repository hygiene

- Removed tracked patch/recovery scripts, logs, backups, generated URL dumps, test spreadsheets, and duplicate nested source artifacts from the final repository. Only runtime source, migrations, tests, deployment files, documentation, and required assets remain.

### Frontend and runtime

- Removed production loopback API URLs; the frontend uses same-origin paths.
- Added Angular dev proxy configuration and preview-host support.
- Removed build-time Google Font/CDN dependency; Chart.js is bundled.
- Production build initial bundle is approximately 343 kB raw / 91 kB estimated transfer, down from over 1.4 MB during the initial audit.
- Reduced the fixed boot splash delay from 3.7 seconds to under 1.1 seconds.
- Fixed generated unit-test imports and added offline API mocks.
- Added chart teardown and client event-listener cleanup to reduce navigation memory leaks.
- Added SQLite development fallback while production can explicitly use MySQL.
- Added production security settings, token lifetime configuration, Gunicorn settings, Supervisor configuration, and backend/frontend runbooks.

## Verification completed

- Backend Django system check: **PASS**
- Production-mode `check --deploy` with a supplied secret and SQLite verification database: **PASS**
- Backend migrations and `makemigrations --check`: **PASS**
- Backend test suite: **17 tests passed**
- Billing integrity regressions: idempotency, stock rollback, one-time finalization, full refund reversal, cashback reversal: **PASS**
- Role permission regressions: read allowed only where configured; writes denied without explicit action: **PASS**
- Frontend production build: **PASS**
- Frontend unit tests: **11/11 passed**
- `npm audit --omit=dev --audit-level=high`: **0 vulnerabilities**
- Bandit scan: **0 high / 0 medium severity findings**
- Live preview smoke checks: Angular host **200**, Django host accepted, login **200**, authenticated core report/inventory/billing endpoints **200**

## Staging checklist before live use

1. Use a production MySQL database and run migrations after a backup.
2. Set a new random `DJANGO_SECRET_KEY`; never use `.env.example` values.
3. Set `DJANGO_DEBUG=False`, exact `DJANGO_ALLOWED_HOSTS`, HTTPS CORS/CSRF origins, and Redis.
4. Configure the reverse proxy to serve Angular and forward all API module paths to Django over HTTPS.
5. Test the real receipt printer, barcode scanner, cash drawer, UPI/card gateway callbacks, refund provider, and printer failure/retry behavior.
6. Load-test realistic data volumes, especially detailed finance exports, dashboard reports, client lists, audit logs, and WhatsApp campaigns.
7. Verify database backups and restore them before opening the first live register.
8. Run a staging end-to-end checklist covering draft → hold → resume → pay → refund, split payments, advance, cashback, value card, membership, package redemption, stock receipt/sale/refund, appointment double-booking, shift open/close, and payroll lock/pay.
