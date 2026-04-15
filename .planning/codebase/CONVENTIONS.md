# Coding Conventions

**Analysis Date:** 2026-04-16

## Language & Framework

**Primary:** Python 3 with Flask (server-rendered Jinja2 templates)
**UI:** HTML + CSS + vanilla JavaScript (no frontend framework)
**All UI labels, error messages, and comments are in Traditional Chinese (zh-Hant).**

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (`app.py`, `migrate_v2.py`, `test_scenario.py`)
- Templates: `snake_case.html` (`base.html`, `list.html`, `new.html`, `vendors.html`, `users.html`, `login.html`)
- Static assets: `snake_case.ext` (`style.css`, `app.js`)
- Test files: `test_*.py` prefix (`test_scenario.py`, `test_v3_full.py`, `test_v4.py`)

**Functions (Python):**
- Use `snake_case` for all functions: `get_conn()`, `login_required()`, `default_remit_date()`
- Route handler names match their purpose: `index()`, `submit()`, `delete()`, `vendor_create()`
- Prefix with entity for CRUD: `vendor_create()`, `vendor_update()`, `vendor_delete()`, `vendor_import()`
- Helper/utility functions are standalone module-level: `is_business_day()`, `next_business_day()`, `get_core()`

**Variables (Python):**
- `snake_case` throughout: `vendor_totals`, `remit_date`, `amount_str`, `invoice_no`
- Single-letter only for loop iterables: `r` for row, `d` for date, `v` for vendor
- Database cursors always named `cur`, connections always named `conn`

**CSS Classes:**
- `kebab-case` throughout: `.btn-primary`, `.card-header`, `.inline-edit-input`
- BEM-like but not strict BEM: `.card-row`, `.card-label`, `.card-value`, `.card-footer`
- Component prefix pattern: `.btn-*`, `.nav-*`, `.card-*`, `.summary-*`, `.dup-*`
- State classes: `.row-locked`, `.row-disabled`, `.dup-highlight`
- Badge variants via suffix: `.badge-cost`, `.badge-admin`, `.badge-bonus`
- Status variants: `.status-active`, `.status-disabled`

**HTML IDs:**
- Dynamic IDs use prefix + database ID: `edit-{{ r[0] }}`, `medit-{{ r[0] }}`, `vedit-{{ v[0] }}`
- Static IDs use `kebab-case`: `vendor-hint`, `bank-info`, `vendor-list`

**JavaScript:**
- `camelCase` for variables: `vendorInput`, `hintBox`, `bankBox`, `fetchBankInfo`

## Code Style

**Formatting:**
- No linter or formatter configured (no `.eslintrc`, `.prettierrc`, `pyproject.toml`, etc.)
- 4-space indentation in Python (PEP 8 default)
- 4-space indentation in HTML templates and CSS
- Single quotes in Python strings
- Jinja2 uses `{{ }}` with single space padding

**Code Organization in `app.py`:**
- Sections delimited by comment blocks using `# =====================` banners
- Each section has a Chinese title comment: `# 登入 / 登出`, `# DB 連線`, `# 認證工具`
- Related routes grouped together (login/logout, CRUD for reports, CRUD for vendors, user management)
- Helper functions defined before routes that use them

## Route Conventions

**URL Pattern:**
- Resource listing: `GET /` (reports), `GET /vendors`, `GET /users`
- New form page: `GET /new`
- Create action: `POST /submit` (reports), `POST /vendors/create`, `POST /users/create`
- Update action: `POST /update-report/<id>`, `POST /vendors/update/<id>`
- Delete action: `POST /delete/<id>`, `POST /vendors/delete/<id>`
- Toggle action: `POST /users/<id>/toggle`, `POST /toggle-lock-project`
- API endpoints: `GET /api/check-vendor`, `GET /api/vendor-bank`
- Export: `GET /export`

**All mutating operations use POST (no PUT/PATCH/DELETE HTTP methods).**

**Route decorators are stacked:**
```python
@app.route('/vendors/update/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_update(vendor_id):
```

## Import Organization

**Order in `app.py`:**
1. Standard library (`os`, `datetime`, `functools`, `io`)
2. Third-party (`pandas`, `psycopg2`, `dotenv`, `flask`, `flask_wtf`, `werkzeug`)
3. No local imports at top level; `from collections import defaultdict` is imported inline in `index()`

**Note:** The inline `from collections import defaultdict` at line 261 of `app.py` breaks convention. New code should import at the top of the file.

## Error Handling

**Form Validation Pattern (submit route):**
```python
errors = []
if not vendor:
    errors.append('名稱為必填')
if not amount_str:
    errors.append('請款金額為必填')
else:
    try:
        amount = float(amount_str)
        if amount <= 0:
            errors.append('請款金額必須為正數')
    except ValueError:
        errors.append('請款金額必須為數字')

if errors:
    return render_template('new.html', error='、'.join(errors), ...)
```
- Collect all errors into a list
- Join with Chinese comma `、` for display
- Re-render the form with `error` context variable and `form=request.form` to preserve input

**Admin Update Validation Pattern (silent redirect):**
```python
if not vendor or not invoice_date or not project_no:
    cur.close(); conn.close()
    return redirect('/')
```
- Invalid input silently redirects to `/` with no error message
- Exception: duplicate invoice redirects to `/?error=invoice_dup`

**Vendor Create Validation Pattern (query param redirect):**
```python
return redirect('/vendors?error=missing')
return redirect('/vendors?error=duplicate')
```
- Error codes passed as query parameters
- Decoded to Chinese messages in the GET handler:
```python
if error == 'missing':
    error_msg = '所有欄位皆為必填'
elif error == 'duplicate':
    error_msg = '此廠商名稱已存在'
```

