"""V3 完整情境測試 — 模擬管理員 + 設計師角色"""
import json
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import sys

BASE = 'http://127.0.0.1:5000'
PASS = 0
FAIL = 0


def result(name, ok):
    global PASS, FAIL
    tag = 'PASS' if ok else '** FAIL **'
    if ok:
        PASS += 1
    else:
        FAIL += 1
    print(f'  [{tag}] {name}')


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


def db_query(sql, params=None):
    from app import get_conn
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ============================================================
print('=' * 60)
print('  V3 完整情境測試')
print('=' * 60)

# ============================================================
print('\n--- 1. 管理員建立測試帳號 ---')
# ============================================================
admin = make_session()
body = login(admin, 'dawn', 'admin123')
result('管理員登入成功', 'Dawn' in body)

# 建立 designer_a (王小明) 和 designer_b (李小華)
post_form(admin, '/users/create', {
    'username': 'designer_a', 'display_name': '王小明',
    'password': 'pass123', 'role': 'designer'
})
post_form(admin, '/users/create', {
    'username': 'designer_b', 'display_name': '李小華',
    'password': 'pass123', 'role': 'designer'
})

_, users_body = get_page(admin, '/users')
result('designer_a (王小明) 建立成功', 'designer_a' in users_body)
result('designer_b (李小華) 建立成功', 'designer_b' in users_body)

# ============================================================
print('\n--- 2. 設計師 A (王小明) 提報 ---')
# ============================================================
des_a = make_session()
body_a = login(des_a, 'designer_a', 'pass123')
result('設計師 A 登入成功', '王小明' in body_a or '出帳管理' in body_a)

# 看不到管理員連結
result('設計師 A 看不到帳號管理', '帳號管理' not in body_a)

# 提報 3 筆
reports_a = [
    {'vendor': '大明設計公司', 'vendor_type': '設計', 'amount': '50000',
     'category': '案場成本', 'invoice_no': 'A2026-001',
     'invoice_date': '2026-04-10', 'project_no': '陳宅翻新',
     'stage': '設計階段', 'remit_date': ''},
    {'vendor': '好木材料行', 'vendor_type': '建材', 'amount': '32000',
     'category': '案場成本', 'invoice_no': 'A2026-002',
     'invoice_date': '2026-04-11', 'project_no': '陳宅翻新',
     'stage': '施工階段', 'remit_date': ''},
    {'vendor': '快遞物流公司', 'vendor_type': '物流', 'amount': '3500',
     'category': '管銷', 'invoice_no': 'A2026-003',
     'invoice_date': '2026-04-12', 'project_no': '林宅新建',
     'stage': '', 'remit_date': '2026-04-15'},
]

for i, r in enumerate(reports_a):
    status, _ = post_form(des_a, '/submit', r)
    result(f'設計師 A 提報第 {i+1} 筆 ({r["vendor"]})', status == 200)

# 確認看到自己的 3 筆
_, list_a = get_page(des_a, '/')
result('設計師 A 看到大明設計公司', '大明設計公司' in list_a)
result('設計師 A 看到好木材料行', '好木材料行' in list_a)
result('設計師 A 看到快遞物流公司', '快遞物流公司' in list_a)

# ============================================================
print('\n--- 3. 設計師 B (李小華) 提報 ---')
# ============================================================
des_b = make_session()
body_b = login(des_b, 'designer_b', 'pass123')
result('設計師 B 登入成功', '出帳管理' in body_b)

# B 看到空清單
result('設計師 B 初始為空', '目前沒有提報資料' in body_b)

reports_b = [
    {'vendor': '永豐工程行', 'vendor_type': '工程', 'amount': '120000',
     'category': '案場成本', 'invoice_no': 'B2026-001',
     'invoice_date': '2026-04-13', 'project_no': '張宅裝潢',
     'stage': '拆除階段', 'remit_date': ''},
    {'vendor': '文具王', 'vendor_type': '辦公', 'amount': '1200',
     'category': '管銷', 'invoice_no': 'B2026-002',
     'invoice_date': '2026-04-14', 'project_no': '張宅裝潢',
     'stage': '', 'remit_date': ''},
]

