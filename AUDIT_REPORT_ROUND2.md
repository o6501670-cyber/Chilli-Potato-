# Chilli Potato POS — Re-Audit (Round 2)

**Date:** 12 August 2026
**Reviewing:** commit `372fcd1` — *"Fix audit report issues M1-M20 and Phase 4/5 user bugs"*
**Baseline:** my Round 1 report (`AUDIT_REPORT.md`) against `f9f8c30`
**Method:** re-ran every Round 1 reproduction script, then wrote new tests specifically hunting for regressions introduced by the fixes

---

## Verdict

**Great progress — all 9 critical issues are genuinely fixed.** I re-ran my original exploit scripts and every one now fails to exploit:

```
[PASS] C1 self-promotion to Owner blocked      -> role stays Receptionist
[PASS] C2 cannot change other's password
[PASS] C6a non-owner cannot create centre      -> HTTP 403
[PASS] C6b non-owner cannot edit role perms    -> HTTP 403
[PASS] C6c non-owner cannot delete centre      -> HTTP 403
[PASS] C4 advance balance correct (200)        -> got 200.0  (was 600)
[PASS] C4 cashback balance correct (30)        -> got 30.0   (was 60)
[PASS] C5 auto PIN is hashed at rest           -> pbkdf2_sha256$1000000$...
[PASS] C3 no cross-tenant cache leak           -> A=1000.0  B=7.0  (correctly differ)
[PASS] H2/H3 campaign sends as owner           -> HTTP 200 "Campaign sent to 3 clients"
PASSED 10 / 10
```

Plus: all 6 `F821` undefined-name crashes are gone, `manage.py check` is clean, no migration drift, `tsc` passes, the Angular build succeeds, and **38 of 39 endpoints return 200**.

**However, the fix pass introduced 5 new defects — 2 of them serious.** Two are data-destroying, one blocks deployment entirely, and one blocks sales at the till. All are small fixes. Details below.

---

# NEW ISSUES INTRODUCED BY THIS COMMIT

## N1 — 🔴 CRITICAL: A notes-only edit wipes the invoice total to ₹0
**`backend/billing/serializers.py:257-263`**

The C-fix made the server authoritative over invoice math — correct in principle, but it runs on **every** update including partial ones:

```python
expected_total_raw = max(Decimal('0'), expected_subtotal - discount + cgst + sgst)
expected_total_rounded = Decimal(str(round(float(expected_total_raw))))
data['rounding'] = expected_total_rounded - expected_total_raw
data['total_amount'] = expected_total_rounded
```

`expected_subtotal` is computed by looping `data.get('items', [])`. On a PATCH that doesn't include `items`, that loop runs zero times, so `expected_subtotal = 0` → **`total_amount` is overwritten with 0**.

**Proof (live):**
```
create paid invoice        -> HTTP 201, total_amount 1180.00  ✔
PATCH {"notes":"just a note"} -> HTTP 200
total_amount in DB after PATCH: 0.00      <-- was 1180.00
subtotal: 1000.00  |  status: paid
```
A ₹1,180 paid invoice silently becomes ₹0 while still marked `paid`, with its subtotal intact — so revenue reports, GST returns and daily closing all under-report. Any workflow that PATCHes an invoice without resending the full item list destroys the amount.

Round 1's validation (which *rejected* mismatches) would have caught this; replacing rejection with silent overwrite removed the safety net.

**Fix:** only recompute when items are actually supplied.
```python
if 'items' in data:
    ...compute and override total_amount / rounding...
else:
    data.pop('total_amount', None)   # never derive a total from absent items
    data.pop('rounding', None)
```
Also worth restoring a sanity check: if a computed total differs wildly from the stored one on a full update, reject rather than overwrite.

---

## N2 — 🔴 CRITICAL: `pip install -r requirements.txt` now fails
**`backend/requirements.txt`**

`user-agents` was correctly identified as missing (my M5) — but it was appended in **UTF-16LE** to an ASCII file, so every character is followed by a null byte.

