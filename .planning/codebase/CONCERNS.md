# Codebase Concerns

**Analysis Date:** 2026-04-16

## Tech Debt

**Single-File Architecture (1,122 lines):**
- Issue: All business logic, routing, authentication, database access, Excel generation, holiday calculation, and vendor matching live in one file
- Files: `app.py`
- Impact: Difficult to navigate, test in isolation, or assign work to multiple developers. Any change risks unintended side effects across unrelated features. The `index()` function alone (lines 215-327) handles query execution, vendor deduplication, keyword matching, and total aggregation in ~110 lines.
- Fix approach: Extract into modules: `routes/`, `services/`, `db.py`. Start by pulling out `export` logic (lines 882-1041), vendor matching (lines 287-311), and holiday calculation (lines 18-91) into separate files.

**Hardcoded Taiwan Holidays (2026-2027 only):**
- Issue: `TW_HOLIDAYS_2026` and `TW_HOLIDAYS_2027` are hardcoded sets that expire at end of 2027
- Files: `app.py` lines 18-63
- Impact: `default_remit_date()` will produce incorrect results starting 2028-01-01 by treating all holidays as business days
- Fix approach: Move holidays to a database table (`tw_holidays`) with an admin UI for yearly maintenance, or load from an external JSON file that can be updated without code changes.

**No Database Migration Framework:**
- Issue: Migrations are ad-hoc Python scripts (`migrate_v2.py`, `migrate_v3.py`, `migrate_v4.py`) with no version tracking, rollback capability, or idempotency guarantees beyond `IF NOT EXISTS`
- Files: `migrate_v2.py`, `migrate_v3.py`, `migrate_v4.py`
- Impact: No way to verify which migrations have run on a given environment. Manual execution risk. No rollback path if a migration fails partway.
- Fix approach: Adopt Alembic (SQLAlchemy migration tool) or a lightweight alternative. Even a simple `schema_version` table would help.

**Tuple-Index Access for Query Results:**
- Issue: All database rows are accessed by positional index (e.g., `r[0]`, `r[3]`, `r[16]`) rather than named columns or dictionaries
- Files: `app.py` (throughout all route handlers), `templates/list.html` (references like `r[12]`, `r[16]`)
- Impact: Extremely fragile. Adding or reordering a column in a SELECT statement silently breaks every template reference. The `reports` query returns 17 columns — one miscount breaks the entire list page.
- Fix approach: Use `psycopg2.extras.RealDictCursor` or `NamedTupleCursor` so rows are accessed as `r['vendor']` or `r.vendor`. Update templates accordingly.

**Inline `from collections import defaultdict` Import:**
- Issue: `defaultdict` is imported inside the `index()` function body (line 261) instead of at the top of the file
- Files: `app.py` line 261
- Impact: Minor style issue, but indicates rushed development. Inconsistent with all other imports at file top.
- Fix approach: Move to top-level imports.

**No Soft Delete for Reports:**
- Issue: `DELETE FROM reports` is a hard delete with no audit trail
- Files: `app.py` lines 457, and the absence of any `deleted_at` or audit log
- Impact: Accidental deletions are unrecoverable. No way to audit who deleted what or when.
- Fix approach: Add `deleted_at TIMESTAMP` column and filter queries with `WHERE deleted_at IS NULL`, or implement an `audit_log` table.

**Vendor Name Join is Fragile:**
- Issue: Reports link to vendors by `r.vendor = v.name` (string match) rather than a foreign key
- Files: `app.py` lines 896, 906 (export queries), line 274 (vendor bank info lookup)
- Impact: Renaming a vendor in the `vendors` table breaks the link to all existing reports. No referential integrity enforced.
- Fix approach: Add `vendor_id` foreign key to `reports` table. Requires migration and data backfill.

## Known Bugs

**CSRF Error Handler Catches All 400 Errors:**
- Symptoms: Any HTTP 400 error that contains the string "CSRF" in its message is caught and rendered as "操作逾時". Other 400 errors that happen to contain that string are mishandled.
- Files: `app.py` lines 153-157
- Trigger: Any non-CSRF 400 error whose string representation contains "CSRF"
- Workaround: None currently. The TODO documents acknowledge this as P0 #3.
- Fix: Import `CSRFError` from `flask_wtf.csrf` and use `@app.errorhandler(CSRFError)` instead of `@app.errorhandler(400)`.

