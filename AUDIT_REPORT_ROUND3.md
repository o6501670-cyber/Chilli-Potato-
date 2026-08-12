# Chilli Potato POS — Full Audit (Round 3)

**Date:** 12 August 2026
**Reviewing:** commit `d645660` — *"Refactor: Implement permission classes, fix bugs, frontend tests, and maintenance"*
**Baseline:** Round 2 report (`AUDIT_REPORT_ROUND2.md`)
**Method:** re-ran the complete Round 1 + Round 2 reproduction suite, swept all 54 endpoints live, then wrote new tests probing the refactored code paths

---

## Verdict

**This is the strongest commit of the three.** All 5 Round 2 regressions are fixed, permission classes are now real, the frontend test suite genuinely works, and `check --deploy` is clean for the first time.

```
########## SECURITY (Round 1 criticals) ##########
[PASS] C1 no self-promotion to Owner          [PASS] C4 advance balance = 200
[PASS] C2 cannot reset other's password       [PASS] C4 cashback balance = 30
[PASS] C6a non-owner create centre blocked    [PASS] C5 client PIN hashed
[PASS] C6b non-owner edit role perms blocked  [PASS] H2/H3 whatsapp campaign works
[PASS] C6c non-owner delete centre blocked
[FAIL] C3 register_summary endpoint alive  -> HTTP 500

########## ROUND 2 REGRESSIONS ##########
[PASS] N1 notes-only PATCH keeps total  -> 1180.00 preserved
[PASS] N3 expired promo -> 400 not 500
[PASS] N4 deleted centre hidden from list
[PASS] N5 aged-draft perk removed on cancel

PASSED 14/15
```

**Two things still block deployment**, both narrow and quick:

| # | Issue | Impact |
|---|---|---|
| **R1** | `compute_register_summary()` has 2 stray lines that crash it | **Register Summary — the main finance screen — is 100% down (500)**, plus multi-salon export |
| **R2** | `requirements.txt` still not ASCII (cp1252 em-dashes) | `pip install -r requirements.txt` **exits 2** — nothing can be provisioned |

Plus one genuine money bug found in the newly-refactored perk logic (**R3**, membership renewals).

---

# BLOCKERS

## R1 — 🔴 Register Summary returns HTTP 500 (new regression)
**`backend/finance/views.py:505-512`**

The refactor I recommended in Round 2 (extract the logic into a plain function) was done correctly — but two lines from the old request-based version were left in, and they overwrite the function's own parameters:

```python
def compute_register_summary(user, center_id, start_date, end_date) -> dict:
    class MockReq: pass
    req = MockReq()
    req.user = user
    request = req
    start_date = request.query_params.get('start_date')   # ← MockReq has no query_params
    end_date   = request.query_params.get('end_date')     # ← same
```

`MockReq` is a bare class with only `.user` set, so the very first statement raises.

**Proof (live server, 54-endpoint sweep):**
```
finance/api/register_summary/               500
finance/api/export_multi_salon/             500
finance/api/register_summary/?export=true   500
--- 51/54 returned 200; 3 failing
```
```
File "backend/finance/views.py", line 510, in compute_register_summary
    start_date = request.query_params.get('start_date')
AttributeError: 'MockReq' object has no attribute 'query_params'
```

**Fix — delete the two stray lines** (the parameters are already passed in):
```python
def compute_register_summary(user, center_id, start_date, end_date) -> dict:
    class MockReq: pass
    req = MockReq()
    req.user = user
    request = req
    # (delete the two query_params lines and the redundant `user = request.user`)
```

**I verified this fix works** — patched it temporarily, restarted, and all three endpoints returned 200 with correct date filtering, then reverted so the repo reflects your code:
```
finance/api/register_summary/                200
finance/api/export_multi_salon/              200
finance/api/register_summary/?export=true    200
narrow 2020 range -> collection: 0.0    (date filter applied correctly)
```

Note the `MockReq` shim only exists to satisfy `_get_filtered_invoices(request, ...)`, which reads `request.user`. Cleaner long-term: change that helper's signature to take `user` directly.

---

## R2 — 🔴 `pip install -r requirements.txt` still fails
**`backend/requirements.txt`**

The UTF-16 null bytes from Round 2 are gone — good — but the file still contains **6 cp1252 em-dash bytes (`0x97`)** that aren't valid UTF-8, so pip can't decode it at all.

**Proof:**
```
has null bytes? False          ← the UTF-16 issue was fixed
non-ascii byte count: 6  [(49,'0x97'), (426,'0x97'), (692,'0x97'), ...]

$ pip install --dry-run -r backend/requirements.txt
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97 in position 49
EXIT CODE: 2
```
Position 49 is in the comment `# FIXED: Django 6.x does not exist — latest LTS is 5.2` — the em-dash. They're all in comments, so the fix is cosmetic but mandatory.