**Proof:**
```
last line raw: b'as\r\nu\x00s\x00e\x00r\x00-\x00a\x00g\x00e\x00n\x00t\x00s\x00\r\x00\n\x00'

$ pip install -r requirements.txt
ERROR: Invalid requirement: 'u\x00s\x00e\x00r\x00-\x00a\x00g\x00e\x00n\x00t\x00s\x00'
       (from line 43 of requirements.txt)
```
The file is unparseable — **no server can be provisioned from this repo**. This is almost certainly PowerShell `Add-Content`/`>>` on Windows, which defaults to UTF-16.

**Fix:** rewrite the file as UTF-8/ASCII and append the dependency properly:
```bash
python -c "
d=open('requirements.txt','rb').read().decode('utf-8',errors='ignore').replace('\x00','')
open('requirements.txt','w',newline='\n').write(d)"
```
Verify with `pip install --dry-run -r requirements.txt` in CI so this can't recur.

---

## N3 — 🟠 HIGH: An expired promo now returns HTTP 500 and blocks the sale
**`backend/billing/services.py:376-382`**

My H5 said the discarded return value should be acted on. It now is — but by raising a bare `ValueError` inside `finalize_invoice`, which sits inside `@transaction.atomic` in `create()`. Nothing converts it to a 400.

**Proof (live):**
```
create invoice with an expired promo -> HTTP 500
invoices saved: 0   -> the entire sale is rolled back
```
```
File "billing/services.py", line 379, in finalize_invoice
    raise ValueError(f"Promotion Error: {error}")
ValueError: Promotion Error: Promotion has expired
```
At the counter this means: customer presents a lapsed coupon → the whole bill fails with an opaque "Server Error" toast, and staff cannot complete the sale at all. Previously the promo was silently ignored and the sale went through (wrong, but not blocking).

The same pattern was added in 5 other places (`raise` after `logger.error` at lines 180, 259, 347, 371, 382). Those help atomicity — my M18 asked for exactly that — but **the exception type matters**: any non-DRF exception becomes a 500.

**Fix:** raise a DRF-aware error so it renders as a clean 400:
```python
from rest_framework.exceptions import ValidationError as DRFValidationError
if error:
    raise DRFValidationError({'promo_id': error})
```
Better still, validate the promo in `InvoiceSerializer.validate()` *before* any money moves, so the user is warned before checkout.

---

## N4 — 🟠 HIGH: Centre "soft delete" writes to a field that doesn't exist
**`backend/salon_admin/views.py:64-73`**

```python
instance.is_active = False
instance.save()
```
`Center` has **no `is_active` field** — I enumerated every field on the model to confirm. Django lets you set an arbitrary attribute on an instance, and `save()` silently ignores it. So the delete is a no-op that reports success.

**Proof (live):**
```
DELETE /salon_admin/api/centers/<id>/  -> HTTP 204   (success)
centre still in DB?                    -> True
Center model has is_active field?      -> False
list API afterwards: ['Live', 'DeletedCentre']   <-- still listed
```
The owner clicks Delete, gets a success response, and the centre stays in every dropdown. Confusing, but note the **upside**: this accidentally prevents the catastrophic cascade I flagged in C6 (which would have wiped products, staff, appointments and service logs). So the current behaviour is safe-but-broken rather than dangerous.

**Fix:** add the field and a migration, then filter it out of `get_queryset()`:
```python
# models.py
is_active = models.BooleanField(default=True)
# views.py get_queryset()
qs = qs.filter(is_active=True)
```
Without the queryset filter the soft delete still won't appear to work.

---

## N5 — 🟡 MEDIUM: The ±5-minute de-provisioning window misses held drafts
**`backend/billing/views.py:287-289`**

My H7 (perks de-provisioned by client+product instead of by invoice) was addressed with a time window:
```python
window_start = invoice.created_at - timedelta(minutes=5)
window_end   = invoice.created_at + timedelta(minutes=5)
```
Perks are provisioned when the invoice is **paid**, but the window is anchored to when it was **created**. A draft held longer than 5 minutes — the normal "start a tab, pay on the way out" flow — falls outside its own window.

**Proof (live):** membership draft created 2 h before payment, then cancelled:
```
pay draft -> 200 | memberships provisioned: 1
cancel    -> 200 | memberships remaining:   1   (should be 0)
>>> client keeps a membership they were refunded for
```
It also still mis-targets when the same perk is bought twice inside 5 minutes.

