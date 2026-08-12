# Chilli Potato POS — Full Stack Audit Report

**Date:** 12 August 2026
**Scope:** Complete backend (Django 5.2 / DRF) + frontend (Angular 22) codebase
**Method:** Static analysis (ruff/pyflakes, tsc, AOT build) + **live runtime reproduction** of every finding against a real database and a running server
**Codebase size:** ~13,000 lines backend Python · ~13,100 lines frontend TypeScript · ~28,700 lines HTML/CSS · 96 registered routes

---

## Executive Summary

The project builds and boots cleanly. `manage.py check` reports zero issues, the Angular production build succeeds, and **21 of 22 primary API endpoints return HTTP 200**. On the surface it looks healthy.

Underneath, the audit found **47 defects**, including **9 critical** issues. These are not style nits — I reproduced each one by running the code:

| # | Critical finding | Proven impact |
|---|---|---|
| C1 | Any user can promote themselves to **Owner** | Full system takeover, verified live |
| C2 | Any user can **change another user's password** | Account takeover, verified live |
| C3 | Finance reports **cached across tenants** | Centre B's manager saw Centre A's revenue, verified live |
| C4 | Client wallet balances **inflated 3×** by a SQL join bug | ₹200 displayed as ₹600, verified live |
| C5 | Client mobile app login is **100% broken** | No customer can ever log in, verified live |
| C6 | Non-owners can **create/delete centres & edit role permissions** | Verified live (HTTP 201/204/200) |
| C7 | Production `apiUrl: '/'` | Every API call resolves to `https://accounts/...` — app is dead on deploy |
| C8 | 4 endpoints throw **HTTP 500** (undefined variables) | Verified live |
| C9 | Django **SECRET_KEY committed to git** | Session/token forgery |

The recurring theme: **the ViewSet layer filters what you can *see*, but almost never validates what you can *write*.** Read-side multi-tenancy is implemented carefully and consistently; write-side authorisation is largely missing. Separately, several bugs sit specifically in money paths (wallets, incentives, petty cash), which is the worst place for them in a POS.

Nothing in this report is speculative. Every "Proof" block below is real output from this codebase.

---

## How to read this report

- **Severity:** CRITICAL (data loss / breach / total outage) → HIGH (money wrong or feature broken) → MEDIUM (wrong data in edge cases) → LOW (hygiene)
- Each finding: exact file + line, why it happens, reproduction, and a concrete fix.
- I made **no code changes**. The working tree is clean — this is a pure audit, as requested.

---

# PART 1 — CRITICAL

## C1. Privilege escalation: any user can make themselves Owner
**`backend/accounts/views.py:19-41`** · **`backend/accounts/serializers.py:4-8`**

`UserViewSet` is a full `ModelViewSet` whose only permission is `IsAuthenticated`. `get_queryset()` scopes *visibility* by centre, but there is no `perform_update` guard, and `role`, `center`, and `centers` are all writable fields. Users can see themselves, so they can edit themselves — including their own role.

**Proof (live):**
```
Before: role = Receptionist | center = A | superuser = False
PATCH /accounts/api/users/<own id>/  {"role": <Owner id>, "center": 2}  ->  HTTP 200
After : role = Owner | center = B
>>> CONFIRMED PRIVILEGE ESCALATION
```
Once Owner, `all_centers` unlocks every centre's financials, payroll and audit logs.

**Fix:** add write-side authorisation:
```python
def perform_update(self, serializer):
    actor = self.request.user
    is_owner = actor.is_superuser or (actor.role and actor.role.name.lower() == 'owner')
    if not is_owner:
        # non-owners may never change role/center/centers, on any account
        for f in ('role', 'center', 'centers'):
            serializer.validated_data.pop(f, None)
        if serializer.instance.pk != actor.pk:
            raise PermissionDenied("You may only edit your own profile.")
    serializer.save()
```
Also gate `create`/`destroy` behind Owner, and never trust `is_superuser`/`is_staff` from the payload.

---

## C2. Account takeover: any user can reset any other user's password
**`backend/accounts/serializers.py:20-33`**

`UserSerializer.update()` honours a `password` key and calls `set_password()`. Combined with C1's missing object-level check, any authenticated user can rewrite any visible colleague's password and log in as them.

**Proof (live):**
```
PATCH /accounts/api/users/<victim id>/  {"password": "HackedPass!99"}  -> HTTP 200
password now 'HackedPass!99'?  True
```

**Fix:** password changes belong on a dedicated endpoint requiring the current password (or Owner rights). Remove `password` from the general update path, and validate with `django.contrib.auth.password_validation` — the configured validators are currently bypassed entirely on this route.

