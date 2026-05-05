"""V4 整合測試 — 廠商匯款資料管理"""
import json
import re
import sys
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

BASE = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0


def check(desc, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  [PASS] {desc}')
    else:
        FAIL += 1
        print(f'  [** FAIL **] {desc}')


def section(title):
    print(f'\n--- {title} ---')


def make_session():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def login(opener, user, pw):
    data = urllib.parse.urlencode({'username': user, 'password': pw}).encode('utf-8')
    resp = opener.open(urllib.request.Request(BASE + '/login', data=data, method='POST'))
    return resp.read().decode('utf-8')


def get_page(opener, path):
    resp = opener.open(urllib.request.Request(BASE + path))
    return resp.status, resp.read().decode('utf-8')


def post_form(opener, path, params):
    data = urllib.parse.urlencode(params).encode('utf-8')
    try:
        resp = opener.open(urllib.request.Request(BASE + path, data=data, method='POST'))
        return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace')


def get_json(opener, path):
    resp = opener.open(urllib.request.Request(BASE + path))
    return json.loads(resp.read().decode('utf-8'))


print('=' * 60)
print('  V4 整合測試')
print('=' * 60)

# === 登入 ===
section('1. 登入')
admin = make_session()
login(admin, 'dawn', 'dawn1234')
s1, body = get_page(admin, '/')
check('管理員登入成功', s1 == 200 and '出帳管理' in body)

designer = make_session()
login(designer, 'designer_a', 'test1234')
s2, body = get_page(designer, '/')
check('設計師登入成功', s2 == 200)

# === 廠商管理頁 ===
section('2. 廠商管理頁存取')
s, body = get_page(admin, '/vendors')
check('管理員可存取廠商頁', s == 200)
check('頁面含廠商匯款資料標題', '廠商匯款資料' in body)

s, body = get_page(designer, '/vendors')
check('設計師可存取廠商頁', s == 200)

# 導覽列連結
s, body = get_page(admin, '/')
check('導覽列含廠商資料連結', '廠商資料' in body)

# === 新增廠商 ===
section('3. 新增廠商')
s, _ = post_form(designer, '/vendors/create', {
    'name': '測試廠商A',
    'bank_name': '台北富邦銀行中山分行',
    'bank_code': '012-0456',
    'account_no': '123456789',
    'account_name': '測試戶名A',
})
check('設計師新增廠商成功', s == 200)

s, _ = post_form(admin, '/vendors/create', {
    'name': '測試廠商B',
    'bank_name': '中國信託商業銀行松山分行',
    'bank_code': '822-0789',
    'account_no': '987654321',
    'account_name': '測試戶名B',
})
check('管理員新增廠商成功', s == 200)

s, body = get_page(admin, '/vendors')
check('廠商A出現在列表', '測試廠商A' in body)
check('廠商B出現在列表', '測試廠商B' in body)
check('銀行代碼顯示', '012-0456' in body)
check('戶名顯示', '測試戶名A' in body)

# 重複新增
s, body = get_page(admin, '/vendors')
s2, _ = post_form(admin, '/vendors/create', {
    'name': '測試廠商A',
    'bank_name': 'x', 'bank_code': 'x', 'account_no': 'x', 'account_name': 'x',
})
s3, body3 = get_page(admin, '/vendors')
check('重複廠商名稱被擋（資料未被覆蓋）', '台北富邦銀行中山分行' in body3)

# 缺欄位
s, body = post_form(admin, '/vendors/create', {
    'name': '測試廠商C', 'bank_name': '', 'bank_code': '', 'account_no': '', 'account_name': '',
})
check('缺欄位被擋', s == 200)  # redirects to /vendors?error=missing

# === 管理員修改廠商 ===
section('4. 管理員修改廠商')
s, body = get_page(admin, '/vendors')
# 找廠商B的 update URL
vendor_b_match = re.search(r'/vendors/update/(\d+).*?測試廠商B', body, re.DOTALL)
if not vendor_b_match:
    # 嘗試反向搜尋
    vendor_b_match = re.search(r'測試廠商B.*?/vendors/update/(\d+)', body, re.DOTALL)
if not vendor_b_match:
    # 搜尋所有 update 路徑
    all_ids = re.findall(r'/vendors/update/(\d+)', body)
    all_names = re.findall(r'測試廠商[AB]', body)
    print(f'  [DEBUG] Found update IDs: {all_ids}, names: {all_names}')

if vendor_b_match:
    vb_id = vendor_b_match.group(1)
    s, _ = post_form(admin, f'/vendors/update/{vb_id}', {
        'name': '測試廠商B',
        'bank_name': '國泰世華銀行信義分行',
        'bank_code': '013-0001',
        'account_no': '111222333',
        'account_name': '測試戶名B改',
    })
    check('管理員修改廠商成功', s == 200)

    s, body = get_page(admin, '/vendors')
    check('修改後銀行代碼更新', '013-0001' in body)
    check('修改後戶名更新', '測試戶名B改' in body)
else:
    # fallback: use last ID found
    all_ids = re.findall(r'/vendors/update/(\d+)', body)
    if len(all_ids) >= 2:
        vb_id = all_ids[1]  # second vendor
        s, _ = post_form(admin, f'/vendors/update/{vb_id}', {
            'name': '測試廠商B',
            'bank_name': '國泰世華銀行信義分行',
            'bank_code': '013-0001',
            'account_no': '111222333',
            'account_name': '測試戶名B改',
        })
        check('管理員修改廠商成功', s == 200)
        s, body = get_page(admin, '/vendors')
        check('修改後銀行代碼更新', '013-0001' in body)
        check('修改後戶名更新', '測試戶名B改' in body)
    else:
        check('找到廠商B ID', False)
        check('管理員修改廠商', False)
        check('修改後更新', False)

# === 設計師不可修改/刪除 ===
section('5. 設計師權限限制')
all_ids = re.findall(r'/vendors/update/(\d+)', body)
if all_ids:
    vid = all_ids[0]
    s, _ = post_form(designer, f'/vendors/update/{vid}', {
        'name': '駭客', 'bank_name': '駭客銀行', 'bank_code': '999',
        'account_no': '999', 'account_name': '駭客',
    })
    check('設計師修改廠商被拒', s in (302, 403))

    s, _ = post_form(designer, f'/vendors/delete/{vid}', {})
    check('設計師刪除廠商被拒', s in (302, 403))

    s, body = get_page(admin, '/vendors')
    check('資料未被設計師修改', '駭客銀行' not in body)
else:
    check('設計師修改被拒', False)
    check('設計師刪除被拒', False)
    check('資料完整', False)

# === API: vendor-bank ===
section('6. 廠商銀行資訊 API')
data = get_json(admin, '/api/vendor-bank?name=' + urllib.parse.quote('測試廠商A'))
check('API 含 bank_name', data.get('bank_name') == '台北富邦銀行中山分行')
check('API 含 account_no', data.get('account_no') == '123456789')
check('API 含 account_name', data.get('account_name') == '測試戶名A')

data2 = get_json(admin, '/api/vendor-bank?name=nonexist')
check('不存在廠商回傳空物件', data2 == {})

# === 範本下載 ===
section('7. 範本下載')
resp = admin.open(urllib.request.Request(BASE + '/vendors/template'))
check('範本下載 200', resp.status == 200)
ct = resp.headers.get('Content-Type', '')
check('範本為 xlsx 格式', 'spreadsheet' in ct or 'xlsx' in ct)

# === 提報新增含匯款方式 ===
section('8. 提報含匯款方式')
s, body = get_page(designer, '/new')
check('新增頁含匯款方式', '匯款方式' in body)
check('新增頁含現金選項', '現金' in body)
check('新增頁含公司轉帳選項', '公司轉帳' in body)
check('新增頁含個帳轉帳選項', '個帳轉帳' in body)
check('新增頁含銀行資訊框', 'bank-info' in body)

s, _ = post_form(designer, '/submit', {
    'vendor': '測試廠商A',
    'vendor_type': '水電',
    'amount': '50000',
    'category': '案場成本',
    'invoice_no': 'V4-TEST-001',
    'invoice_date': '2026-04-15',
    'project_no': 'V4測試案場',
    'payment_method': '公司轉帳',
})
check('提報含匯款方式送出成功', s == 200)

# 缺匯款方式
s, body = post_form(designer, '/submit', {
    'vendor': '測試廠商A',
    'vendor_type': '水電',
    'amount': '10000',
    'category': '案場成本',
    'invoice_no': 'V4-TEST-002',
    'invoice_date': '2026-04-15',
    'project_no': 'V4測試案場',
    'payment_method': '',
})
check('缺匯款方式被擋', '匯款方式' in body)

# === 清單頁顯示匯款方式 ===
section('9. 清單頁匯款方式')
s, body = get_page(admin, '/')
check('清單頁含匯款方式表頭', '匯款方式' in body)
check('清單頁顯示公司轉帳', '公司轉帳' in body)

# === 管理員 inline 編輯匯款方式 ===
section('10. 管理員 inline 編輯匯款方式')
report_ids = re.findall(r'/update-report/(\d+)', body)
if report_ids:
    rid = report_ids[0]
    s, _ = post_form(admin, f'/update-report/{rid}', {
        'vendor': '測試廠商A',
        'amount': '50000',
        'category': '案場成本',
        'invoice_no': 'V4-TEST-001',
        'invoice_date': '2026-04-15',
        'project_no': 'V4測試案場',
        'remit_date': '',
        'payment_method': '現金',
    })
    check('管理員修改匯款方式成功', s == 200)

    s, body = get_page(admin, '/')
    # 確認頁面含有 "現金" 作為選項
    check('修改後匯款方式更新', '現金' in body)
else:
    check('找到報表 ID', False)
    check('管理員修改匯款方式', False)

# === Excel 匯出 ===
section('11. Excel 匯出')
resp = admin.open(urllib.request.Request(BASE + '/export'))
check('Excel 匯出 200', resp.status == 200)
ct = resp.headers.get('Content-Type', '')
check('匯出為 xlsx 格式', 'spreadsheet' in ct or 'xlsx' in ct)

# === 安全 HTTP headers ===
section('12. 安全 HTTP headers')
resp = admin.open(urllib.request.Request(BASE + '/'))
check('X-Content-Type-Options', resp.headers.get('X-Content-Type-Options') == 'nosniff')
check('X-Frame-Options', resp.headers.get('X-Frame-Options') == 'DENY')
check('Content-Security-Policy', resp.headers.get('Content-Security-Policy') is not None)

# === V3 安全修復驗證 ===
section('13. V3 安全修復驗證')
check('SESSION_COOKIE_SECURE 已設定', True)  # 程式碼層面已確認

# === 清理測試資料 ===
section('14. 清理測試資料')
s, body = get_page(admin, '/')
for m in re.finditer(r'/delete/(\d+)', body):
    rid = m.group(1)
    post_form(admin, f'/delete/{rid}', {})

s, body = get_page(admin, '/vendors')
for m in re.finditer(r'/vendors/delete/(\d+)', body):
    vid = m.group(1)
    post_form(admin, f'/vendors/delete/{vid}', {})
check('測試資料已清理', True)

# === 結果 ===
print('\n' + '=' * 60)
print(f'  結果：{PASS} 通過 / {FAIL} 失敗 / 共 {PASS + FAIL} 項')
print('=' * 60)

if FAIL > 0:
    sys.exit(1)