**Fix:** as originally recommended, add a nullable `source_invoice` FK to `ClientMembership` / `ClientPackage` / `ClientValueCard`, set it during provisioning, and de-provision by that FK. A timestamp window can't be made reliable here.

---

# Round 1 items — current status

## ✅ Properly fixed (verified)

| ID | Fix quality |
|---|---|
| **C1/C2** | `perform_create/update/destroy` added; non-owners lose `role`/`center`/`centers` and can only edit themselves. `password` removed from generic update. Solid. |
| **C3** | `cache_page` removed from all 3 finance views. Verified two tenants now get different data. |
| **C4** | Cartesian annotations deleted; serializer falls back to the correct model property. Exact values confirmed. |
| **C5** | PIN hashed via `make_password`, column widened to 128 with migration `0010`, raw PIN emailed, plaintext-login fallback added for legacy rows. Complete and well done. |
| **C6** | Owner-only guards on both `CenterViewSet` and `RoleViewSet` (see N4 for the delete detail). |
| **C7** | `apiUrl: ''` → resolves to `https://salon.example.com/accounts/api/login/`. Correct. |
| **C8** | All 6 `F821` gone; `Decimal` and `Center` imported; procurement export rewritten against real data. Stock checkout/audit confirmed working. |
| **C9** | Key replaced with `<generate-a-new-secret-key-here>`; **history is clean** (new repo has no trace of the old key). Still rotate the live key if it was ever deployed. |
| **H1** | `date__date__gte/lte` — today's petty cash now included. |
| **H2/H3** | Role-name comparison fixed with superuser bypass; `.only()` uses `first_name`/`last_name`. Verified sending. |
| **H4** | `or 0` moved inside `str()`. |
| **H6** | `SafeServiceLogManager` is a **very clean fix** — I stress-tested it: cancelled logs hidden from `.objects`, visible via `.all_objects`, NULL-invoice logs still visible, related-name counts correct, and cascade deletes leave no orphans. |
| **M1** | `close_old_connections()` on entry and in `finally`; pool raised to 4 workers / 10k queue. |
| **M2** | Bounded 5-worker `ThreadPoolExecutor` replaces unbounded threads, with connection cleanup. |
| **M4** | Geo timeout 3s → 1s. |
| **M8** | `shareReplay(1)` + Map — duplicate POSTs now share the response instead of getting `EMPTY`. Correct fix. |
| **M13** | Django `ValidationError` translated to DRF `ValidationError` in create and update. |
| **M14** | `update_or_create` wrapped in `atomic` with `IntegrityError` retry. |
| **M15** | Advances bucketed by `Coalesce('invoice__created_at','created_at')` — advances now align with the invoice month. |
| **M17** | PO reversal uses `select_for_update` + `max(0, ...)`. |
| **M19** | Deadlock avoided by sorting services by staff id; **and the real bug fixed** — `initial_data` instead of `validated_data`, so double-booking detection actually runs now. |
| **M20** | The duplicate 349-line staff bulk-upload handler was deleted. |
| Export bugs | Round 1 noted several export loops reading keys the rows don't have (`month_name`, `total_sales`, `tax`, `payment_methods`). All corrected to real keys. |

## ⚠️ Still outstanding

| ID | Status |
|---|---|
| **export_multi_salon still 500s** | See N6 below — new root cause, not the old one |
| **H8** (tax convention) | Backend fallback changed to `total * pct/100`, now matching the frontend's tax-exclusive model. Consistent — but `Product.price` is still labelled *"Price (incl. tax)"*, so products and services likely still disagree. Needs an explicit per-type rule. |
| **H9** | Superseded by the server-authoritative math, but that introduced N1. |
| **H10** | `USE_TZ = False` unchanged. |
| **M3** | Audit logs still silently dropped when the queue fills (larger queue now, same behaviour). |
| **M5** | Dependency added but file corrupted — see N2. |
| **M6** | Frontend still calls `audit_logs/logs/` (works, returns 200); `backend_urls.txt` still documents the wrong path. |
| **M7, M9, M10, M11** | Unchanged. |
| **M12** | Still **zero** `BasePermission` classes — authorisation is now duplicated in ~55 hand-written blocks (up from ~40, since each new guard repeats the same 4 lines). This is the main maintainability debt: the `is_owner` idiom is copy-pasted 12 times in `salon_admin/views.py` and `accounts/views.py` alone. |
| **M16** | 15 silent `except: pass` blocks remain. |
| **M18** | Improved via the new `raise` statements, but see N3 for the exception-type problem. |
| **L1** | **All 10 frontend test files still fail** (`describe is not defined`; `Auth` vs `AuthService`, `Users` vs `UsersComponent`). Zero frontend test coverage — which is exactly why N1 and N4 shipped unnoticed. |
| **L2** | Backend still has 2 real tests. |
| **L3–L15** | Unchanged: `print()` statements, dead `.bak` files, the `chowmein/` tree, `angular.json` font inlining, placeholder `gunicorn.conf`. |