**Admin Can Toggle Their Own Account:**
- Symptoms: An admin can disable their own account via `/users/<uid>/toggle`, locking themselves out
- Files: `app.py` lines 1092-1101
- Trigger: Admin clicks "停用" on their own row (the template hides the button for `u[0] == user.id` at `templates/users.html` line 63, but there is no server-side check)
- Workaround: The UI hides the button, but a crafted POST request bypasses this.
- Fix: Add server-side check: `if uid == user['id']: abort(403)`.

**Update Report Silently Redirects on Validation Failure:**
- Symptoms: When admin inline-edit fails validation (missing vendor, bad amount), the user is silently redirected to `/` with no error message
- Files: `app.py` lines 528-544
- Trigger: Submit an inline edit with empty vendor or negative amount
- Workaround: None — user has no idea what went wrong.
- Fix: Return error feedback via query parameter or flash message.

## Security Considerations

**No Login Rate Limiting:**
- Risk: Brute force password attacks are unrestricted. An attacker can try unlimited username/password combinations.
- Files: `app.py` lines 178-203
- Current mitigation: None
- Recommendations: Implement `flask-limiter` with a persistent backend (Neon DB counter or Upstash Redis). Set limit to 5 attempts per minute per IP on `POST /login`. Consider account lockout after N failures.

**No Password Complexity Requirements:**
- Risk: Users and admins can set single-character passwords. Default test credentials (`dawn1234`, `test1234`) are weak.
- Files: `app.py` lines 1063-1089 (user create), lines 1104-1117 (password reset)
- Current mitigation: None
- Recommendations: Enforce minimum 8 characters, mix of letters and numbers. Add validation in `user_create()` and `user_reset_password()`.

**Default Admin Credentials in Documentation:**
- Risk: The HANDOFF document (committed to git) contains plaintext credentials: `dawn / dawn1234` and `designer_a / test1234`
- Files: `HANDOFF20260415night.md` line 13-14
- Current mitigation: None — anyone with repo access can log in
- Recommendations: Rotate credentials immediately. Remove plaintext credentials from committed documentation.

**Hardcoded Admin Password in Migration Script:**
- Risk: `migrate_v2.py` line 32 contains `generate_password_hash('admin123')` — a different default password than what the HANDOFF doc states, suggesting the password was changed manually but the script retains a weak default
- Files: `migrate_v2.py` line 32
- Current mitigation: Script is meant to run once
- Recommendations: Use environment variable for initial admin password, or prompt interactively.

**No File Upload Size Limit:**
- Risk: The vendor import endpoint (`/vendors/import`) accepts arbitrarily large files. A malicious user could upload a multi-GB file to exhaust server memory.
- Files: `app.py` lines 775-853
- Current mitigation: None
- Recommendations: Set `app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024` (2 MB). Validate MIME type server-side. Limit DataFrame row count after parsing.

**Vendor Bank Data Visible to All Authenticated Users:**
- Risk: Any logged-in user (including designers) can view all vendor bank account numbers via `/vendors` page and `/api/vendor-bank` API endpoint. Bank account information is sensitive financial data.
- Files: `app.py` lines 654-683 (vendor_list), lines 856-876 (vendor_bank API)
- Current mitigation: Login required, but no role-based restriction
- Recommendations: Consider restricting full bank details to admin role only. Designers may only need partial info (last 4 digits).

**Logout via GET Request:**
- Risk: CSRF-style attacks can log users out by embedding `<img src="/logout">` in any page. While low severity, it violates REST conventions.
- Files: `app.py` lines 206-209
- Current mitigation: SameSite=Lax cookies mitigate cross-origin, but same-site pages can still trigger it
- Recommendations: Change logout to POST with CSRF token.

**No Session Invalidation on Password Change:**
- Risk: When an admin resets a user's password, the user's existing sessions remain valid indefinitely (up to 7 days)
- Files: `app.py` lines 1104-1117
- Current mitigation: None — Flask client-side sessions cannot be server-side invalidated
- Recommendations: Add a `session_version` column to users table. Increment on password change. Check in `get_current_user()`.

