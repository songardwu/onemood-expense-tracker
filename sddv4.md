# SDD V4 — 廠商匯款資料管理（系統設計文件）

## 1. DB Migration

### 1.1 新增 vendors 表

```sql
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    bank_name VARCHAR(200) NOT NULL,
    bank_code VARCHAR(50) NOT NULL,
    account_no VARCHAR(50) NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP
);
```

### 1.2 修改 reports 表

```sql
ALTER TABLE reports ADD COLUMN payment_method VARCHAR(20);
```

> 既有資料 payment_method 為 NULL，新提報為必填。

---

## 2. 路由總覽

| 方法 | 路由 | 權限 | 說明 |
|------|------|------|------|
| GET | /vendors | login_required | 廠商清單頁 |
| POST | /vendors/create | login_required | 新增單筆廠商 |
| POST | /vendors/update/\<id\> | admin_required | 修改廠商 |
| POST | /vendors/delete/\<id\> | admin_required | 刪除廠商 |
| GET | /vendors/template | login_required | 下載匯入範本 |
| POST | /vendors/import | login_required | 批次匯入 |

---

## 3. 廠商管理頁（/vendors）

### 3.1 Template: vendors.html

```
頁面結構：
┌─────────────────────────────────────┐
│ 廠商匯款資料                    [← 回清單] │
│ [+ 新增廠商] [匯入] [下載範本]           │
├─────────────────────────────────────┤
│ 桌面版 table / 手機版 cards              │
│ 欄位：名稱│銀行分行│銀行代碼│帳號│戶名│操作  │
│ admin: inline 編輯 + 刪除按鈕            │
│ designer: 純文字顯示                     │
└─────────────────────────────────────┘
```

### 3.2 GET /vendors

```python
@app.route('/vendors')
@login_required
def vendor_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.id, v.name, v.bank_name, v.bank_code,
               v.account_no, v.account_name
        FROM vendors v
        ORDER BY v.name
    """)
    vendors = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('vendors.html', vendors=vendors, user=user)
```

### 3.3 POST /vendors/create

```python
@app.route('/vendors/create', methods=['POST'])
@login_required
def vendor_create():
    user = get_current_user()
    name = request.form.get('name', '').strip()
    bank_name = request.form.get('bank_name', '').strip()
    bank_code = request.form.get('bank_code', '').strip()
    account_no = request.form.get('account_no', '').strip()
    account_name = request.form.get('account_name', '').strip()

    if not all([name, bank_name, bank_code, account_no, account_name]):
        return redirect('/vendors?error=missing')

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendors (name, bank_name, bank_code, account_no,
                                 account_name, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, bank_name, bank_code, account_no, account_name, user['id']))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return redirect('/vendors?error=duplicate')
    finally:
        cur.close()
        conn.close()
    return redirect('/vendors')
```

### 3.4 POST /vendors/update/\<id\> (admin only)

```python
@app.route('/vendors/update/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_update(vendor_id):
    user = get_current_user()
    # 取 form 欄位，驗證必填
    # UPDATE vendors SET ... updated_by, updated_at = NOW() WHERE id = %s
    # 名稱重複 → catch UniqueViolation → redirect ?error=duplicate
```

### 3.5 POST /vendors/delete/\<id\> (admin only)

```python
@app.route('/vendors/delete/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_delete(vendor_id):
    # DELETE FROM vendors WHERE id = %s
```

---

## 4. 批次匯入（/vendors/import）

### 4.1 上傳處理

```python
@app.route('/vendors/import', methods=['POST'])
@login_required
def vendor_import():
    user = get_current_user()
    file = request.files.get('file')
    if not file:
        return redirect('/vendors?error=nofile')

    filename = file.filename.lower()
    if filename.endswith('.xlsx'):
        df = pd.read_excel(file, dtype=str)
    elif filename.endswith('.csv'):
        df = pd.read_csv(file, dtype=str)
    else:
        return redirect('/vendors?error=badformat')

    # 欄位對應（支援中英文表頭）
    col_map = {
        '名稱': 'name', '廠商名稱': 'name',
        '銀行分行名稱': 'bank_name', '銀行分行': 'bank_name',
        '銀行代碼': 'bank_code',
        '帳號': 'account_no', '銀行帳號': 'account_no',
        '戶名': 'account_name',
    }
    df.rename(columns=col_map, inplace=True)

    required = ['name', 'bank_name', 'bank_code', 'account_no', 'account_name']
    # 驗證欄位存在

    added = 0; skipped = 0; updated = 0; errors = []

    for idx, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        # ... 驗證必填

        # 查是否已存在
        cur.execute("SELECT id FROM vendors WHERE name = %s", (name,))
        existing = cur.fetchone()

        if existing:
            if user['role'] == 'admin':
                # 覆蓋更新
                cur.execute("UPDATE vendors SET ... WHERE id = %s")
                updated += 1
            else:
                skipped += 1  # 設計師跳過
        else:
            cur.execute("INSERT INTO vendors ...")
            added += 1

    # 回傳結果頁
    return render_template('vendors.html', ...,
        import_result={'added': added, 'updated': updated,
                       'skipped': skipped, 'errors': errors})
```