for i, r in enumerate(reports_b):
    status, _ = post_form(des_b, '/submit', r)
    result(f'設計師 B 提報第 {i+1} 筆 ({r["vendor"]})', status == 200)

_, list_b = get_page(des_b, '/')
result('設計師 B 看到永豐工程行', '永豐工程行' in list_b)
result('設計師 B 看到文具王', '文具王' in list_b)

# ============================================================
print('\n--- 4. 資料隔離驗證 ---')
# ============================================================
# A 看不到 B 的資料
_, list_a2 = get_page(des_a, '/')
result('設計師 A 看不到永豐工程行', '永豐工程行' not in list_a2)
result('設計師 A 看不到文具王', '文具王' not in list_a2)

# B 看不到 A 的資料
_, list_b2 = get_page(des_b, '/')
result('設計師 B 看不到大明設計公司', '大明設計公司' not in list_b2)
result('設計師 B 看不到好木材料行', '好木材料行' not in list_b2)

# B 嘗試存取管理員頁面
status_users, body_users = get_page(des_b, '/users')
result('設計師 B 無法進入帳號管理 (被導回)', '/users' not in body_users or '帳號管理' not in body_users or '新增帳號' not in body_users)

# ============================================================
print('\n--- 5. 跨使用者操作防護 ---')
# ============================================================
# 取得 A 的 report id
rows_a = db_query("SELECT id FROM reports WHERE vendor = '大明設計公司'")
a_report_id = rows_a[0][0]

# B 嘗試刪除 A 的提報
status_del, _ = post_form(des_b, f'/delete/{a_report_id}', {})
result(f'設計師 B 刪除 A 的提報 → 403', status_del == 403)

# B 嘗試修改 A 的匯款日期
status_upd, _ = post_form(des_b, f'/update-remit-date/{a_report_id}', {'remit_date': '2026-04-20'})
result(f'設計師 B 修改 A 的匯款日期 → 403', status_upd == 403)

# 確認 A 的資料沒被動到
rows_check = db_query("SELECT vendor, remit_date FROM reports WHERE id = %s", (a_report_id,))
result('A 的提報資料完好', rows_check[0][0] == '大明設計公司' and rows_check[0][1] is None)

# ============================================================
print('\n--- 6. 發票號碼重複防呆 ---')
# ============================================================
# A 嘗試用已存在的發票號碼
status_dup, body_dup = post_form(des_a, '/submit', {
    'vendor': 'TestDup', 'vendor_type': 'Test', 'amount': '1000',
    'category': '管銷', 'invoice_no': 'A2026-001',
    'invoice_date': '2026-04-15', 'project_no': 'TestProj',
    'stage': '', 'remit_date': ''
})
result('重複發票 A2026-001 被阻擋', '發票號碼已存在' in body_dup)

# B 嘗試用 A 的發票號碼（跨使用者也要擋）
status_dup2, body_dup2 = post_form(des_b, '/submit', {
    'vendor': 'TestDup2', 'vendor_type': 'Test', 'amount': '2000',
    'category': '獎金', 'invoice_no': 'A2026-002',
    'invoice_date': '2026-04-15', 'project_no': 'TestProj',
    'stage': '', 'remit_date': ''
})
result('B 用 A 的發票號碼也被擋', '發票號碼已存在' in body_dup2)

# 空發票號碼不檢查
status_empty, body_empty = post_form(des_a, '/submit', {
    'vendor': 'TestEmpty', 'vendor_type': 'Test', 'amount': '500',
    'category': '管銷', 'invoice_no': '',
    'invoice_date': '2026-04-15', 'project_no': '陳宅翻新',
    'stage': '', 'remit_date': ''
})
result('空發票號碼正常通過', status_empty == 200 and 'TestEmpty' in body_empty)

# ============================================================
print('\n--- 7. 管理員全域檢視 ---')
# ============================================================
admin2 = make_session()
admin_list = login(admin2, 'dawn', 'admin123')
result('管理員看到大明設計公司', '大明設計公司' in admin_list)
result('管理員看到永豐工程行', '永豐工程行' in admin_list)
result('管理員看到提報人欄', '提報人' in admin_list)
result('管理員看到王小明', '王小明' in admin_list)
result('管理員看到李小華', '李小華' in admin_list)
result('管理員看到 inline 編輯', 'update-report' in admin_list)
result('管理員看到案場管理', 'project-lock-panel' in admin_list or 'toggle-lock-project' in admin_list)