## Performance Bottlenecks

**No Database Indexes on Reports Table:**
- Problem: The `reports` table has only a primary key index. All queries filter/sort by `user_id`, `project_no`, `invoice_no`, and `invoice_date` without index support.
- Files: `app.py` lines 222-244 (list queries), line 399 (invoice duplicate check)
- Cause: Indexes were never created during migration
- Improvement path: Add indexes immediately:
  ```sql
  CREATE INDEX idx_reports_user_id ON reports(user_id);
  CREATE INDEX idx_reports_project_no ON reports(project_no);
  CREATE INDEX idx_reports_invoice_no ON reports(invoice_no);
  CREATE INDEX idx_reports_invoice_date ON reports(invoice_date DESC);
  ```

**No Pagination on List Page:**
- Problem: The `index()` route fetches ALL reports from the database and renders them all in one page
- Files: `app.py` lines 222-244 (SELECT without LIMIT), `templates/list.html` (renders all rows)
- Cause: No pagination implemented
- Improvement path: Add `?page=1&per_page=50` with SQL `LIMIT/OFFSET`. Move aggregation totals to separate `SUM()` queries. Critical threshold: ~300 reports.

**New Database Connection Per Request:**
- Problem: Every request creates a new `psycopg2.connect()` and closes it. Some routes open multiple connections (e.g., `submit()` opens up to 3 connections: one for duplicate check, one for error-case vendor list, one for insert).
- Files: `app.py` line 110-112 (`get_conn()`), called ~30+ times across all routes
- Cause: No connection pooling
- Improvement path: Use Neon's PgBouncer pooler endpoint, or implement application-level pooling with `psycopg2.pool.ThreadedConnectionPool`. Note: Vercel serverless complicates traditional pooling — prefer Neon pooler.

**Index Page Loads All Vendors for Duplicate Detection:**
- Problem: The `index()` route loads the entire `vendors` table and does O(n^2) string comparison for duplicate detection in Python
- Files: `app.py` lines 272-311
- Cause: Duplicate detection logic runs in application code rather than SQL
- Improvement path: Move similarity detection to a scheduled job or background process. Cache results. For small vendor counts (<100) this is acceptable, but it scales poorly.

**Excel Export Loads All Data Into Memory:**
- Problem: `pd.read_sql()` loads the entire result set into a pandas DataFrame in memory
- Files: `app.py` lines 888-910
- Cause: No streaming or chunked export
- Improvement path: For current scale this is fine. For 10,000+ reports, consider streaming writes with openpyxl directly or chunked queries.

## Fragile Areas

**Template Tuple Index References:**
- Files: `templates/list.html` (references `r[0]` through `r[16]`), `templates/vendors.html` (references `v[0]` through `v[5]`), `templates/users.html` (references `u[0]` through `u[5]`)
- Why fragile: Any change to SELECT column order in `app.py` silently breaks template rendering. The reports query has 17 positional columns — extremely error-prone.
- Safe modification: When changing queries, verify every `r[N]` reference in both desktop and mobile template sections. The list.html has 6 distinct rendering paths (admin locked, admin unlocked, designer locked, designer unlocked, for both desktop and mobile).
- Test coverage: The test suite (`test_scenario.py`) verifies page loads but does not validate specific field rendering.

**Vendor Similarity Detection Logic:**
- Files: `app.py` lines 287-319 (in `index()`), lines 596-648 (in `check_vendor()`)
- Why fragile: The duplicate detection logic is duplicated between the list page and the API endpoint with slightly different implementations. Changes to one must be mirrored in the other.
- Safe modification: Extract into a shared function. Test with edge cases (empty strings, single-character vendor names, vendors with only keyword characters).
- Test coverage: Basic similarity is tested in `test_scenario.py`, but edge cases are not.

## Scaling Limits

**Neon Free Tier Connection Limits:**
- Current capacity: Neon free tier allows limited concurrent connections
- Limit: With no connection pooling, concurrent users can exhaust the connection limit, causing 500 errors
- Scaling path: Enable Neon PgBouncer pooler endpoint. Switch `POSTGRES_URL` to the pooler URL.