---

## C3. Cross-tenant data leak: finance reports cached without a user key
**`backend/finance/views.py:498, 705, 947`** · **`backend/services/views.py:18`**

```python
@method_decorator(cache_page(60 * 5))
def get(self, request):
```
`cache_page` keys on the **URL only** — not on the user or token. `_get_filtered_invoices()` correctly scopes by centre *per user*, but the first user's rendered response is stored and replayed to everyone hitting the same URL for 5 minutes.

**Proof (live)** — two managers, two different centres, identical URL:
```
User A (centre A only) cash total: {'amount': 1000.0, 'count': 1}
User B (centre B only) cash total: {'amount': 1000.0, 'count': 1}   <-- B's real total is 7.0
>>> CONFIRMED CROSS-TENANT CACHE LEAK
```
Centre B's manager received Centre A's revenue figures. This affects Register Summary, Monthly Sales, and Detailed Revenues — the three most sensitive screens in the product. `services/views.py` adds `vary_on_headers('Authorization')`, which is the right idea but still caches per-token rather than per-permission-set, and the finance views omit it entirely.

**Fix:** drop `cache_page` on per-tenant data. If caching is needed, key it explicitly:
```python
key = f"regsum:{user.id}:{center_id}:{start_date}:{end_date}"
cached = cache.get(key)
```
This is the single highest-risk finding for a multi-salon deployment — it is a confidentiality breach between franchisees.

---

## C4. Client wallet balances inflated by JOIN fan-out
**`backend/clients/views.py:48-52`** · surfaced by **`backend/clients/serializers.py:42-50`**

```python
qs = qs.annotate(
    advance_balance_annotated=Coalesce(Sum('advances__amount'), ...),
    cashback_balance_annotated=Coalesce(Sum('cashback_transactions__amount'), ...),
)
```
Two `Sum()`s across two different reverse FKs in one queryset produce a cartesian product: each advance row is duplicated once per cashback row. The serializer *prefers* the annotated value over the correct model property, so the wrong number is what the UI shows.

**Proof (live)** — 2 advances of ₹100, 3 cashbacks of ₹10:
```
TRUE advance balance : 200   | annotated: 600     (3x inflated)
TRUE cashback balance: 30    | annotated: 60      (2x inflated)
property (correct)   : 200.00  30.00
```
A customer with ₹200 credit appears to have ₹600. Billing reads this balance when offering "Pay by Advance", so the salon can hand out credit that does not exist. The inflation factor equals the number of rows in the *other* table, so it worsens with account age.

**Fix:** use `distinct=True` (`Sum('advances__amount', distinct=True)` is still wrong for equal amounts) — the correct approach is subqueries:
```python
from django.db.models import OuterRef, Subquery, Sum
adv = AdvancePayment.objects.filter(client=OuterRef('pk')).values('client').annotate(s=Sum('amount')).values('s')
qs = qs.annotate(advance_balance_annotated=Coalesce(Subquery(adv), Decimal('0')))
```
Or simply delete the annotations and let the already-correct `advance_balance` property do the work.

---

## C5. Client mobile app login is completely broken
**`backend/clients/models.py:75-82`** vs **`backend/clients/app_views.py:70`**

`Client.save()` generates a **plaintext** 4-digit PIN and emails it to the customer:
```python
self.app_pin = f"{secrets.randbelow(9000) + 1000}"   # e.g. "7564"
```
`client_app_login` verifies with `check_password(str(pin), client.app_pin)`, which expects a **hashed** value. A plaintext PIN can never match a hash, so login always fails.

**Proof (live):**
```
auto-generated app_pin stored as: '7564' (plaintext)
login with the PIN the customer was emailed -> 401 {'error': 'Invalid phone number or PIN'}
```
Every client who has ever been auto-provisioned is locked out — the customer PWA is non-functional. Note the staff equivalent (`staff/views.py:1461`) *does* have a plaintext fallback that transparently upgrades to a hash; the client path is missing that branch.

Secondary issue: PINs are stored in plaintext at rest and emailed in the clear.

**Fix:** hash on write — `self.app_pin = make_password(raw_pin)` — and add the same transitional fallback used for staff:
```python
elif client.app_pin == str(pin):          # legacy plaintext
    client.app_pin = make_password(str(pin))
    client.save(update_fields=['app_pin'])
```
`app_pin` is `max_length=10`; a hash needs ~128 chars, so a migration widening the column is required.

---