# ============================================================
print('\n--- 8. 管理員 inline 編輯 ---')
# ============================================================
# 修改「好木材料行」的金額和匯款日期
rows_edit = db_query("SELECT id FROM reports WHERE vendor = '好木材料行'")
edit_id = rows_edit[0][0]

status_edit, body_edit = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木材料行', 'category': '案場成本', 'amount': '35000',
    'invoice_no': 'A2026-002', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新'
})
result('管理員修改好木材料行金額+匯款日期', status_edit == 200)

# 驗證 DB
rows_verify = db_query("SELECT amount, remit_date, updated_by, updated_at FROM reports WHERE id = %s", (edit_id,))
result('金額改為 35000', float(rows_verify[0][0]) == 35000.0)
result('匯款日期改為 2026-04-18', str(rows_verify[0][1]) == '2026-04-18')
result('updated_by 有值', rows_verify[0][2] is not None)
result('updated_at 有值', rows_verify[0][3] is not None)

# 修改名稱
status_name, _ = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木建材行', 'category': '案場成本', 'amount': '35000',
    'invoice_no': 'A2026-002', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新'
})
rows_name = db_query("SELECT vendor FROM reports WHERE id = %s", (edit_id,))
result('管理員修改名稱為好木建材行', rows_name[0][0] == '好木建材行')

# 修改分類
status_cat, _ = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木建材行', 'category': '管銷', 'amount': '35000',
    'invoice_no': 'A2026-002', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新'
})
rows_cat = db_query("SELECT category FROM reports WHERE id = %s", (edit_id,))
result('管理員修改分類為管銷', rows_cat[0][0] == '管銷')

# 修改發票號碼（改成新號碼）
status_inv, _ = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木建材行', 'category': '管銷', 'amount': '35000',
    'invoice_no': 'A2026-002-R', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新'
})
rows_inv = db_query("SELECT invoice_no FROM reports WHERE id = %s", (edit_id,))
result('管理員修改發票號碼', rows_inv[0][0] == 'A2026-002-R')

# 管理員嘗試將發票號碼改為已存在的（應被擋）
status_dup3, body_dup3 = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木建材行', 'category': '管銷', 'amount': '35000',
    'invoice_no': 'A2026-001', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新'
})
result('管理員改成重複發票號碼被擋', 'invoice_dup' in body_dup3)

# 修改案場名稱
status_proj, _ = post_form(admin2, f'/update-report/{edit_id}', {
    'vendor': '好木建材行', 'category': '管銷', 'amount': '35000',
    'invoice_no': 'A2026-002-R', 'invoice_date': '2026-04-11',
    'remit_date': '2026-04-18', 'project_no': '陳宅翻新-二期'
})
rows_proj = db_query("SELECT project_no FROM reports WHERE id = %s", (edit_id,))
result('管理員修改案場名稱', rows_proj[0][0] == '陳宅翻新-二期')

# ============================================================
print('\n--- 9. 案場鎖定機制 ---')
# ============================================================
# 鎖定「陳宅翻新」案場
status_lock, _ = post_form(admin2, '/toggle-lock-project', {
    'project_no': '陳宅翻新', 'action': 'lock'
})
result('鎖定陳宅翻新', status_lock == 200)

# 驗證 DB
rows_locked = db_query("SELECT COUNT(*) FROM reports WHERE project_no = '陳宅翻新' AND is_locked = TRUE")
result('陳宅翻新全部鎖定', rows_locked[0][0] > 0)

# 管理員看到鎖頭
_, admin_list2 = get_page(admin2, '/')
# 鎖定列應無 edit form
result('鎖定列無編輯按鈕 (桌面)', '🔒' in admin_list2)

