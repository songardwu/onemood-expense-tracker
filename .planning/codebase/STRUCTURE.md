# Codebase Structure

**Analysis Date:** 2026-04-16

## Directory Layout

```
c:/Claude DEV-20260415/
├── api/
│   └── index.py            # Vercel serverless entry point
├── static/
│   ├── app.js              # Client-side JS (vendor check + bank info)
│   └── style.css           # All CSS (Apple-inspired, 1121 lines)
├── templates/
│   ├── base.html           # Layout template (navbar + container)
│   ├── login.html          # Standalone login page (no base extend)
│   ├── list.html           # Main report list (desktop table + mobile cards)
│   ├── new.html            # New report form
│   ├── users.html          # Admin user management
│   └── vendors.html        # Vendor bank info management
├── .claude/
│   ├── settings.json       # Claude Code project settings
│   └── settings.local.json # Claude Code local settings
├── .planning/
│   └── codebase/           # Architecture analysis docs (this dir)
├── .vercel/
│   ├── project.json        # Vercel project config
│   └── README.txt          # Vercel CLI readme
├── app.py                  # Main Flask application (1122 lines)
├── migrate_v2.py           # DB migration: users table + user_id on reports
├── migrate_v3.py           # DB migration: is_locked, updated_by, vendor_keywords
├── migrate_v4.py           # DB migration: vendors table, payment_method
├── requirements.txt        # Python dependencies (6 packages)
├── vercel.json             # Vercel routing + build config
├── .env.local              # Environment variables (secrets - DO NOT READ)
├── .gitignore              # Ignores .env.local, __pycache__, .vercel, *.xlsx
├── prd.md                  # V1 product requirements
├── prdv2.md                # V2 product requirements
├── prdv3.md                # V3 product requirements
├── prdv4.md                # V4 product requirements
├── sdd.md                  # V1 system design doc
├── sddv2.md                # V2 system design doc
├── sddv3.md                # V3 system design doc
├── sddv4.md                # V4 system design doc
├── task.md                 # V1 task breakdown
├── taskv2.md               # V2 task breakdown
├── taskv3.md               # V3 task breakdown
├── taskv4.md               # V4 task breakdown
├── test_scenario.py        # Test scenarios (committed)
├── test_v3_full.py         # V3 test suite (untracked)
├── test_v4.py              # V4 test suite (untracked)
├── HANDOFF20260415.md      # Handoff notes
├── HANDOFF20260415night.md # Handoff notes (night session)
├── TODO20260415.md         # Todo notes
└── TODO20260415night.md    # Todo notes (night session)
```

## Directory Purposes

**`api/`:**
- Purpose: Vercel serverless function adapter
- Contains: Single file `index.py` that imports the Flask app
- Key files: `api/index.py` - adds parent dir to `sys.path` and re-exports `app`

**`static/`:**
- Purpose: Client-side assets served at `/static/`
- Contains: One JS file, one CSS file
- Key files:
  - `static/app.js` (61 lines) - vendor similarity check + bank info lookup, loaded only on `/new` page
  - `static/style.css` (1121 lines) - complete Apple-inspired design system with dark mode + responsive breakpoints

**`templates/`:**
- Purpose: Jinja2 HTML templates
- Contains: 6 template files
- Key files:
  - `templates/base.html` (31 lines) - layout with navbar, block content; used by all pages except login
  - `templates/login.html` (33 lines) - standalone, does NOT extend base.html
  - `templates/list.html` (311 lines) - largest template; dual desktop-table/mobile-cards layout
  - `templates/new.html` (119 lines) - report creation form with datalist autocomplete
  - `templates/users.html` (85 lines) - admin-only user CRUD
  - `templates/vendors.html` (152 lines) - vendor bank info CRUD + bulk import

**Root directory:**
- Purpose: Application source, config, documentation
- Contains: Main app, migrations, config, docs
- Key files: `app.py` (the entire backend), `requirements.txt`, `vercel.json`

## Key File Locations

**Entry Points:**
- `app.py`: Main Flask application, all routes and business logic
- `api/index.py`: Vercel serverless adapter (imports `app` from `app.py`)
- `vercel.json`: Routes all requests to `api/index.py`

**Configuration:**
- `.env.local`: Environment variables (SECRET_KEY, POSTGRES_URL) - exists, never read
- `vercel.json`: Vercel build and routing config
- `requirements.txt`: Python package dependencies

**Core Logic (all in `app.py`):**
- Lines 18-91: Taiwan holidays + business day calculation + default remit date
- Lines 94-104: Flask app initialization, session config, CSRF setup
- Lines 110-112: `get_conn()` - database connection factory
- Lines 118-148: Authentication utilities (decorators)
- Lines 153-165: Security headers + CSRF error handler
- Lines 171-209: Login/logout routes
- Lines 215-327: `index()` - main list view (heaviest route, ~110 lines)
- Lines 333-432: Report CRUD (new, submit, delete)
- Lines 467-567: Report update routes (remit date, full edit, lock toggle)
- Lines 596-648: Vendor similarity API
- Lines 654-877: Vendor management (list, create, update, delete, template, import, bank API)
- Lines 882-1042: Excel export (detail + summary sheets)
- Lines 1047-1117: User management (list, create, toggle, reset password)

