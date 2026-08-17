# Full-stack QA and load-test report

**Date:** 2026-08-17  
**Scope:** Angular frontend, Django/DRF backend, database migrations, authentication/authorization, billing and inventory transaction integrity, dependency security, production configuration, and representative API load.

## Result summary

| Check | Result |
|---|---:|
| Django regression tests | 41 passed |
| Angular/Vitest tests | 18 passed |
| Angular production build | Passed (424 kB initial raw / 110 kB estimated transfer) |
| Django system + migration drift checks | Passed; no model drift |
| Django deploy check + collectstatic | Passed |
| Python Ruff correctness scan | Passed |
| Bandit medium/high security scan | Passed |
| `pip-audit` | 0 known vulnerabilities |
| `npm audit` | 0 known vulnerabilities |
| Exact-count API load run | 15,000 / 15,000 HTTP 200; 0 failures |

## Load test

The final deterministic run used `backend/load_test.py` against Gunicorn's production-style `gthread` configuration:

- **Total requests:** 15,000
- **Concurrent clients:** 300
- **Endpoints:** 9 authenticated operational endpoints, round-robin
- **Dedicated tokens:** 4
- **Failures/network errors:** 0
- **Throughput:** 132.78 requests/second
- **Latency:** p50 2,280.64 ms; p95 3,633.03 ms; p99 4,804.64 ms; max 5,771.47 ms
- **Server:** 4 Gunicorn workers × 8 threads
- **Test database:** local SQLite fixture with 100 clients and 50 products
- **Audit writes:** disabled for this read-throughput run

Endpoint counts were split almost evenly (1,666–1,667 each) across centers, staff, inventory, billing, appointments, paginated clients, services, marketing, and finance register summary. Every response was HTTP 200.

This validates an exact 15,000-request burst at concurrency 300 in the sandbox. It does **not** claim 15,000 simultaneous open users or establish production capacity. A final capacity/SLA test must run against the real MySQL + Redis + reverse-proxy topology, with production-sized data and audit logging enabled. The local p95 also shows that database and hardware sizing matter. The client list's per-row balance-query bottleneck was removed after profiling by using correlated aggregate subqueries.

### Reproduce safely

The deterministic runner rejects remote targets unless `--allow-remote` is explicitly supplied:

```bash
cd backend
export LOAD_TEST_TOKENS=token1,token2,token3,token4
.venv/bin/python load_test.py \
  --url http://127.0.0.1:8000 \
  --requests 15000 \
  --concurrency 300 \
  --json-output load-report.json
```

A sustained, non-destructive Locust profile is also provided in `backend/locustfile.py`.

## Important defects fixed

### Financial and inventory integrity

- Made invoice payment, wallet/cashback/value-card debit, and finalization one atomic operation.
- Rejected overpayment, invalid methods, cross-client value cards, and insufficient balances.
- Corrected cashback handling that previously followed advance-wallet logic.
- Ensured finalization failures roll the entire payment back.
- Fixed payroll-lock checks referencing a nonexistent invoice date field.
- Prevented draft cancellation from adding inventory that was never deducted.
- Corrected partial refunds to record the amount actually paid, not the full invoice total.
- Prevented unsafe relabeling of wallet/value-card payments.
- Made checkout/audit batches validate fully before any stock mutation.
- Rejected negative/duplicate stock operations and cross-center product operations.
- Fixed purchase-order tax calculation to apply tax after discount and made PO writes atomic.
- Fixed product-lot center filtering and cross-center bulk import/update access.

### Authentication, authorization, and privacy

- Enabled expiring API-token authentication and token rotation on login.
- Closed chat-room read/send/mark-read authorization gaps.
- Required and validated passwords when creating users.
- Removed app tokens from query strings to avoid URL/history/log leakage.
- Added staff-app login throttling.
- Hashed client PINs and staff app PINs on every write and made them write-only.
- Expanded staff password storage to safely hold Django password hashes.
- Handled duplicate client/staff identifiers without server errors.
- Closed cross-center service creation, update, override, and bulk-upload paths.
- Recursively redacted nested audit secrets and bounded audit payload size.
- Added audit success/HTTP-status fields and raised burst queue capacity above 15k.
- Made forwarded-IP trust and external geolocation explicit opt-ins.

### Frontend and deployment

- Removed vulnerable SheetJS/xlsx usage; exports now use formula-safe CSV.
- Updated Angular/tooling packages and added local Font Awesome assets.
- Fixed offline production builds by removing Google Fonts build/runtime dependencies.
- Switched browser API calls to same-origin URLs and added an Angular dev proxy.
- Fixed POST de-duplication for FormData/circular bodies and removed stale-response reuse.
- Fixed a multi-salon center-name indexing error.
- Added production Gunicorn worker/thread/recycling configuration.
- Added `DATABASE_URL` support for CI/containers while retaining MySQL as the default.
- Disabled Django media serving in production.
- Added request/upload limits and hardened environment parsing.

## Deployment requirements

Before release:

1. Apply both new migrations:
   - `audit_logs.0006_systemlog_response_status_systemlog_success`
   - `staff.0020_alter_staffmember_app_password`
2. Configure a strong `DJANGO_SECRET_KEY`, explicit hosts/origins, MySQL, and Redis.
3. Set `POS_BACKEND_DIR` for the provided Supervisor configuration.
4. Run a staging load test on production-sized MySQL data with audit logging enabled.
5. Put a reverse proxy/load balancer in front of Gunicorn and tune workers, DB pool limits, timeouts, and autoscaling from observed staging metrics.

No finite test can mathematically guarantee that no defect exists. The repository now passes all checks listed above, and regression coverage was added for every critical issue fixed in this pass.