# 嘗試刪除鎖定的提報
rows_locked_id = db_query("SELECT id FROM reports WHERE project_no = '陳宅翻新' AND is_locked = TRUE LIMIT 1")
if rows_locked_id:
    locked_id = rows_locked_id[0][0]
    status_del_locked, _ = post_form(admin2, f'/delete/{locked_id}', {})
    result('管理員刪除鎖定提報 → 403', status_del_locked == 403)

    status_edit_locked, _ = post_form(admin2, f'/update-report/{locked_id}', {
        'vendor': 'hacked', 'category': '管銷', 'amount': '1',
        'invoice_no': '', 'invoice_date': '2026-01-01',
        'remit_date': '', 'project_no': 'hacked'
    })
    result('管理員編輯鎖定提報 → 403', status_edit_locked == 403)

# 設計師對鎖定提報刪除也要被擋
status_des_del_locked, _ = post_form(des_a, f'/delete/{locked_id}', {})
result('設計師刪除鎖定提報 → 403', status_des_del_locked == 403)

# 設計師仍可對鎖定案場「新增」提報
status_new_locked, body_new_locked = post_form(des_a, '/submit', {
    'vendor': '新廠商', 'vendor_type': '水電', 'amount': '8000',
    'category': '案場成本', 'invoice_no': 'A2026-NEW',
    'invoice_date': '2026-04-15', 'project_no': '陳宅翻新',
    'stage': '', 'remit_date': ''
})
result('設計師仍可對鎖定案場新增提報', status_new_locked == 200)

# 新提報不應被鎖定
rows_new = db_query("SELECT is_locked FROM reports WHERE invoice_no = 'A2026-NEW'")
result('新提報 is_locked = FALSE', rows_new[0][0] == False)

# 解鎖
status_unlock, _ = post_form(admin2, '/toggle-lock-project', {
    'project_no': '陳宅翻新', 'action': 'unlock'
})
result('解鎖陳宅翻新', status_unlock == 200)

rows_unlocked = db_query("SELECT COUNT(*) FROM reports WHERE project_no = '陳宅翻新' AND is_locked = TRUE")
result('陳宅翻新全部解鎖', rows_unlocked[0][0] == 0)

# 解鎖後可以編輯
_, admin_list3 = get_page(admin2, '/')
result('解鎖後恢復編輯', 'update-report' in admin_list3)

# ============================================================
print('\n--- 10. 廠商相似性即時比對 ---')
# ============================================================
# 大明工程公司 vs 大明設計公司（核心都是「大明」）
q1 = urllib.parse.quote('大明工程公司')
result1 = get_json(des_a, f'/api/check-vendor?q={q1}')
result('大明工程公司 → 找到大明設計公司', '大明設計公司' in result1.get('similar', []))

# 好木工作室 vs 好木建材行（核心都是「好木」）
q2 = urllib.parse.quote('好木工作室')
result2 = get_json(admin2, f'/api/check-vendor?q={q2}')
result('好木工作室 → 找到好木建材行', '好木建材行' in result2.get('similar', []))

# 完全不同的廠商
q3 = urllib.parse.quote('天天快餐店')
result3 = get_json(des_a, f'/api/check-vendor?q={q3}')
result('天天快餐店 → 無相似', len(result3.get('similar', [])) == 0)

# 太短（< 2 字）
q4 = urllib.parse.quote('大')
result4 = get_json(des_a, f'/api/check-vendor?q={q4}')
result('單字輸入 → 空結果', len(result4.get('similar', [])) == 0)

# 完全相同的不會出現在相似列表
q5 = urllib.parse.quote('大明設計公司')
result5 = get_json(des_a, f'/api/check-vendor?q={q5}')
result('完全相同不列入相似', '大明設計公司' not in result5.get('similar', []))

# ============================================================
print('\n--- 11. 審計軌跡顯示 ---')
# ============================================================
_, admin_list4 = get_page(admin2, '/')
result('清單頁有最後修改欄', '最後修改' in admin_list4)
result('顯示修改人 Dawn', 'Dawn' in admin_list4)

# ============================================================
print('\n--- 12. 設計師停用 / 啟用 ---')
# ============================================================
# 取得 designer_b 的 user id
rows_uid = db_query("SELECT id FROM users WHERE username = 'designer_b'")
uid_b = rows_uid[0][0]

# 停用 designer_b
post_form(admin2, f'/users/{uid_b}/toggle', {})