**Fix:**
```bash
python -c "
d=open('backend/requirements.txt','rb').read().decode('cp1252')
open('backend/requirements.txt','w',encoding='utf-8',newline='\n').write(d)"
```
Then gate it in CI: `pip install --dry-run -r requirements.txt`. This has now broken twice in a row from Windows editor encoding — worth adding a pre-commit hook.

---

## R3 — 🟠 Membership renewals break refunds in both directions
**`backend/billing/services.py:26-42`** + **`backend/billing/views.py:288-300`**

The `source_invoice` FK (my N5 recommendation) was implemented properly — models, migration `0011`, provisioning and de-provisioning all use it. But the **renewal branch** extends an existing membership rather than creating a new row, and never updates `source_invoice`:

```python
if existing_cm and existing_cm.expiry_date >= datetime.date.today():
    existing_cm.expiry_date = existing_cm.expiry_date + timedelta(days=membership.expiry_days)
    existing_cm.save(update_fields=['expiry_date'])     # source_invoice NOT updated
else:
    ClientMembership.objects.create(..., source_invoice=invoice)
```

**Proof (live)** — customer buys the same membership twice (invoices 1 and 2):
```
purchase #1 -> expiry 2027-08-12 | source_invoice: 1
purchase #2 -> expiry 2028-08-11 | source_invoice: 1   ← still invoice 1

Refund the SECOND purchase (invoice 2):
  expiry after refund: 2028-08-11   ← unchanged
  >>> money returned, but the extra 365 days were NOT revoked

Refund the FIRST purchase (invoice 1):
  memberships remaining: 0
  >>> deletes the ENTIRE membership, including the still-paid-for second year
```

So a renewing customer either keeps a year they were refunded for, or loses a year they still paid for. Both directions are wrong, and renewals are the common case for memberships.

**Fix:** record renewals as their own rows so each purchase is independently reversible:
```python
ClientMembership.objects.create(
    client=invoice.client, membership=membership,
    start_date=max(existing_cm.expiry_date, today) if existing_cm else today,
    expiry_date=(existing_cm.expiry_date if existing_cm else today) + timedelta(days=membership.expiry_days),
    source_invoice=invoice,
)
```
and compute effective coverage as the max expiry across active rows. Alternatively keep the single-row model but store `days_added` per invoice so a cancel can subtract exactly that many days.

---

# What this commit got right

## Round 2 regressions — all 5 fixed ✅

| ID | Fix | Verified |
|---|---|---|
| **N1** | Total override wrapped in `if 'items' in data:` with `data.pop('total_amount')` on the else branch | Notes-only PATCH keeps `total=1180.00` |
| **N2** | UTF-16 nulls removed | …but see R2 — still not UTF-8 |
| **N3** | Raises `DRFValidationError({'promo_id': error})`, with a re-raise guard so it isn't swallowed | Expired promo → **HTTP 400**, not 500 |
| **N4** | `Center.is_active` field + migration `0009` + `qs.filter(is_active=True)` in `get_queryset` | Deleted centre disappears from the list |
| **N5** | `source_invoice` FK on all three perk models + migration `0011`, set on provisioning, used for de-provisioning (replaced the ±5min window) | Aged draft correctly de-provisions (see R3 for the renewal edge) |

## Permission classes — genuinely centralised ✅

`backend/pos_backend/permissions.py` now defines `IsOwner` with a reusable `check_is_owner()` static method, used across **9 modules** (`accounts`, `appointments`, `audit_logs`, `billing`, `clients`, `finance`, `inventory`, `marketing`, `salon_admin`, `services`, `staff`). The duplicated 4-line idiom is gone.

Verified still enforced:
```
POST   /accounts/api/users/        -> 403
DELETE /accounts/api/users/<id>/   -> 403
POST   /salon_admin/api/roles/     -> 403
DELETE /salon_admin/api/roles/<id>/-> 403
non-owner GET /audit_logs/logs/    -> 403      owner -> 200
```

*Minor:* `IsOwnerOrSelf` is defined but **never used anywhere** — dead code. Either wire it to `UserViewSet` (replacing the manual `serializer.instance.pk != user.pk` check) or drop it.

## Frontend tests — actually working now ✅

All 10 spec files were rewritten with correct class names (`AuthService`, `UsersComponent`, …) and proper providers (`provideHttpClient`, `provideHttpClientTesting`, `provideRouter`).

```
$ ng test --watch=false
✓ 10 passed (10 files) · 11 tests passed
```
*Note:* running bare `npx vitest run` still fails with `describe is not defined` — there's no standalone vitest config, and the Angular builder injects the globals. **Use `npm test` / `ng test`**; don't call vitest directly in CI.