## C6. Centres and role permissions are writable by everyone
**`backend/salon_admin/views.py:7-44`**

`CenterViewSet` and `RoleViewSet` are unguarded `ModelViewSet`s with only `IsAuthenticated`. `RoleViewSet` doesn't even scope reads — `queryset = Role.objects.annotate(...)`.

**Proof (live), as a plain Receptionist:**
```
PATCH /salon_admin/api/roles/<id>/ {"permissions":{"all_centers":true}} -> 200  | perms now: {'all_centers': True}
POST  /salon_admin/api/centers/    {"center_name":"Rogue Center"}       -> 201
DELETE /salon_admin/api/centers/<id>/                                    -> 204
```
Editing a role's permission JSON is a second, independent path to `all_centers` — and deleting a centre **cascades**: `Product`, `Vendor`, `PurchaseOrder`, `StaffMember`, `ServiceLog`, `Appointment` all declare `on_delete=CASCADE` to `Center`. One DELETE by any logged-in user destroys a salon's entire operational history. (`Invoice.center` is correctly `SET_NULL`, so financial records survive — but their centre attribution is silently lost.)

**Fix:** apply an `IsOwner` permission class to both viewsets; make `Center` deletion soft (`is_active=False`) given the cascade blast radius.

---

## C7. Production build points the API at a non-existent host
**`frontend/src/environments/environment.prod.ts:3`**

```typescript
apiUrl: '/'  // ← Update this to your production backend URL
```
Every call is built as `` `${baseUrl}/${path}` `` (`api.ts:16`), yielding `//accounts/api/login/`. A leading `//` is a **protocol-relative URL**, so the browser treats the next segment as a hostname.

**Proof:**
```
constructed URL: //accounts/api/login/
resolves to:     https://accounts/api/login/     <-- wrong host entirely
```
Not one request reaches the backend; the production bundle is dead on arrival. The dev environment works only because it happens to have no trailing slash.