## N6 — `export_multi_salon` still returns 500 (new cause)

The missing `Center` import was fixed, but the endpoint fails one line later:

**Proof (live):** `AttributeError: 'NoneType' object has no attribute 'role'`

```python
django_req = HttpRequest()
django_req.user = request.user
drf_req = Request(django_req)        # <-- DRF re-authenticates
res = view_instance.get(drf_req)
```
DRF's `Request.user` is a **property** that re-runs authentication against the wrapped request. The synthetic `HttpRequest` carries no auth headers, and `settings.REST_FRAMEWORK['UNAUTHENTICATED_USER'] = None`, so `drf_req.user` is `None` → `_get_filtered_invoices()` hits `user.role` → 500.

**Fix:** stop faking HTTP requests. Extract the computation:
```python
def compute_register_summary(user, center_id, start_date, end_date) -> dict: ...
```
and call it directly from both `RegisterSummaryView.get()` and the multi-salon export. As a stopgap: `Request(django_req, authenticators=request.authenticators)` then force `drf_req.user = request.user`.

---

# Verification Summary

| Check | Round 1 | Round 2 |
|---|---|---|
| Critical exploits reproducible | 9 | **0** ✅ |
| `F821` runtime crashes | 6 | **0** ✅ |
| `manage.py check` | clean | clean ✅ |
| Migration drift | none | none ✅ |
| `tsc --noEmit` | clean | clean ✅ |
| Angular build | ✅ | ✅ |
| Endpoints returning 200 | 39/43 | **38/39** |
| `pip install -r requirements.txt` | ✅ | ❌ **fails (N2)** |
| Frontend tests | 10/10 fail | 10/10 fail |
| New defects introduced | — | **5** |

---

# Recommended next actions

**Blockers (roughly an hour's work total)**
1. **N2** — re-encode `requirements.txt` as UTF-8. Nothing deploys until this is done.
2. **N1** — guard the total override behind `if 'items' in data`. This is silently zeroing revenue.
3. **N3** — raise DRF `ValidationError` instead of `ValueError` so expired promos give a 400, not a blocked sale.

**Next**
4. **N4** — add `Center.is_active` + migration + queryset filter (or revert to hard delete with a confirmation).
5. **N6** — refactor `RegisterSummaryView` into a callable function; fixes the last 500.
6. **N5** — `source_invoice` FK for perk de-provisioning.

**Then — and I'd push for this one**
7. **L1 / M12.** Fix the vitest config (`globals: true` + correct class names) and introduce two permission classes (`IsOwner`, `IsOwnerOrSelf`) to replace the ~55 duplicated blocks.

That last point is worth emphasising. N1 and N4 are exactly the kind of bug a single test would have caught — "editing an invoice's notes must not change its total", "deleting a centre must remove it from the list". The security fixes in this commit are genuinely good work, but the codebase currently has no safety net to keep them working. Getting the test harness running is now the highest-leverage thing you can do.

---

## Bottom line

You closed every critical hole I found — the privilege escalation, the cross-tenant leak, the wallet inflation and the broken client login are all properly dead, and I verified that by re-running the original exploits. The `SafeServiceLogManager` and the appointment `initial_data` fix in particular were done better than I suggested.

The trade-off is that 5 new defects came in with the fix pass, two of which (₹0 invoices, unparseable requirements) are worse in isolation than some of what was fixed. That's normal for a change of this size against a codebase with no tests — and all five are quick fixes.

Want me to fix N1–N6 now and get the test harness running so the next round can be verified automatically?
