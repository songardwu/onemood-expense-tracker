# Technology Stack

**Analysis Date:** 2026-04-16

## Languages

**Primary:**
- Python 3.x - All backend logic, migrations, tests (`app.py`, `migrate_v*.py`, `test_*.py`)

**Secondary:**
- JavaScript (ES5) - Client-side vendor similarity check and bank info lookup (`static/app.js`)
- HTML (Jinja2 templates) - Server-rendered UI (`templates/*.html`)
- CSS - Custom styling (`static/style.css`)

## Runtime

**Environment:**
- Python 3.x (exact version not pinned; no `.python-version` or `runtime.txt` present)
- Vercel Serverless Functions (`@vercel/python` builder)

**Package Manager:**
- pip
- Lockfile: **missing** (no `requirements.lock` or `pip.lock`; only `requirements.txt` without version pins)

## Frameworks

**Core:**
- Flask - Web framework, routing, sessions, template rendering (`app.py`)
- Flask-WTF / CSRFProtect - CSRF token protection on all forms (`app.py` line 104)
- Jinja2 - HTML templating (bundled with Flask) (`templates/`)

**Testing:**
- No test framework - Tests use raw `urllib` with custom `check()` assertion helper (`test_scenario.py`, `test_v3_full.py`, `test_v4.py`)

**Build/Dev:**
- No build tool for frontend (plain CSS + vanilla JS, no bundler)
- Flask development server for local dev (`app.py` line 1121: `app.run(debug=True)`)

## Key Dependencies

All dependencies in `requirements.txt` are **unpinned** (no version numbers):

**Critical:**
- `flask` - Web framework, routing, sessions, request handling
- `flask-wtf` - CSRF protection via `CSRFProtect`
- `psycopg2-binary` - PostgreSQL database driver (direct SQL, no ORM)
- `python-dotenv` - Loads `.env.local` for environment variables

**Infrastructure:**
- `pandas` - Excel/CSV import/export, SQL query results, data aggregation (`app.py` lines 890-1041)
- `openpyxl` - Excel `.xlsx` read/write engine (used by pandas)

## Configuration

**Environment:**
- `.env.local` file present - contains environment configuration (loaded via `python-dotenv`)
- Key env vars used in code:
  - `SECRET_KEY` - Flask session secret (required, `app.py` line 98)
  - `POSTGRES_URL` or `DATABASE_URL` - PostgreSQL connection string (`app.py` line 111)
  - `VERCEL` - Presence flag to enable secure cookies (`app.py` line 99)

**Session:**
- Flask server-side sessions with 7-day lifetime (`app.py` line 102)
- `SESSION_COOKIE_SECURE` enabled when `VERCEL` env var is set
- `SESSION_COOKIE_HTTPONLY = True`
- `SESSION_COOKIE_SAMESITE = 'Lax'`

**Security Headers:**
- `X-Content-Type-Options: nosniff` (`app.py` line 163)
- `X-Frame-Options: DENY` (`app.py` line 164)
- `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'` (`app.py` line 165)

**Build/Deploy:**
- `vercel.json` - Vercel deployment config, routes all requests to `api/index.py`

## Database

**Engine:** PostgreSQL (via `psycopg2-binary`)

**Access Pattern:** Raw SQL queries (no ORM). All queries use parameterized `%s` placeholders.

**Schema** (reconstructed from migrations):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | Authentication & roles | `id`, `username`, `display_name`, `password_hash`, `role`, `is_active` |
| `reports` | Invoice/payment records | `id`, `vendor`, `vendor_type`, `amount`, `category`, `invoice_no`, `invoice_date`, `remit_date`, `project_no`, `stage`, `payment_method`, `user_id`, `is_locked`, `updated_by`, `updated_at` |
| `vendors` | Vendor bank account info | `id`, `name` (unique), `bank_name`, `bank_code`, `account_no`, `account_name`, `created_by`, `updated_by` |
| `vendor_keywords` | Keywords for vendor name similarity matching | `id`, `keyword` (unique) |

**Migrations:** Manual Python scripts (`migrate_v2.py`, `migrate_v3.py`, `migrate_v4.py`)

## Platform Requirements

**Development:**
- Python 3.x with pip
- PostgreSQL database accessible via connection URL
- `.env.local` file with `SECRET_KEY` and `POSTGRES_URL`

**Production:**
- Vercel (serverless Python functions)
- PostgreSQL (likely Vercel Postgres or external provider based on `POSTGRES_URL` env var)

## Frontend

**Approach:** Server-rendered HTML with Jinja2 templates. No frontend framework.

**Assets:**
- `static/style.css` - Custom CSS (Apple-inspired minimal design)
- `static/app.js` - Vanilla JavaScript for vendor autocomplete/bank info (ES5, IIFE pattern)
- No npm/node dependencies
- No CSS framework (pure custom CSS)

---

*Stack analysis: 2026-04-16*