### 4.2 範本下載

```python
@app.route('/vendors/template')
@login_required
def vendor_template():
    df = pd.DataFrame(columns=['名稱', '銀行分行名稱', '銀行代碼', '帳號', '戶名'])
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='廠商匯款資料範本.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
```

---

## 5. 提報頁連結

### 5.1 /new 頁面修改

- 新增 radio group「匯款方式」：現金 / 公司轉帳 / 個帳轉帳（required）
- vendor input 的 `input` 事件（已有 debounce）加入銀行資訊查詢

### 5.2 新增 API：GET /api/vendor-bank?name=xxx

```python
@app.route('/api/vendor-bank')
@login_required
def vendor_bank():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({})
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT bank_name, bank_code, account_no, account_name
        FROM vendors WHERE name = %s
    """, (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return jsonify({
            'bank_name': row[0], 'bank_code': row[1],
            'account_no': row[2], 'account_name': row[3]
        })
    return jsonify({})
```

### 5.3 app.js 擴充

```javascript
// vendor input change/blur → fetch /api/vendor-bank?name=...
// 若有結果 → 顯示銀行資訊提示框（唯讀）
vendorInput.addEventListener('change', function() {
    var name = this.value.trim();
    if (!name) { bankBox.style.display = 'none'; return; }
    fetch('/api/vendor-bank?name=' + encodeURIComponent(name))
        .then(r => r.json())
        .then(data => {
            if (data.bank_name) {
                bankBox.innerHTML = '銀行：' + data.bank_name +
                    '（' + data.bank_code + '）<br>帳號：' +
                    data.account_no + '　戶名：' + data.account_name;
                bankBox.style.display = 'block';
            } else {
                bankBox.style.display = 'none';
            }
        });
});
```

### 5.4 /submit 修改

```python
payment_method = request.form.get('payment_method', '').strip()
# 驗證
if payment_method not in ('現金', '公司轉帳', '個帳轉帳'):
    errors.append('匯款方式必須為現金、公司轉帳或個帳轉帳')
# INSERT 加入 payment_method
```

---

## 6. 清單頁修改

### 6.1 index() 查詢加入 payment_method

```sql
SELECT r.id, r.vendor, ..., r.payment_method, ...
```

> payment_method 放在 r[16]（新欄位加在最後）

### 6.2 list.html

- 桌面表格新增「匯款方式」欄
- admin inline：`<select>` 含現金/公司轉帳/個帳轉帳 + 空白選項（相容舊資料）
- 手機卡片同步新增
- designer 版純文字顯示

### 6.3 /update-report 加入 payment_method

```python
payment_method = request.form.get('payment_method', '').strip()
if payment_method and payment_method not in ('現金', '公司轉帳', '個帳轉帳'):
    # 驗證失敗
# UPDATE SET ... payment_method = %s ...
```

---

## 7. Excel 匯出合併

### 7.1 查詢修改

```sql
SELECT ..., r.payment_method,
       v.bank_name, v.bank_code, v.account_no, v.account_name
FROM reports r
JOIN users u ON r.user_id = u.id
LEFT JOIN vendors v ON r.vendor = v.name
ORDER BY ...
```

### 7.2 明細表新增欄位

```python
col_map 新增：
'payment_method': '匯款方式',
'bank_name': '銀行分行名稱',
'bank_code': '銀行代碼',
'account_no': '銀行帳號',
'account_name': '戶名',
```

---

## 8. 安全考量

- vendors/update、vendors/delete 限 admin_required
- 批次匯入：設計師遇到重複名稱只能跳過，不可覆蓋
- payment_method 白名單驗證
- 所有輸入 strip() 處理
- 檔案上傳限制：只接受 .xlsx / .csv

---

## 9. 檔案異動清單

| 檔案 | 異動 |
|------|------|
| migrate_v4.py | 新增，DB migration |
| app.py | 新增 7 個路由，修改 3 個路由 |
| templates/vendors.html | 新增，廠商管理頁 |
| templates/new.html | 新增匯款方式 radio + 銀行資訊提示 |
| templates/list.html | 新增匯款方式欄位 |
| static/app.js | 擴充銀行資訊查詢 |
| static/style.css | 廠商頁 + 匯入結果樣式 |