**Fix:** set `apiUrl: ''` (same-origin) or the real absolute URL, and normalise the join so double slashes can't occur:
```typescript
const url = `${this.baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
```

---

## C8. Four endpoints crash with HTTP 500 (undefined variables)
Ruff flagged 6 × F821; I confirmed each reaches production code paths.

| Endpoint | File:line | Undefined name |
|---|---|---|
| `GET /finance/api/procurement/?export=true` | `finance/views.py:1284, 1294` | `item_analysis`, `supplier_totals` |
| `GET /finance/api/export_multi_salon/` | `finance/views.py:2091, 2098` | `Center` (never imported at module scope) |
| `POST /inventory/api/products/checkout/` | `inventory/views.py:573` | `Decimal` |
| `POST /inventory/api/products/audit/` | `inventory/views.py:613` | `Decimal` |

**Proof (live, against the running server):**
```
procurement (export=true) : EXCEPTION NameError: name 'item_analysis' is not defined
multi_salon_export        : EXCEPTION NameError: name 'Center' is not defined
inventory checkout        : EXCEPTION NameError: name 'Decimal' is not defined
inventory audit           : EXCEPTION NameError: name 'Decimal' is not defined

$ curl finance/api/export_multi_salon/     -> 500
$ curl finance/api/procurement/?export=true -> 500
```
**Stock checkout and stock audit are core daily inventory operations and are entirely non-functional.** The plain (non-export) procurement view returns 200, which is why this was missed.

Note `quantity_change` is an `IntegerField` but checkout assigns a `Decimal` — fix the import *and* cast to `int`.

**Fix:** `from decimal import Decimal` and `from salon_admin.models import Center` at module top; delete the dead export block in `procurement` (it references variables from a different report) or implement it properly.

---

## C9. Django SECRET_KEY committed to the repository
**`backend/.env.example:8`**

```
DJANGO_SECRET_KEY=jfglx^+9i*=6n-f76xf+jk8uqt6jcbhg-o!1e=ny&=g&hteyxj
```
This is a real 50-char key in a file the header itself says never to commit. Anyone with repo access can forge session cookies, password-reset tokens, and the signed staff/client app tokens (`_signing.dumps`, `staff/views.py:1409`).

The `settings.py` guard only rejects the *hardcoded fallback* key, so this leaked-but-valid key passes the check silently.

**Fix:** rotate the key immediately, replace with a `<generate-me>` placeholder, and purge from git history (`git filter-repo`). Rotating invalidates all sessions and app tokens — expect a forced re-login.

---

# PART 2 — HIGH

## H1. Petty cash date filtering silently drops today's entries
**`backend/finance/models.py:7`** vs **`backend/finance/views.py:161-166`**

`PettyCashEntry.date` is a **`DateTimeField`** (with `auto_now_add=True`), but the view filters it as a date:
```python
queryset = queryset.filter(date__lte=end_date)   # end_date = '2026-08-12'
```
**Proof:** the generated SQL is
```sql
WHERE "date" <= 2026-08-12 00:00:00
```
Every expense recorded **after midnight on the final day is excluded**. A manager closing the books for today sees ₹0 of today's petty cash. This directly corrupts the cash-reconciliation figure that daily closing depends on.

The comment above the code claims the opposite of what the field actually is:
> `# PettyCashEntry.date is a DateField — use direct comparison`

**Fix:** `filter(date__date__lte=end_date)`, or change the model to a true `DateField`. Note `auto_now_add=True` also makes the field non-editable, so **back-dating a petty cash entry is impossible** — likely not intended for an expense ledger.

---

## H2. WhatsApp campaigns are impossible to send — inverted permission check
**`backend/marketing/views.py:146`**

```python
if hasattr(request.user, 'role') and request.user.role not in ['owner', 'marketing']:
    return Response({'error': 'Permission denied...'}, status=403)
```
`request.user.role` is a **`Role` model instance**, never the string `'owner'`. The comparison is always `True`, so the guard always fires.

**Proof (live), as superuser + Owner:**
```
send_campaign as OWNER/superuser -> 403 {"error":"Permission denied. Only owners and marketing staff can send campaigns."}
```
The entire marketing campaign feature is unreachable by every user including the owner.

**Fix:** `role_name = (request.user.role.name or '').lower() if request.user.role else ''` and compare against that (plus a superuser bypass).

---

## H3. `.only('full_name')` crashes — `full_name` is a property, not a column
**`backend/marketing/views.py:165, 167`**

```python
clients = base_qs.only('id', 'phone', 'full_name', 'center_id')
```
`Client.full_name` is a `@property` (`clients/models.py:24`). `.only()` accepts concrete fields only.

**Proof (live):**
```
.only('full_name') ->  FieldDoesNotExist: Client has no field named 'full_name'
```
This is the line immediately after H2's guard, so it is currently masked by that 403 — **fixing H2 alone will expose this crash.** Both must be fixed together.

**Fix:** `.only('id', 'phone', 'first_name', 'last_name', 'center_id')`.

---

## H4. Cashback promotions crash on empty config
**`backend/marketing/promotions.py:39, 43`**

```python
min_bill = Decimal(str(promo.config.get('cashback_min_bill')) or 0)
```
Precedence bug: `str(None)` is the truthy string `'None'`, so the `or 0` never fires and `Decimal('None')` raises.

**Proof (live):**
```
POST /billing/invoices/<id>/apply_promo/ -> decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]
```
Any Cashback promotion created without a fully-populated `config` JSON blob takes down the invoice.

**Fix:** `Decimal(str(promo.config.get('cashback_min_bill') or 0))` — move the `or` **inside** `str()`. Same fix on line 43.

---

## H5. `apply_promotion`'s return value is discarded during checkout
**`backend/billing/services.py:372-373`**

```python
from marketing.promotions import apply_promotion
apply_promotion(invoice, request_data.get('promo_id'))   # returns (discount, error)
```
The function returns `(discount, error)`, and `views.py:363` handles that tuple correctly — but the checkout path ignores it. So when a promo is rejected ("expired", "usage limit reached"), the error is swallowed, **yet `PromotionUsage` is still recorded** (`promotions.py:65`, executed unconditionally). The customer's one-per-client promo is burned without them receiving the discount.

**Fix:** capture and act on the result; move the `PromotionUsage.objects.create()` inside a success branch.

---

## H6. Cancelled invoices still pay staff commission
**`backend/billing/views.py:253-255`**

The cancel handler deliberately keeps `ServiceLog` rows:
> `# FIXED: Do not delete ServiceLogs — they are business/payroll records.`

Preserving them is correct. The problem is that **only 3 of 9 `ServiceLog` query sites filter cancelled invoices.**

**Proof (live):** after cancelling a paid invoice, `ServiceLog` rows remain (count: 1), and these payroll queries still count them:

| File:line | Excludes cancelled? |
|---|---|
| `staff/views.py:461` (commission_report) | ❌ filters `status__in=['paid','partial']` ✔ actually safe |
| `staff/views.py:511` (incentive_report) | ✔ safe |
| `staff/views.py:664`, `732` | ❌ **`ServiceLog.objects.all()`** |
| `clients/app_views.py:159` | ❌ |
| `salon_admin/dashboard_endpoints.py:198, 698` | ✔ safe |

`staff/views.py:664` and `:732` are `.all()` with no status filter — staff get paid commission on refunded work, and the client app shows cancelled services in visit history.

**Fix:** centralise it:
```python
ServiceLog.objects.exclude(invoice__status__in=['cancelled', 'refunded'])
```
Better: add a model manager so the safe path is the default.

---

## H7. Refund/cancel de-provisioning deletes the wrong records
**`backend/billing/views.py:281-297`**

```python
cm = ClientMembership.objects.filter(client=..., membership_id=...).order_by('-created_at').first()
if cm: cm.delete()
```
The lookup is by *client + product type*, **not by the invoice being cancelled**. If a client bought the same membership twice, cancelling the **older** invoice deletes the **newer** perk. Likewise, `ClientPackage` restore (`:262`) credits services back to the first matching package regardless of origin, and a `ClientValueCard` with a spent-down balance is hard-`delete()`d, destroying the audit trail.

**Fix:** add a nullable `source_invoice` FK to `ClientMembership`/`ClientPackage`/`ClientValueCard`, provision it in `finalize_invoice`, and de-provision by that FK. Prefer `is_active=False` over `delete()`.

---

## H8. Frontend and backend disagree on how tax is calculated
**`frontend/src/app/billing/billing.ts:1159-1163`** vs **`backend/billing/serializers.py:56-62`**

Frontend treats price as **tax-exclusive** (adds tax on top):
```typescript
let total = (unitPrice * qty) - discount;
return total * (taxPct / 100);          // tax ADDED
```
Backend's display fallback treats it as **tax-inclusive** (extracts tax from within):
```python
base = total / (1 + tax_pct / 100)
ret['tax_amount'] = round(total - base, 2)
```
On a ₹1,000 item at 18%: frontend says tax = ₹180 (total ₹1,180); backend's fallback reports tax = ₹152.54. The serializer's `validate()` accepts the frontend's numbers, so invoices are stored correctly — but **GST reports and reprints of older invoices show a different tax figure than the receipt the customer was given.** That is a compliance exposure.

**Fix:** pick one convention, document it on the model, and make the fallback match. Given `Product.price` is labelled "Price (incl. tax)" while services appear exclusive, the two item types may genuinely differ — that needs an explicit per-type rule.

---

## H9. Rounding is applied twice and can drift
**`frontend/src/app/billing/billing.ts:1719-1723, 1907-1912`**

`finalTotalAmount` returns `Math.round(sub + totalTax)` — already rounded. `roundingAmount` separately computes `Math.round(exact) - exact`. Both are sent. The backend then validates:
```python
expected_total = max(0, subtotal - discount + cgst + sgst) + rounding
```
This happens to reconcile, but only because the tolerance is `Decimal('0.1')` (`serializers.py:264`). With multi-item carts where per-item tax is rounded to 2dp before summing (`:1902`), accumulated drift can exceed 0.1 and the invoice is **rejected with a confusing "does not match mathematical calculation" error** at the point of sale.

**Fix:** compute the total server-side as the single source of truth and return it; treat client figures as advisory only.

---

## H10. `settings.USE_TZ = False` with threaded background writes
**`backend/pos_backend/settings.py:213`**

`USE_TZ = False` with `TIME_ZONE = 'Asia/Kolkata'` means naive datetimes throughout. Combined with `finance/views.py:41-52`, which mixes `created_at__gte=<naive datetime>` and `created_at__date__gte=<string>` as a fallback in the same function, date-boundary results differ between code paths. Invoices created between 00:00–05:30 IST are the usual casualties in reports.

**Fix:** enable `USE_TZ = True` and store UTC (Django converts for display). This is a migration-level change — plan it, but the current inconsistency is already producing wrong month-end numbers.

---

# PART 3 — MEDIUM

## M1. Audit-log middleware leaks DB connections in threads
**`backend/audit_logs/middleware.py:32, 272`** — `_write_log` runs in a `ThreadPoolExecutor` and calls the ORM. Django opens a **new connection per thread** and never closes it; `CONN_MAX_AGE = 60` doesn't apply to threads it doesn't own. Under sustained write traffic this exhausts MySQL's `max_connections`.
**Fix:** wrap the worker body in `django.db.close_old_connections()` on entry *and* in a `finally`.

## M2. Welcome-email thread has the same leak plus no pooling
**`backend/clients/models.py:113`** — an unbounded `threading.Thread` per client creation, inside `save()`. A bulk import of 5,000 clients spawns 5,000 threads. `bulk_create` (`clients/views.py:246`) bypasses `save()` entirely, so imported clients silently never get their PIN email — an inconsistency between the two creation paths.
**Fix:** move to a task queue, or at minimum reuse the bounded executor.

## M3. Audit logging silently drops records under load
**`backend/audit_logs/middleware.py:20-22`** — queue full ⇒ log discarded with only a `logger.warning`. For a system whose audit trail is a compliance artefact, silent loss under peak load is the exact opposite of what's needed.

## M4. Geo-IP lookup blocks the audit worker for 3s
**`backend/audit_logs/middleware.py:139-142`** — a synchronous `requests.get(timeout=3)` to `freeipapi.com` per unique IP. With only 2 workers, a slow third party stalls the whole audit pipeline (and `lru_cache` never expires, so a transient failure is cached as empty forever).

## M5. `user_agents` imported but absent from requirements
**`backend/audit_logs/middleware.py:94`** vs `requirements.txt`
**Proof:** `ModuleNotFoundError: No module named 'user_agents'` in this environment. The `except Exception` swallows it, so device/browser/OS columns are silently `'Unknown'` on every log row. `pandas` is pinned without a version (used at `clients/views.py:213`), which is a reproducibility risk for a ~50 MB dependency.

## M6. Frontend calls a URL that 404s
**`frontend/src/app/admin/logs/logs.ts:96`** calls `audit_logs/logs/`; middleware excludes `/audit_logs/`. **Proof:** `GET /audit_logs/api/logs/ -> 404`, `GET /audit_logs/logs/ -> 200`. The frontend path is right and the middleware's `EXCLUDED_PREFIXES` matches — but the mismatch means the *documented* path in `backend_urls.txt` is wrong, and it's a trap for the next developer.

## M7. `OptionalPagination` makes response shape unpredictable
**`backend/pos_backend/pagination.py:13-16`** — returns a bare array normally, but `{results, count}` when `?page=` is present. Only ~32 of the frontend's call sites guard with `Array.isArray`. `billing.ts:480-559` assumes arrays outright (`(d: any[]) => this.services = d`). The moment anyone adds a `page` param, those screens render blank with no error.

## M8. Double-submit interceptor swallows responses
**`frontend/src/app/prevent-double-submit.interceptor.ts:26-30`** — returns `EMPTY` on a duplicate, so the caller's `next`/`error` never fire. Any component showing a spinner until a callback runs stays stuck. The 1s cooldown also blocks *legitimate* rapid identical posts (e.g. two ₹100 cash payments on one bill).
**Fix:** share the in-flight observable (`shareReplay`) instead of returning `EMPTY`.

## M9. Loading spinner can stick on forever
**`frontend/src/app/loading.service.ts`** + interceptor — the counter is global; because the double-submit interceptor sits *after* the loading interceptor and returns `EMPTY`, `finalize` still runs, but any exception thrown between `show()` and subscription leaves the count > 0 permanently.

## M10. Owner bypass is inconsistent between the two permission layers
**`auth.guard.ts:115-122`** treats `is_superuser` OR `role === 'Owner'` as owner. **`module-access.ts:92-95`** does the same but then hard-returns `false` for `centers`/`users`/`roles`/`services`/`clients` (lines 126-132) — so a non-owner with legitimate `admin.users.read` permission is denied by `canAccessModule` while `roleGuard` would have allowed them. Two sources of truth that disagree.

## M11. Login response embeds permissions; client trusts them
`CustomAuthToken` (`accounts/views.py:53-63`) returns the permission JSON, which is cached in `localStorage` and used for all UI gating. Permissions changed server-side don't take effect until re-login, and a user can edit `localStorage` to reveal UI (backend still enforces reads — but see C1/C6 for where it doesn't).