## Backend tests doubled ✅
`Ran 4 tests ... OK` — new `billing/tests.py` (29 lines) and `salon_admin/tests_center.py` (39 lines) covering the invoice-total and centre-delete regressions. Exactly the right instinct: tests written for the bugs that shipped.

## Other confirmed fixes
- **`check --deploy` is fully clean** (was 1 warning) — secret key placeholder in place.
- **H8 tax convention** — `Product.price` relabelled *"Price (exclusive of tax)"*, so products and services now share one convention matching the frontend.
- **M16** — silent `except: pass` blocks down from 15 → **1**.
- **L3** — `print()` in production paths down from 5 → **1**.
- **L8** — the stray `chowmein/.../finance.ts` duplicate (555 lines) deleted.
- **M20 / dead code** — 381 more lines removed from `staff/views.py`.
- All Round 1 criticals (C1–C9 except C3's endpoint) and highs remain fixed; no `F821` undefined names anywhere.

---

# Still outstanding (unchanged, lower priority)

| ID | Item |
|---|---|
| **H10** | `USE_TZ = False` — naive datetimes; month-boundary reports still drift |
| **M3** | Audit logs silently dropped when the queue fills (`logger.warning` only) |
| **M7** | `OptionalPagination` still returns array-or-object depending on `?page=` |
| **M10/M11** | `auth.guard.ts` and `module-access.ts` still disagree on admin sub-modules; permissions cached in `localStorage` until re-login |
| **L7** | Dead files remain: `billing.css.bak`, `billing.html.bak`, `hq.json` (empty), `staff/views_recovered.py` (empty), `check_finance.py`, and the `chowmein/` directory tree |
| **L13** | `angular.json` has no `optimization.fonts.inline: false` — **the production build fetches Google Fonts over the network and hard-fails in an offline/restricted CI** (reproduced again this round) |
| **L14** | `gunicorn.conf` still has placeholder `directory=/path/to/backend`, no `--max-requests` |
| **L15** | `backend_urls.txt` still documents `audit_logs/api/logs/` (real path is `audit_logs/logs/`) |
| — | 40 ruff findings (`F841`/`F811`): 6 unused `role` variables left behind in `salon_admin/views.py` after the `IsOwner` refactor, plus shadowed `datetime` imports in `staff/views.py` |

---

# Verification Summary

| Check | Round 1 | Round 2 | **Round 3** |
|---|---|---|---|
| Critical exploits reproducible | 9 | 0 | **0** ✅ |
| `F821` runtime crashes | 6 | 0 | **0** ✅ |
| `manage.py check` | clean | clean | **clean** ✅ |
| `check --deploy` | 1 warning | 1 warning | **clean** ✅ |
| Migration drift | none | none | **none** ✅ |
| Endpoints returning 200 | 39/43 | 38/39 | **51/54** |
| `pip install -r requirements.txt` | ✅ | ❌ | **❌ (R2)** |
| Backend tests | 2 pass | 2 pass | **4 pass** ✅ |
| Frontend tests | 10 fail | 10 fail | **10 pass / 11 tests** ✅ |
| `tsc --noEmit` | clean | clean | **clean** ✅ |
| Angular build | ✅ | ✅ | **✅** |
| New defects introduced | — | 5 | **1 (R1)** + 1 latent (R3) |

Trajectory is clearly right: 9 criticals → 5 regressions → 1 regression, with test coverage appearing for the first time.

---

# Next actions

**Blockers — about 15 minutes total**
1. **R1** — delete the 2 stray `query_params` lines in `compute_register_summary`. Restores the finance dashboard and multi-salon export. *(Fix verified working.)*
2. **R2** — re-encode `requirements.txt` from cp1252 to UTF-8, and add `pip install --dry-run` to CI.

**Then**
3. **R3** — make membership renewals create their own row (or track `days_added` per invoice) so refunds are exact.
4. Wire up or delete `IsOwnerOrSelf`; clear the 6 unused `role` variables the refactor left in `salon_admin/views.py`.
5. Add `"fonts": {"inline": false}` to the production build config (L13) so CI builds don't depend on network access.
6. Delete the dead files and the `chowmein/` tree (L7).

---

## Bottom line

The security posture is solid and has held across three rounds — I re-ran every original exploit and none work. The permission-class refactor and the working test suite are exactly what I'd hoped to see, and the `source_invoice` FK was implemented properly rather than patched over.

The one thing to watch: **R1 is the same class of mistake as N1 last round** — a refactor that's correct in design but leaves stale lines behind, shipped without the endpoint being hit once. You now have a test suite; adding a smoke test that GETs each report endpoint and asserts 200 would have caught both R1 and Round 2's N-series before push. That's the highest-value thing to add next.

Want me to apply R1, R2 and R3 and push them?
