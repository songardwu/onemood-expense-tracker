# External Integrations

**Analysis Date:** 2026-04-16

## APIs & External Services

**Internal JSON APIs:**
- `GET /api/check-vendor?q=<name>` - Vendor name similarity check (returns `{"similar": [...]}`)
  - Used by: `static/app.js` with debounced `fetch()` on vendor input
  - Implementation: `app.py` lines 596-648
- `GET /api/vendor-bank?name=<name>` - Vendor bank account lookup (returns bank details JSON)
  - Used by: `static/app.js` on vendor input blur/change
  - Implementation: `app.py` lines 856-876

**No external API integrations detected.** The application does not call any third-party REST APIs, webhooks, or external services.

## Data Storage

**Database:**
- PostgreSQL
  - Connection: `POSTGRES_URL` or `DATABASE_URL` env var
  - Client: `psycopg2-binary` (raw SQL, no ORM)
  - Connection function: `get_conn()` in `app.py` line 110-112
  - Pattern: New connection per request, manually opened and closed (no connection pooling)
  - Tables: `users`, `reports`, `vendors`, `vendor_keywords`

**File Storage:**
- No persistent file storage
- Excel export generated in-memory (`BytesIO`) and streamed to client (`app.py` lines 916-928)
- Vendor import reads uploaded file in-memory (no disk write) (`app.py` lines 776-853)

**Caching:**
- None. No Redis, memcached, or in-memory caching layer.

## Authentication & Identity

**Auth Provider:** Custom (built-in)
- Session-based authentication using Flask `session`
- Password hashing: `werkzeug.security.generate_password_hash` / `check_password_hash`
- Roles: `admin` and `designer` (stored in `users.role` column)
- CSRF protection: `flask_wtf.csrf.CSRFProtect` applied globally (`app.py` line 104)
- Login endpoint: `POST /login` (`app.py` lines 178-203)
- Decorators: `@login_required` and `@admin_required` (`app.py` lines 129-147)

**No OAuth, SSO, JWT, or third-party auth providers.**

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Datadog, or error tracking service.

**Logs:**
- No structured logging. Uses default Flask/Werkzeug request logging only.
- Migration scripts use `print()` for status output.

**Analytics:**
- None detected.

## CI/CD & Deployment

**Hosting:**
- Vercel (serverless Python functions)
- Entry point: `api/index.py` imports `app` from root `app.py`
- Config: `vercel.json` routes all traffic (`/static/*` and `/*`) to `api/index.py`

**CI Pipeline:**
- None detected (no `.github/workflows/`, no `Jenkinsfile`, no `.circleci/`)

**Database Migrations:**
- Manual Python scripts run by developer:
  - `migrate_v2.py` - Creates `users` table, adds `user_id` to `reports`
  - `migrate_v3.py` - Adds `is_locked`/`updated_by`/`updated_at` to `reports`, creates `vendor_keywords`
  - `migrate_v4.py` - Creates `vendors` table, adds `payment_method` to `reports`
- No migration framework (no Alembic, no Flask-Migrate)

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` - Flask session encryption key (fatal if missing, `app.py` line 98)
- `POSTGRES_URL` or `DATABASE_URL` - PostgreSQL connection string (`app.py` line 111)

**Optional env vars:**
- `VERCEL` - When set (truthy), enables `SESSION_COOKIE_SECURE` (`app.py` line 99)

**Secrets location:**
- `.env.local` file (present in repo root, loaded by `python-dotenv`)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## File Import/Export

**Excel Export (`GET /export`):**
- Uses `pandas` + `openpyxl` to generate `.xlsx` in memory
- Two sheets: detail ("明細") with vendor subtotals, and summary ("總覽") with category breakdown
- Admin export includes reporter names and per-reporter aggregation
- Implementation: `app.py` lines 882-1041

**Vendor Data Import (`POST /vendors/import`):**
- Accepts `.xlsx` or `.csv` uploads
- Column mapping supports Chinese headers with aliases (e.g., "名稱" or "廠商名稱" both map to `name`)
- Admin users can update existing vendors; non-admin users skip duplicates
- Template download available at `GET /vendors/template`
- Implementation: `app.py` lines 775-853

## Third-Party Libraries (Integration Role)

| Library | Integration Purpose | Used In |
|---------|-------------------|---------|
| `psycopg2-binary` | PostgreSQL wire protocol | `app.py` (all routes) |
| `pandas` | SQL result reading, Excel/CSV I/O | `app.py` (export, import) |
| `openpyxl` | Excel .xlsx engine for pandas | `app.py` (export, import, template) |
| `python-dotenv` | Load `.env.local` config | `app.py` line 13 |
| `werkzeug` | Password hashing (bundled with Flask) | `app.py` (login, user mgmt) |

---

*Integration audit: 2026-04-16*