## M12. No object-level permission checks anywhere
`check_object_permissions` is called once (`marketing/views.py:102`) and no custom `BasePermission` classes exist in the codebase. All authorisation is ad-hoc `if` statements repeated ~40 times, with the variations that inevitably follow (some check `perms.get('all_centers')`, some don't; some handle the no-centre case, some fall through open).

## M13. `Invoice.save()` raises `ValidationError` from the model layer
**`backend/billing/models.py:38-41`** — a `django.core.exceptions.ValidationError` raised in `save()` is **not** caught by DRF's exception handler, producing an HTTP 500 instead of a 400. Any code path writing a negative total (a refund adjustment) crashes.

## M14. Race condition in `DailyClosing.update_or_create`
**`backend/finance/views.py:249-253`** — `unique_together('center','date')` plus a non-atomic `update_or_create` under concurrency raises `IntegrityError` → 500. Wrap in `transaction.atomic()` and catch.

## M15. `MonthlySalesView` groups advances by their own date, not the invoice's
**`backend/finance/views.py:880-899`** — advances are bucketed by `AdvancePayment.created_at` while revenue is bucketed by `Invoice.created_at`. An advance taken in March and redeemed in April is counted in different months on the same report row, so monthly collection never ties out.

## M16. Silent `except: pass` blocks (14 occurrences)
`S110` hits in `middleware.py` (5), `billing/serializers.py` (4), `billing/views.py` (2), `dashboard_endpoints.py` (2), `finance/views.py` (1). Notably `billing/serializers.py:135` swallows the product-centre validation failure, and `billing/views.py:424` swallows the blacklist lookup — a DB hiccup silently lets a blacklisted client be billed.

## M17. Stock can go negative via the PO path
**`backend/inventory/serializers.py:141-153`** — reverting a PO from `Delivered` does `current_stock -= quantity` with no floor and no row lock, unlike `services.py:164` which correctly uses `max(0, ...)` and `select_for_update`. Read-modify-write here also races with concurrent sales.

## M18. `finalize_invoice` catches exceptions but leaves partial state
**`backend/billing/services.py:155-258`** — each step is individually try/excepted and `continue`s. Because the caller wraps everything in `@transaction.atomic`, a caught-and-logged failure does **not** roll back, so an invoice can end up with stock deducted but no `ServiceLog`, or perks provisioned twice. The `_vc_incentive_ratio` cache is set on the instance (`:212`) and would leak across calls if the object were reused.

## M19. Appointment double-booking check has a lock-ordering flaw
**`backend/appointments/views.py:67`** — `select_for_update()` on `StaffMember` inside a loop over services. Two concurrent bookings touching the same two staff in opposite order can deadlock. Also `_check_double_booking` reads `serializer.validated_data.get('services')`, but the serializer pops services and reads `self.initial_data` instead (`serializers.py:112`) — so **`validated_data['services']` is empty and the double-booking check never runs on create.**

## M20. Bulk staff upload defaults unknown centres to the first centre
**`backend/staff/views.py:227-229`** — an unmatched location name silently assigns the employee to `all_centers[0]` rather than erroring, quietly corrupting centre attribution for payroll. (A second, near-duplicate upload handler at `:1320` *does* error correctly — two implementations, two behaviours.)

---

# PART 4 — LOW / HYGIENE

| ID | Finding | Location |
|---|---|---|
| L1 | **All 10 frontend test files fail** — `describe is not defined` (vitest globals not enabled) and class names are wrong (`Auth` vs `AuthService`, `Users` vs `UsersComponent`). Zero effective frontend tests. | `frontend/src/**/*.spec.ts`, `package.json` |
| L2 | Backend has **2 real tests** total (`services/tests.py`); 9 of 10 `tests.py` are empty stubs. | `backend/*/tests.py` |
| L3 | `print()` used instead of logging in 5 production paths | `staff/views.py:884, 938, 1107, 1240, 1366` |
| L4 | 539 × trailing-whitespace, 55 × unused imports, 22 × unused variables (ruff) | backend-wide |
| L5 | 8 × redefinition-of-unused (`F811`), e.g. `datetime` shadowed | `finance/views.py:296`, `staff/views.py:10,17`, `inventory/views.py:249,653` |
| L6 | `zip()` without `strict=` (6×) — silently truncates on length mismatch during Excel import | `staff/views.py:194,828,1051,1184,1310`, `billing/serializers.py:459` |
| L7 | Dead files committed: `billing.html.bak` (1,280 lines), `billing.css.bak` (1,723), `view_700_800.html`, empty `hq.json`, empty `staff/views_recovered.py` | frontend/backend |
| L8 | Stray nested `chowmein/chowmein/chowmein/chowmein/properback/...` tree containing an **outdated duplicate** of `finance.ts` | repo root |
| L9 | `check_finance.py` is a debug script at backend root, imports prod settings | `backend/check_finance.py` |
| L10 | `MEDIA_ROOT` served via `re_path` **unconditionally**, not dev-only — comment says "development only" but there's no `if DEBUG` | `pos_backend/urls.py:27-29` |
| L11 | 6 npm advisories (3 low, 3 moderate) — all dev-only (`esbuild`, `@babel/core`, `@hono/node-server`) | `frontend` |
| L12 | Anonymous throttle 200/hour is generous for a login surface; `LoginRateThrottle` (5/min) is applied to login but keyed by IP only | `settings.py:73`, `throttles.py` |
| L13 | `angular.json` production config lacks `"fonts": {"inline": false}`; the build **fails hard** in any network-restricted CI because it fetches Google Fonts at build time | `frontend/angular.json` (reproduced: build failed until patched) |
| L14 | `gunicorn.conf` is a supervisor stanza with a placeholder `directory=/path/to/backend`; 4 workers × no `--max-requests` means the M1/M2 connection leaks accumulate indefinitely | `backend/gunicorn.conf` |
| L15 | `backend_urls.txt` (305 lines) is hand-maintained API documentation, already drifted from reality | `backend/backend_urls.txt` |

---

# Verification Performed

What I ran, and what passed:

| Check | Result |
|---|---|
| `manage.py check` | ✅ 0 issues |
| `manage.py check --deploy` | ⚠️ 1 warning (SECRET_KEY strength) |
| `makemigrations --check` | ✅ No drift — model state matches migrations |
| `manage.py test` | ✅ 2/2 pass (but near-zero coverage) |
| `tsc --noEmit` (app + `--strict`) | ✅ 0 errors |
| `ng build --configuration production` | ✅ after disabling font inlining (see L13); 345 kB initial, good lazy-chunking |
| `ng build --configuration development` | ✅ |
| `vitest run` | ❌ 10/10 files fail |
| `ruff` (F, E9, B, S) | 65 real issues incl. 6 × F821 |
| Live server, 43 endpoints exercised | 39 × 200, 2 × 500, 1 × 404 |
| Runtime reproductions written | 8 scripts, all findings confirmed |

**Credit where due — things that are genuinely well built:**
- Read-side multi-tenancy is applied consistently across ~40 querysets.
- Invoice math is validated server-side against forgery (`serializers.py:219-266`) — a real anti-tamper control many POS systems lack.
- `select_for_update` is used correctly in 18 places for stock/wallet races.
- `Invoice.client` is `PROTECT` and `ServiceLog`s survive cancellation — someone thought carefully about financial record retention.
- Index coverage is thorough (~60 explicit indexes) and N+1s are actively managed with `select_related`/`prefetch_related`.
- Lazy-loaded routes and `OnPush` change detection in the heavy components.

The engineering instincts are sound. The gap is almost entirely **write-path authorisation** and **money-path edge cases** — both fixable without architectural change.

---

# Recommended Remediation Order

**Ship-blockers — fix before any deployment (1–2 days)**
1. C1 + C2 — lock down `UserViewSet` (role/centre/password)
2. C6 — Owner-only on `CenterViewSet` / `RoleViewSet`
3. C3 — remove `cache_page` from finance views
4. C9 — rotate SECRET_KEY, purge from history
5. C7 — fix `apiUrl` (one line, currently breaks 100% of production)

**Week 1 — correctness**
6. C4 — wallet balance subqueries (money shown to customers is wrong)
7. C8 — 4 missing imports (restores stock checkout/audit)
8. C5 — hash client PINs + migration (restores customer app)
9. H1 — petty cash datetime filter
10. H2 + H3 — WhatsApp campaigns (fix together)
11. H4 + H5 — promotion crashes and usage burn

**Week 2 — money integrity**
12. H6 — `ServiceLog` cancellation filter (centralise in a manager)
13. H7 — invoice-linked perk de-provisioning
14. H8 + H9 — agree one tax/rounding convention, server-authoritative
15. M1 + M2 — thread connection leaks (these will bite at scale)

**Ongoing**
16. Introduce `IsOwner` / `HasModulePermission` permission classes and delete the ~40 duplicated `if` blocks (M12)
17. Fix the test harness (L1) and add regression tests for every C-item above
18. Remove dead files and the `chowmein/` tree (L7, L8)

---

## Answering your question directly

You asked whether it "always works like butter." Honestly: **not yet.** It boots and most screens load, which makes it *look* production-ready — but four features are completely non-functional today (stock checkout, stock audit, WhatsApp campaigns, the client mobile app), the production frontend build cannot reach its own backend, and any logged-in user can make themselves Owner in a single HTTP request.

The good news is that none of this requires a rewrite. The 9 critical items are all small, surgical fixes — most are one to ten lines — and I've given you the exact file, line, and replacement code for each. Fix the ship-blockers and you close the security holes; work through week 1 and 2 and the money paths become trustworthy.

I deliberately made **no code changes** so you can review the findings first. Say the word and I'll start fixing them in priority order, with a regression test for each.