**Database Migrations:**
- `migrate_v2.py`: Creates `users` table, adds `user_id` to `reports`
- `migrate_v3.py`: Adds `is_locked`, `updated_by`, `updated_at` to `reports`; creates `vendor_keywords`
- `migrate_v4.py`: Creates `vendors` table; adds `payment_method` to `reports`

**Testing:**
- `test_scenario.py`: Committed test scenarios
- `test_v3_full.py`: V3 test suite (untracked)
- `test_v4.py`: V4 test suite (untracked)

**Static Assets:**
- `static/style.css`: Complete CSS design system
- `static/app.js`: Vendor check + bank info JS (only used on `/new` page)

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `app.py`, `migrate_v2.py`, `test_scenario.py`)
- Templates: `lowercase.html` (e.g., `base.html`, `list.html`)
- Static assets: `lowercase.ext` (e.g., `app.js`, `style.css`)
- Documentation: Mixed. PRD/SDD use `{name}v{N}.md`, handoffs use `ALLCAPS{date}.md`

**Routes:**
- Pages: kebab-case paths (e.g., `/update-remit-date/<id>`, `/toggle-lock-project`)
- API endpoints: `/api/` prefix with kebab-case (e.g., `/api/check-vendor`, `/api/vendor-bank`)
- Resource CRUD: `/resource/action/<id>` pattern (e.g., `/vendors/update/3`, `/users/5/toggle`)

**Python Functions:**
- Route handlers: `snake_case` matching the route purpose (e.g., `login_page`, `vendor_create`, `update_remit_date`)
- Utilities: `snake_case` (e.g., `get_conn`, `get_current_user`, `is_business_day`)

**CSS Classes:**
- BEM-lite with kebab-case (e.g., `.btn-primary`, `.card-header`, `.inline-edit-input`)
- Component-scoped prefixes (e.g., `.summary-panel`, `.summary-row`, `.summary-label`)

**HTML IDs:**
- Form linking: `edit-{id}`, `medit-{id}` (mobile), `vedit-{id}` (vendor), `mvedit-{id}` (mobile vendor)

## Where to Add New Code

**New Route/Feature:**
- Add to `app.py` in the appropriate section (follow the `# ===== Section =====` comment blocks)
- Use `@login_required` or `@admin_required` decorator
- Follow existing pattern: get connection, execute SQL, close connection, return redirect or render_template

**New Template:**
- Create in `templates/` directory
- Extend `base.html` using `{% extends "base.html" %}` and `{% block content %}`
- Include CSRF token in all forms: `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- Implement both desktop table (`.desktop-table`) and mobile cards (`.mobile-cards`) if it's a list view

**New CSS:**
- Add to `static/style.css`
- Follow the existing CSS custom property system (use `var(--accent)`, `var(--surface)`, etc.)
- Add dark mode overrides in the `@media (prefers-color-scheme: dark)` block at bottom
- Add responsive adjustments in the existing media query breakpoints

**New JavaScript:**
- Add to `static/app.js` or create a new file in `static/`
- Follow the IIFE pattern used in `app.js`: `(function() { ... })();`
- Load via `<script>` tag in the specific template that needs it (not in `base.html`)

**New Database Table:**
- Create a new migration file: `migrate_v{N}.py`
- Follow existing pattern: connect, execute DDL, commit, close
- Run manually: `python migrate_v{N}.py`

**New API Endpoint:**
- Add to `app.py` in the API section (after line ~596)
- Use `/api/` prefix
- Return `jsonify()` responses
- Apply `@login_required` decorator

**Utilities/Helpers:**
- Currently all in `app.py` (top of file for business logic, inline for one-off helpers)
- No separate utils module exists; for small helpers, add to top of `app.py`

## Special Directories

**`.vercel/`:**
- Purpose: Vercel CLI project metadata
- Generated: Yes (by `vercel` CLI)
- Committed: No (in `.gitignore`)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (by Python runtime)
- Committed: No (in `.gitignore`)

**`.planning/`:**
- Purpose: Project planning and analysis documents
- Generated: By tooling/manual
- Committed: Yes

**`.claude/`:**
- Purpose: Claude Code configuration
- Generated: By Claude Code
- Committed: Yes (settings.json)

## File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 1122 | Entire backend |
| `static/style.css` | 1121 | All CSS |
| `templates/list.html` | 311 | Main list view |
| `templates/vendors.html` | 152 | Vendor management |
| `templates/new.html` | 119 | Report form |
| `templates/users.html` | 85 | User management |
| `static/app.js` | 61 | Client-side JS |
| `templates/base.html` | 31 | Layout template |
| `templates/login.html` | 33 | Login page |
| `api/index.py` | 7 | Vercel adapter |
| `requirements.txt` | 6 | Dependencies |
| `vercel.json` | 10 | Vercel config |

---

*Structure analysis: 2026-04-16*