**Vercel Serverless Cold Starts:**
- Current capacity: Each request may incur a cold start, loading Flask + pandas + openpyxl
- Limit: pandas is a heavy dependency (~150MB). Cold starts can be 3-5 seconds.
- Scaling path: Consider removing pandas for non-export routes (lazy import). Or move export to a separate serverless function.

**Single-Region Deployment:**
- Current capacity: Vercel deploys to a single region by default
- Limit: Users outside the deployment region experience higher latency, especially for DB-heavy pages
- Scaling path: Configure Vercel region to match Neon DB region. Not a concern for a Taiwan-focused internal tool.

## Dependencies at Risk

**psycopg2-binary:**
- Risk: The `-binary` variant is not recommended for production by the psycopg2 maintainers. It bundles its own libpq which may have unpatched vulnerabilities.
- Impact: Potential security issues from bundled libpq
- Migration plan: Use `psycopg2` (non-binary) in production, or migrate to `psycopg` (v3) which is the actively developed successor.

**No Pinned Dependency Versions:**
- Risk: `requirements.txt` lists packages without version pins (`flask`, `pandas`, etc.). A `pip install` at different times can produce different dependency trees.
- Impact: Builds may break unpredictably when upstream packages release breaking changes
- Migration plan: Pin exact versions: `flask==3.x.x`, `pandas==2.x.x`, etc. Use `pip freeze > requirements.txt` from a known-good environment.

## Missing Critical Features

**No Filtering or Search:**
- Problem: Users cannot filter reports by date range, vendor, project, or category
- Blocks: Practical usage once report count exceeds ~50. Users must scroll through the entire list.

**No User Self-Service Password Change:**
- Problem: Designers cannot change their own passwords. They must ask an admin.
- Blocks: Basic self-service security hygiene. Increases admin support burden.

**No Audit Log:**
- Problem: Only the last modifier (`updated_by`, `updated_at`) is tracked. Deletes leave no trace. There is no history of changes.
- Blocks: Compliance, dispute resolution, and debugging data issues.

**No Error/Exception Monitoring:**
- Problem: No error tracking service (Sentry, etc.) is configured. Server errors in production are invisible unless a user reports them.
- Blocks: Proactive issue detection. The team has no way to know if the app is throwing 500 errors.

## Test Coverage Gaps

**No Unit Tests:**
- What's not tested: Individual functions like `default_remit_date()`, `is_business_day()`, `get_core()`, Excel generation helpers (`write_detail_sheet`, `write_summary_sheet`)
- Files: `app.py` (all helper functions)
- Risk: Regression in business logic (e.g., holiday calculation, vendor matching) goes undetected
- Priority: Medium — the scenario tests cover happy paths but miss edge cases

**Tests Require Running Server:**
- What's not tested: The test suite (`test_scenario.py`) uses `urllib` against a live server rather than Flask's test client
- Files: `test_scenario.py` line 12 (`BASE = 'http://127.0.0.1:5000'`)
- Risk: Cannot run in CI without a running server + database. Tests hit the real Neon database, not a test database. Tests mutate production-adjacent data.
- Priority: High — this blocks CI/CD automation and risks data corruption

**No Test for File Upload Edge Cases:**
- What's not tested: Oversized file upload, malformed Excel, Excel with formula injection, CSV injection, empty file, file with thousands of rows
- Files: `app.py` lines 775-853 (vendor_import)
- Risk: Memory exhaustion, data corruption, or security vulnerability via crafted uploads
- Priority: Medium

**No Test for Concurrent Access:**
- What's not tested: Two users editing the same report simultaneously, race conditions on invoice duplicate check
- Files: `app.py` lines 396-401 (invoice duplicate check has TOCTOU race)
- Risk: Duplicate invoice numbers could be inserted if two users submit simultaneously
- Priority: Low — current user count is very small

**No Negative Authorization Tests Beyond Basic 403:**
- What's not tested: Designer accessing `/users`, designer POSTing to `/vendors/update`, designer POSTing to `/toggle-lock-project`
- Files: `test_scenario.py` — tests designer isolation for reports but not for admin-only endpoints
- Risk: Authorization bypass on admin-only routes could go undetected
- Priority: Medium

---

*Concerns audit: 2026-04-16*