**Database Error Handling:**
```python
try:
    cur.execute(...)
    conn.commit()
except psycopg2.errors.UniqueViolation:
    conn.rollback()
    cur.close(); conn.close()
    return redirect('/vendors?error=duplicate')
```
- Only `UniqueViolation` is caught explicitly
- No general exception handling for database errors

**HTTP Error Codes:**
- `abort(404)` for missing resources
- `abort(403)` for unauthorized access (locked records, wrong user)
- No custom error pages except for CSRF 400 errors

**Resource Cleanup Pattern:**
```python
cur.close(); conn.close()  # semicolon-separated on one line for early returns
```
- Multiple statements on one line with semicolons for early-exit cleanup
- No context managers (`with`) used for database connections

## Authentication & Authorization

**Two-tier decorator system:**
- `@login_required` — any authenticated user
- `@admin_required` — admin role only (also checks login)

**Role-based access in templates:**
```jinja2
{% if user.role == 'admin' %}
<a href="/users" class="nav-link">帳號管理</a>
{% endif %}
```

**Ownership checks in route handlers:**
```python
if user['role'] == 'designer' and row[0] != user['id']:
    cur.close(); conn.close()
    abort(403)
```

## Template Patterns

**Layout inheritance:**
- `base.html` is the root layout with navbar + container
- All pages except `login.html` extend `base.html` via `{% extends "base.html" %}`
- `login.html` is standalone (no navbar)
- Single content block: `{% block content %}{% endblock %}`

**CSRF tokens in every form:**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

**Responsive dual-rendering:**
- Desktop: `<table class="desktop-table">` (hidden on mobile)
- Mobile: `<div class="mobile-cards">` (hidden on desktop 768px+)
- Both render the same data; mobile uses card layout, desktop uses table
- Admin inline-edit forms use `form="edit-{{ r[0] }}"` attribute to link inputs outside the form element
- Mobile edit forms use `form="medit-{{ r[0] }}"` prefix

**Data access pattern (tuple indexing):**
```jinja2
{{ r[0] }}   {# id #}
{{ r[1] }}   {# vendor #}
{{ r[3] }}   {# amount #}
{{ r[12] }}  {# is_locked #}
```
- Database rows are raw tuples, not dicts
- Accessed by numeric index throughout templates
- This is fragile; changing query column order breaks templates

**Amount formatting:**
```jinja2
{{ "{:,.0f}".format(r[3]) }}
```

**Badge class mapping via Jinja2 replace chain:**
```jinja2
badge-{{ r[4]|replace('案場成本','cost')|replace('管銷','admin')|replace('獎金','bonus') }}
```

**Conditional display pattern:**
```jinja2
{{ r[5] if r[5] else '-' }}
```

**Error display in templates:**
```jinja2
{% if error %}
<div class="error-msg">{{ error }}</div>
{% endif %}
```

## CSS Architecture

**Design System:** Apple-inspired minimalist (explicitly stated in CSS header comment)

**CSS Custom Properties (variables):**
- All colors, radii, shadows, transitions, and fonts defined in `:root`
- Semantic naming: `--text-primary`, `--text-secondary`, `--text-tertiary`
- Color + light variant pairs: `--red` / `--red-light`, `--green` / `--green-light`
- Consistent border-radius tokens: `--radius-s` (8px), `--radius-m` (12px), `--radius-l` (16px), `--radius-xl` (20px)

**Responsive Strategy:**
- Mobile-first: base styles target mobile
- Breakpoints: 389px (small mobile), 768px (tablet/desktop), 1200px (large desktop)
- `@supports (padding: env(safe-area-inset-bottom))` for iPhone notch

**Dark Mode:**
- `@media (prefers-color-scheme: dark)` override of CSS variables
- All component colors adapt via variables (no hardcoded colors in components)

**Print Styles:**
- Hides interactive elements (navbar, buttons, forms)
- Forces desktop table view

**Button System:**
- Pill-shaped buttons: `border-radius: 980px`
- Size variants: `.btn` (standard), `.btn-small` (compact), `.btn-submit` (full-width)
- Color variants: `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-success`, `.btn-outline`
- Functional variants: `.btn-save`, `.btn-delete`

**Typography:**
- System font stack: `-apple-system, BlinkMacSystemFont, "SF Pro Display"...`
- Monospace: `"SF Mono", SFMono-Regular, Menlo, monospace`
- Font smoothing: antialiased for both webkit and moz

## JavaScript Conventions

**Single file:** `static/app.js` (61 lines)
- IIFE pattern: `(function() { ... })();`
- No modules, no build step, no framework
- Vanilla `fetch()` for API calls
- Debounce via `setTimeout`/`clearTimeout` (300ms)
- Unicode escapes for Chinese strings in JS (e.g., `\u7CFB\u7D71`)
- ES5-compatible syntax (no arrow functions, no const/let) for broad browser support

## Database Access Pattern

**No ORM.** Raw SQL with `psycopg2` throughout.

**Connection lifecycle:**
```python
conn = get_conn()
cur = conn.cursor()
# ... execute queries ...
conn.commit()  # only for writes
cur.close()
conn.close()
```
- New connection per request (no connection pooling)
- Manual open/close (no context managers)
- Parameterized queries with `%s` placeholders (safe from SQL injection)

**Query results as tuples:**
- `cur.fetchall()` returns list of tuples
- `cur.fetchone()` returns single tuple or None
- No dictionary cursor used

## Logging

**None.** No logging framework configured. No `print()` or `logging.*` calls in production code.

## Comments

**When to Comment:**
- Section headers use decorated comment blocks
- Inline comments in Chinese explain business logic
- Docstrings only on utility functions (Chinese): `"""判斷是否為工作日（排除週末 + 台灣國定假日）"""`
- No comments on route handlers

---

*Convention analysis: 2026-04-16*
