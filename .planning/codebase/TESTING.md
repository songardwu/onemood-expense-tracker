# Testing Patterns

**Analysis Date:** 2026-04-16

## Test Framework

**Runner:**
- Custom hand-rolled test framework using Python stdlib only
- No pytest, unittest, or any test framework dependency
- Tests run as standalone scripts against a live Flask server

**Assertion Library:**
- Custom `check()` / `result()` functions that increment global `PASS`/`FAIL` counters
- No assertion library; boolean conditions evaluated inline

**Run Commands:**
```bash
# Start the server first (required)
python app.py

# In another terminal, run tests:
python test_scenario.py       # Full V1-V4 scenario tests (520 lines, ~55 checks)
python test_v3_full.py        # V3-focused scenario tests (511 lines, ~50 checks)
python test_v4.py             # V4 vendor management tests (317 lines, ~35 checks)
```

**Exit code:** `sys.exit(1)` on any failure, `0` on all pass.

## Test File Organization

**Location:**
- All test files in project root: `test_scenario.py`, `test_v3_full.py`, `test_v4.py`
- Co-located with `app.py` (no separate `tests/` directory)

**Naming:**
- `test_scenario.py` — comprehensive V1-V4 full-scenario test (latest, most complete)
- `test_v3_full.py` — V3-era scenario test (older, does NOT include CSRF tokens)
- `test_v4.py` — V4 vendor management focused test (older, does NOT include CSRF tokens)

**IMPORTANT:** `test_v3_full.py` and `test_v4.py` are likely broken since the CSRF protection was added. Only `test_scenario.py` properly handles CSRF token extraction and injection.

## Test Architecture

**Integration tests only.** All tests are HTTP-level integration tests that:
1. Start sessions via `urllib.request` with cookie jars
2. Make real HTTP requests to `http://127.0.0.1:5000`
3. Parse HTML responses to verify content
4. Query the PostgreSQL database directly for verification
5. Clean up test data after each run

**No unit tests exist.** No functions are tested in isolation (except `default_remit_date()` and `is_business_day()` which are imported and called directly in `test_scenario.py`).

## Test Structure

**Suite Organization in `test_scenario.py`:**
```python
"""全場景測試 — 涵蓋 V1~V4 所有功能"""

# Global counters
PASS = 0
FAIL = 0

# Helper functions
def check(desc, condition):     # Assert with description
def section(title):              # Section header printer
def extract_csrf(html):          # Parse CSRF token from HTML
def make_session():              # Create HTTP session with cookies
def login(opener, user, pw):     # Login and cache CSRF token
def get(opener, path):           # HTTP GET with CSRF caching
def post(opener, path, params):  # HTTP POST with auto CSRF injection
def get_json(opener, path):      # HTTP GET returning parsed JSON
def db_query(sql, params=None):  # Direct DB SELECT
def db_exec(sql, params=None):   # Direct DB INSERT/UPDATE/DELETE

# Test sections (numbered, sequential)
section('1. 登入/登出/權限')
section('2. 廠商資料管理 (V4)')
section('3. 廠商銀行 API + 防呆增強 (V4)')
# ... through section 15

# Cleanup
section('15. 清理測試資料')

# Summary
print(f'結果：{PASS} 通過 / {FAIL} 失敗 / 共 {PASS + FAIL} 項')
```

**Assertion Pattern:**
```python
def check(desc, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {desc}')
    else:
        FAIL += 1
        print(f'  [** FAIL **] {desc}')
```

**Session/Auth Pattern:**
```python
admin = make_session()
login(admin, 'dawn', 'dawn1234')

designer = make_session()
login(designer, 'designer_a', 'test1234')
```

## CSRF Token Handling

**Only `test_scenario.py` handles CSRF properly.** Pattern:

```python
_csrf_cache = {}  # opener id -> token

def extract_csrf(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'value="([^"]+)"\s+name="csrf_token"', html)
    return m.group(1) if m else ''

def post(opener, path, params):
    if 'csrf_token' not in params:
        token = _csrf_cache.get(id(opener), '')
        if not token:
            _, html = get(opener, '/')
            token = extract_csrf(html)
        params = dict(params)
        params['csrf_token'] = token
    # ... make request
```

- Tokens are cached per session (keyed by `id(opener)`)
- Automatically injected into POST requests
- Opportunistically refreshed on every GET response

## Database Verification Pattern

**Direct DB queries for assertion:**
```python
def db_query(sql, params=None):
    from app import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Usage:
rows = db_query("SELECT amount, payment_method FROM reports WHERE invoice_no = 'S-001'")
check('金額更新為 55000', float(rows[0][0]) == 55000)
```

## Test Data Management

**Prefix convention:** Test data uses `S_` or `S-` prefix for easy identification and cleanup.

**Cleanup at end of test:**
```python
section('15. 清理測試資料')
db_exec("DELETE FROM reports WHERE invoice_no LIKE %s", ('S-%',))
db_exec("DELETE FROM reports WHERE invoice_no = %s", ('S-ADMIN-001',))
db_exec("DELETE FROM vendors WHERE name LIKE %s", ('S\\_%',))
```

**Prerequisite:** Tests assume specific users exist in the database:
- `dawn` / `dawn1234` (admin) — used by `test_scenario.py`
- `dawn` / `admin123` (admin) — used by `test_v3_full.py` (different password!)
- `designer_a` / `test1234` (designer) — used by `test_scenario.py`

**`test_v3_full.py` creates its own test users** (`designer_a`, `designer_b`) and cleans them up. `test_scenario.py` assumes they already exist.