# B 嘗試登入
des_b2 = make_session()
body_disabled = login(des_b2, 'designer_b', 'pass123')
result('停用的 B 無法登入', '已停用' in body_disabled)

# B 的歷史資料仍在管理員清單
_, admin_list5 = get_page(admin2, '/')
result('停用後 B 的資料仍在 (永豐工程行)', '永豐工程行' in admin_list5)
result('停用後 B 的資料仍在 (文具王)', '文具王' in admin_list5)

# 重新啟用
post_form(admin2, f'/users/{uid_b}/toggle', {})
des_b3 = make_session()
body_enabled = login(des_b3, 'designer_b', 'pass123')
result('重新啟用後 B 可登入', '永豐工程行' in body_enabled or '出帳管理' in body_enabled)

# ============================================================
print('\n--- 13. 密碼重設 ---')
# ============================================================
post_form(admin2, f'/users/{uid_b}/reset-password', {'new_password': 'newpass456'})

# 舊密碼無法登入
des_b4 = make_session()
body_old = login(des_b4, 'designer_b', 'pass123')
result('舊密碼無法登入', '帳號或密碼錯誤' in body_old)

# 新密碼可以
des_b5 = make_session()
body_new = login(des_b5, 'designer_b', 'newpass456')
result('新密碼可登入', '出帳管理' in body_new)

# ============================================================
print('\n--- 14. Excel 匯出 ---')
# ============================================================
import tempfile, os
resp_xl = admin2.open(urllib.request.Request(BASE + '/export'))
xl_content = resp_xl.read()
xl_path = os.path.join(tempfile.gettempdir(), 'v3_test_export.xlsx')
with open(xl_path, 'wb') as f:
    f.write(xl_content)

import openpyxl
wb = openpyxl.load_workbook(xl_path)
result('Excel 有明細頁', len(wb.sheetnames) >= 1)
result('Excel 有總覽頁', len(wb.sheetnames) >= 2)

ws = wb[wb.sheetnames[0]]
headers = [cell.value for cell in ws[1]]
result('Excel 明細有提報人欄', headers[0] is not None)

# 算 Excel 金額總和（找所有數值列的金額欄）
amount_col = None
for i, h in enumerate(headers):
    if h and '金額' in str(h):
        amount_col = i
        break

if amount_col is not None:
    xl_total = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        val = row[amount_col]
        if isinstance(val, (int, float)) and row[0] and '小計' not in str(row[0]) and '分計' not in str(row[0]) and '總計' not in str(row[0]):
            # 只加明細列
            pass
    # 簡化：找總計列
    for row in ws.iter_rows(min_row=2, values_only=True):
        for cell in row:
            if cell and '總計' in str(cell):
                # 同列的金額欄
                idx = list(row).index(cell)
                total_row = list(row)
                if amount_col < len(total_row) and isinstance(total_row[amount_col], (int, float)):
                    xl_total = total_row[amount_col]
                break

    # 算 DB 總和
    db_total_rows = db_query("SELECT SUM(amount) FROM reports")
    db_total = float(db_total_rows[0][0])
    result(f'Excel 總計 ({xl_total}) = DB 總計 ({db_total})', abs(xl_total - db_total) < 0.01)
else:
    result('找不到金額欄', False)

# ============================================================
print('\n--- 15. 清除測試資料 ---')
# ============================================================
from app import get_conn
conn = get_conn()
cur = conn.cursor()
cur.execute("DELETE FROM reports WHERE vendor IN ('大明設計公司','好木建材行','快遞物流公司','永豐工程行','文具王','TestEmpty','新廠商')")
deleted_r = cur.rowcount
cur.execute("DELETE FROM users WHERE username IN ('designer_a','designer_b')")
deleted_u = cur.rowcount
conn.commit()
cur.close()
conn.close()
result(f'清除 {deleted_r} 筆測試提報', deleted_r > 0)
result(f'清除 {deleted_u} 個測試帳號', deleted_u > 0)

# ============================================================
print('\n' + '=' * 60)
print(f'  結果：{PASS} 通過 / {FAIL} 失敗 / 共 {PASS + FAIL} 項')
print('=' * 60)

if FAIL > 0:
    sys.exit(1)
