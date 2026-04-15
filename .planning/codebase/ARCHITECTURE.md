# Architecture

**Analysis Date:** 2026-04-16

## Pattern Overview

**Overall:** Server-side rendered monolithic Flask application (MVC without explicit Model layer)

**Key Characteristics:**
- Single-file backend (`app.py`, ~1122 lines) containing all routes, business logic, and DB queries
- Server-side HTML rendering via Jinja2 templates with no client-side framework
- Direct PostgreSQL queries via psycopg2 (no ORM)
- Session-based authentication with role-based access control (admin / designer)
- Deployed as a Vercel serverless function via `api/index.py` adapter
- CSRF protection via Flask-WTF on all POST forms
- Mobile-first responsive design with desktop table / mobile card dual rendering

## Layers

**Routing & Request Handling (Controller):**
- Purpose: Accept HTTP requests, validate input, dispatch to DB operations, return responses
- Location: `app.py` lines 171-1121 (all `@app.route` decorated functions)
- Contains: Route handlers, input validation, authorization checks
- Depends on: `get_conn()`, `get_current_user()`, `login_required`, `admin_required`
- Used by: Vercel serverless runtime via `api/index.py`

**Authentication & Authorization:**
- Purpose: Session management, login/logout, role-based decorators
- Location: `app.py` lines 118-148
- Contains: `get_current_user()`, `login_required`, `admin_required` decorators
- Depends on: Flask `session`, `werkzeug.security` for password hashing
- Used by: Every route handler

**Database Access:**
- Purpose: Direct SQL queries against PostgreSQL
- Location: Inline within each route handler in `app.py`
- Contains: Raw SQL via `psycopg2` cursors, no abstraction layer
- Depends on: `get_conn()` (line 110-112) which reads `POSTGRES_URL` or `DATABASE_URL` env var
- Used by: All route handlers

**Business Logic:**
- Purpose: Domain-specific calculations (holidays, remit dates, vendor similarity)
- Location: `app.py` lines 18-91 (holidays/dates), lines 287-319 (vendor dedup in `index()`)
- Contains: Taiwan holiday calendar, business day calculation, vendor similarity matching
- Depends on: Python `datetime`, `vendor_keywords` table
- Used by: `submit()` route, `index()` route, `check_vendor()` API

**Presentation (View):**
- Purpose: Render HTML pages
- Location: `templates/` directory (6 files)
- Contains: Jinja2 templates extending `base.html`
- Depends on: Data passed from route handlers
- Used by: `render_template()` calls in route handlers

**Client-Side JS:**
- Purpose: Real-time vendor similarity check + bank info lookup on the new report form
- Location: `static/app.js` (61 lines)
- Contains: Debounced fetch to `/api/check-vendor`, bank info fetch to `/api/vendor-bank`
- Depends on: DOM elements `#vendor`, `#vendor-hint`, `#bank-info`
- Used by: `templates/new.html` (loaded via `<script>` tag)

**Excel Export:**
- Purpose: Generate downloadable .xlsx reports with detail + summary sheets
- Location: `app.py` lines 882-1042, functions `export()`, `write_detail_sheet()`, `write_summary_sheet()`
- Contains: pandas DataFrame construction, openpyxl Excel writing
- Depends on: `pandas`, `openpyxl`, `BytesIO`
- Used by: `/export` route

## Data Flow

**Report Submission Flow:**

1. User navigates to `/new` -> `new_report()` loads vendor list + vendor types from DB -> renders `new.html`
2. User types vendor name -> `static/app.js` fires debounced GET `/api/check-vendor?q=...` -> returns similar vendor warnings
3. User selects vendor -> `static/app.js` fires GET `/api/vendor-bank?name=...` -> displays bank info inline
4. User submits form -> POST `/submit` -> `submit()` validates all fields server-side
5. If validation fails: re-render `new.html` with errors + preserved form data
6. If valid: INSERT into `reports` table -> redirect to `/`

**List View (Main Page) Flow:**