## What Is Tested

**`test_scenario.py` (most complete, 15 sections):**

| Section | What's Tested |
|---------|---------------|
| 1 | Login/logout, role-based access, invalid credentials |
| 2 | Vendor CRUD (admin + designer), duplicate name prevention, template download |
| 3 | Vendor bank API, similar vendor detection |
| 4 | Report creation with payment method, default remit date, validation |
| 5 | List page totals, vendor subtotals, duplicate vendor warnings |
| 6 | Admin inline edit (amount, payment method, remit date) |
| 7 | Project locking (lock/unlock, prevents delete/edit) |
| 8 | Designer data isolation (can't see other users' reports) |
| 9 | Cross-user operation prevention (designer can't delete admin's report) |
| 10 | Input validation (invalid category, negative amount rejected) |
| 11 | Security HTTP headers (X-Content-Type-Options, X-Frame-Options, CSP) |
| 12 | Default remit date business logic (holidays, weekends, year boundary) |
| 13 | Excel export (format, column headers, bank data inclusion) |
| 14 | Navigation bar (role-based links) |
| 15 | Test data cleanup |

**`test_v3_full.py` (14 sections):**
- User creation by admin, designer login
- Report submission (3 reports per designer)
- Data isolation between designers
- Cross-user deletion/update prevention
- Duplicate invoice prevention (including cross-user)
- Admin global view + inline edit (all fields)
- Project locking/unlocking
- Vendor similarity API
- Audit trail display
- User disable/enable/password reset
- Excel export with total verification
- Test data cleanup

**`test_v4.py` (14 sections):**
- Vendor page access (admin + designer)
- Vendor CRUD with permission checks
- Vendor bank info API
- Template download
- Report with payment_method field
- Admin inline edit of payment_method
- Excel export
- Security headers
- Test data cleanup

## What Is NOT Tested

- **Unit tests:** No isolated function tests (except `default_remit_date` called directly)
- **Edge cases:** No boundary testing for amount values, date formats, XSS payloads
- **Concurrent access:** No parallel request testing
- **File upload:** Vendor import via xlsx/csv is not tested in any test file
- **Error pages:** 404/500 error page rendering
- **Session expiry:** No testing of session timeout behavior
- **CSRF rejection:** No test verifies that requests without CSRF tokens are rejected
- **Password hashing:** No verification that passwords are properly hashed
- **Excel content deep validation:** `test_scenario.py` checks headers but not all data rows
- **Dark mode / responsive CSS:** No visual/UI testing
- **JavaScript functionality:** No testing of `app.js` (vendor hint, bank info fetch)

## Coverage

**Requirements:** None enforced. No coverage tool configured.

**Estimated coverage by area:**
- Authentication/Authorization: **High** (login, roles, cross-user protection)
- Report CRUD: **High** (create, delete, update, validation)
- Vendor CRUD: **High** (create, update, delete, duplicate prevention)
- API endpoints: **High** (`/api/check-vendor`, `/api/vendor-bank`)
- Excel export: **Medium** (format verified, partial content check)
- Vendor import: **None** (not tested)
- Business logic (remit date): **High** (multiple date scenarios tested)
- Security headers: **High** (all three headers verified)
- Error handling: **Medium** (validation tested, but no 500 error scenarios)

## How to Add New Tests

Follow the pattern in `test_scenario.py`:

1. Add a new `section('N. Description')` call
2. Use existing session variables (`admin`, `designer`) or create new ones
3. Use `post()` / `get()` / `get_json()` helpers for HTTP requests
4. Use `db_query()` / `db_exec()` for direct database verification
5. Use `check('description', boolean_condition)` for assertions
6. Prefix test data with `S_` or `S-` for cleanup
7. Add cleanup in section 15

**Example adding a new test:**
```python
section('16. New Feature Test')
s, body = post(designer, '/submit', {
    'vendor': 'S_TestVendor', 'vendor_type': 'Test',
    'amount': '1000', 'category': '管銷',
    'invoice_no': 'S-NEW-001', 'invoice_date': '2026-04-16',
    'project_no': 'S案場Test', 'payment_method': '現金',
})
check('New feature works', s == 200)

# Verify in DB
rows = db_query("SELECT amount FROM reports WHERE invoice_no = 'S-NEW-001'")
check('Amount stored correctly', float(rows[0][0]) == 1000)

# Add cleanup in section 15:
# db_exec("DELETE FROM reports WHERE invoice_no = 'S-NEW-001'")
```

## Known Issues

1. **`test_v3_full.py` and `test_v4.py` are broken** — they do not handle CSRF tokens. Running them against the current server will fail on all POST requests.

2. **Tests depend on pre-existing database users** — `test_scenario.py` requires `dawn`/`dawn1234` and `designer_a`/`test1234` to exist. If the database is reset, tests will fail.

3. **Tests are not idempotent if interrupted** — if a test run is killed before cleanup, leftover `S_`/`S-` prefixed data remains in the database. Manual cleanup needed:
   ```sql
   DELETE FROM reports WHERE invoice_no LIKE 'S-%';
   DELETE FROM vendors WHERE name LIKE 'S\_%';
   ```

4. **No test isolation** — all tests share the same database. Running multiple test files simultaneously will cause conflicts.

5. **Password mismatch** — `test_scenario.py` uses `dawn1234` for admin, `test_v3_full.py` uses `admin123`. Only one can be correct for the current database state.

---

*Testing analysis: 2026-04-16*