1. GET `/` -> `index()` checks user role
2. Admin: SELECT all reports with JOIN on users; Designer: SELECT only own reports
3. Compute vendor totals, method totals, grand total (in-memory via Python dicts)
4. Load vendor bank info from `vendors` table
5. Load `vendor_keywords` for similarity detection
6. Run vendor dedup algorithm (name-based + account-based matching)
7. Render `list.html` with reports, totals, dup_flags, vendor_bank_info

**Admin Inline Edit Flow:**

1. Admin sees editable form fields in `list.html` table (not locked rows)
2. Each row has a `<form id="edit-{id}">` pointing to POST `/update-report/{id}`
3. Input fields use `form="edit-{id}"` attribute to associate with the form
4. Submit -> `update_report()` validates, checks lock status, updates DB -> redirect `/`

**Excel Export Flow:**

1. GET `/export` -> query reports (admin: all with reporter name; designer: own only)
2. Join with `vendors` table to include bank info in export
3. Build detail sheet: group by vendor with subtotals, category subtotals, grand total
4. Build summary sheet: current month + year-to-date by category, admin gets per-reporter breakdown
5. Return `.xlsx` file via `send_file()`

**State Management:**
- Server-side sessions (Flask `session` dict) store `user_id`, `display_name`, `role`
- Session configured with 7-day lifetime, HttpOnly, SameSite=Lax cookies
- No client-side state management; all state lives in PostgreSQL
- Flash-style messages passed via query params (e.g., `/?error=invoice_dup`) or session (e.g., `import_result`)

## Key Abstractions

**User Roles:**
- Purpose: Control access and UI visibility
- Two roles: `admin` (full access) and `designer` (own records only)
- Pattern: Decorators `@login_required` (`app.py` line 129) and `@admin_required` (`app.py` line 138)
- Admin sees: all reports, inline editing, user management, project locking, vendor deletion
- Designer sees: own reports only, limited editing (remit date + delete own unlocked)

**Project Locking:**
- Purpose: Freeze a project's reports to prevent edits/deletes
- `reports.is_locked` boolean column, toggled per `project_no` via `/toggle-lock-project`
- Enforced in: `delete()`, `update_remit_date()`, `update_report()` — all check `is_locked` before mutation
- UI: locked rows display as read-only; admin sees lock/unlock toggle in project panel

**Vendor Similarity Detection:**
- Purpose: Warn about potential duplicate vendors (different names, same entity)
- Two detection methods: name-based (strip keywords, compare cores) and account-based (same bank account)
- Keywords stored in `vendor_keywords` table (e.g., "公司", "行", "工作室")
- Used in: real-time API (`/api/check-vendor`) and list page summary (`index()`)

## Entry Points

**Web Application:**
- Location: `app.py` line 94 (`app = Flask(...)`)
- Triggers: HTTP requests routed through Vercel
- Responsibilities: All web request handling

**Vercel Serverless Adapter:**
- Location: `api/index.py`
- Triggers: All HTTP requests (`vercel.json` routes everything to `api/index.py`)
- Responsibilities: Add project root to `sys.path`, import and expose `app` from `app.py`

**Local Development:**
- Location: `app.py` line 1120-1121 (`if __name__ == '__main__': app.run(debug=True)`)
- Triggers: `python app.py`

**Migration Scripts:**
- Location: `migrate_v2.py`, `migrate_v3.py`, `migrate_v4.py`
- Triggers: Manual one-time execution (`python migrate_v4.py`)
- Responsibilities: Schema evolution (additive only)

## Routes Map

| Method | Path | Handler | Auth | Purpose |
|--------|------|---------|------|---------|
| GET | `/login` | `login_page()` | None | Login form |
| POST | `/login` | `login()` | None | Authenticate user |
| GET | `/logout` | `logout()` | None | Clear session |
| GET | `/` | `index()` | login | Main report list |
| GET | `/new` | `new_report()` | login | New report form |
| POST | `/submit` | `submit()` | login | Create report |
| POST | `/delete/<id>` | `delete()` | login | Delete report |
| POST | `/update-remit-date/<id>` | `update_remit_date()` | login | Update remit date |
| POST | `/update-report/<id>` | `update_report()` | admin | Full report edit |
| POST | `/toggle-lock-project` | `toggle_lock_project()` | admin | Lock/unlock project |
| GET | `/api/check-vendor` | `check_vendor()` | login | Vendor similarity API |
| GET | `/api/vendor-bank` | `vendor_bank()` | login | Vendor bank info API |
| GET | `/vendors` | `vendor_list()` | login | Vendor list page |
| POST | `/vendors/create` | `vendor_create()` | login | Create vendor |
| POST | `/vendors/update/<id>` | `vendor_update()` | admin | Update vendor |
| POST | `/vendors/delete/<id>` | `vendor_delete()` | admin | Delete vendor |
| GET | `/vendors/template` | `vendor_template()` | login | Download Excel template |
| POST | `/vendors/import` | `vendor_import()` | login | Bulk import vendors |
| GET | `/export` | `export()` | login | Export Excel report |
| GET | `/users` | `user_list()` | admin | User management page |
| POST | `/users/create` | `user_create()` | admin | Create user |
| POST | `/users/<id>/toggle` | `user_toggle()` | admin | Toggle user active |
| POST | `/users/<id>/reset-password` | `user_reset_password()` | admin | Reset password |

## Database Schema

**`users` table:**
- `id` SERIAL PK
- `username` VARCHAR(50) UNIQUE NOT NULL
- `display_name` VARCHAR(100) NOT NULL
- `password_hash` VARCHAR(255) NOT NULL
- `role` VARCHAR(20) CHECK IN ('designer', 'admin')
- `is_active` BOOLEAN DEFAULT TRUE
- `created_at` TIMESTAMP

**`reports` table:**
- `id` SERIAL PK
- `vendor` - vendor/payee name
- `vendor_type` - company type
- `amount` - payment amount
- `category` - one of: '案場成本', '管銷', '獎金'
- `invoice_no` - nullable, unique invoice number
- `invoice_date` - invoice date
- `remit_date` - payment date
- `project_no` - project name
- `stage` - nullable construction stage
- `payment_method` VARCHAR(20) - one of: '現金', '公司轉帳', '個帳轉帳'
- `user_id` INTEGER FK -> users(id) NOT NULL
- `is_locked` BOOLEAN DEFAULT FALSE
- `updated_by` INTEGER FK -> users(id)
- `updated_at` TIMESTAMP
- `created_at` TIMESTAMP

**`vendors` table:**
- `id` SERIAL PK
- `name` VARCHAR(200) UNIQUE NOT NULL
- `bank_name` VARCHAR(200) NOT NULL
- `bank_code` VARCHAR(50) NOT NULL
- `account_no` VARCHAR(50) NOT NULL
- `account_name` VARCHAR(200) NOT NULL
- `created_by` INTEGER FK -> users(id)
- `created_at` TIMESTAMP
- `updated_by` INTEGER FK -> users(id)
- `updated_at` TIMESTAMP

**`vendor_keywords` table:**
- `id` SERIAL PK
- `keyword` VARCHAR(50) UNIQUE NOT NULL

## Error Handling

**Strategy:** Minimal error handling; validation errors shown to user, system errors propagate as 500s

**Patterns:**
- Form validation: collect errors list, re-render form with `error` message if non-empty (`app.py` lines 372-417)
- CSRF errors: caught by `@app.errorhandler(400)` -> render login page with timeout message (`app.py` lines 153-157)
- Authorization failures: `abort(403)` for locked records or unauthorized access
- Not found: `abort(404)` for missing records
- Database unique violations: caught via `psycopg2.errors.UniqueViolation` try/except (`app.py` lines 700-711)
- No global error handler for 500 errors

## Cross-Cutting Concerns

**Security Headers:** Set via `@app.after_request` (`app.py` lines 160-165):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'`

**Session Security:** HttpOnly cookies, SameSite=Lax, Secure when on Vercel (`app.py` lines 99-102)

**CSRF Protection:** Flask-WTF `CSRFProtect` globally enabled (`app.py` line 104). Every POST form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`

**Validation:** Server-side only, inline in route handlers. No shared validation utilities.

**Logging:** None. No logging framework configured.

---

*Architecture analysis: 2026-04-16*
