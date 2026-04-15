# 出帳管理系統 V3｜系統設計文件 SDD

**版本:** v3.0
**對應 PRD:** prdv3.md v3.0
**前置:** V2 已部署（認證 + 資料隔離 + 帳號管理 + 403 防護）
**核心目標:** 發票防呆 + 案場鎖定 + 管理員全欄位編輯 + 廠商相似比對 + 審計軌跡

---

## 1. 技術棧變更

| 項目 | V2 | V3 變更 |
|------|-----|---------|
| 前端 JS | 無 | 新增 `static/app.js`（debounce + AJAX 廠商比對） |
| API 格式 | 純 HTML form | 新增 JSON API（`/api/check-vendor`） |
| 依賴新增 | — | 無新套件（Flask 內建 `jsonify`） |
| 環境變數新增 | — | 無 |

`requirements.txt` 不需要變更。

---

## 2. 資料庫變更

### 2.1 reports 表新增欄位

```sql
ALTER TABLE reports ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE reports ADD COLUMN updated_by INTEGER REFERENCES users(id);
ALTER TABLE reports ADD COLUMN updated_at TIMESTAMP;
```

### 2.2 新建 vendor_keywords 表

```sql
CREATE TABLE vendor_keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO vendor_keywords (keyword) VALUES
    ('公司'), ('行'), ('工作室'), ('企業'), ('設計'), ('工程'),
    ('有限'), ('股份'), ('實業'), ('工坊');
```

### 2.3 遷移腳本

```python
# migrate_v3.py — 執行一次
from app import get_conn

def migrate():
    conn = get_conn()
    cur = conn.cursor()

    # reports 加欄位
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            is_locked BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            updated_by INTEGER REFERENCES users(id);
    """)
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            updated_at TIMESTAMP;
    """)

    # vendor_keywords 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendor_keywords (
            id SERIAL PRIMARY KEY,
            keyword VARCHAR(50) NOT NULL UNIQUE
        );
    """)
    for kw in ['公司', '行', '工作室', '企業', '設計', '工程',
               '有限', '股份', '實業', '工坊']:
        cur.execute("""
            INSERT INTO vendor_keywords (keyword) VALUES (%s)
            ON CONFLICT (keyword) DO NOTHING;
        """, (kw,))

    conn.commit()
    cur.close()
    conn.close()
    print('V3 migration done')

if __name__ == '__main__':
    migrate()
```

---

## 3. 路由設計

### 3.1 路由總覽（V3 新增 / 修改）

| 方法 | 路徑 | 功能 | 權限 | 狀態 |
|------|------|------|------|------|
| POST | `/submit` | 寫入提報 | 登入 | **修改：加發票防呆** |
| GET | `/` | 清單頁 | 登入 | **修改：管理員 inline 編輯 + 鎖定 UI** |
| POST | `/update-report/<id>` | 全欄位更新 | admin | **新增** |
| POST | `/toggle-lock-project` | 鎖定/解鎖案場 | admin | **新增** |
| GET | `/api/check-vendor` | 廠商相似比對 | 登入 | **新增** |
| POST | `/delete/<id>` | 刪除提報 | 登入 | **修改：鎖定檢查** |

既有路由（login / logout / new / export / users 系列）不變。

### 3.2 POST /submit — 發票防呆

在現有驗證邏輯後、INSERT 之前加入：

```python
# 發票號碼重複檢查
if invoice_no:
    cur.execute("SELECT id FROM reports WHERE invoice_no = %s", (invoice_no,))
    if cur.fetchone():
        errors.append('此發票號碼已存在，請確認是否重複請款')
```

案場鎖定不影響新增（PRD 確認），故 submit 不做鎖定檢查。

### 3.3 POST /update-report/<id> — 管理員全欄位更新

```python
@app.route('/update-report/<int:report_id>', methods=['POST'])
@admin_required
def update_report(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    # 檢查是否鎖定
    cur.execute("SELECT is_locked FROM reports WHERE id = %s", (report_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)
    if row[0]:  # is_locked = True
        cur.close(); conn.close()
        abort(403)

    # 取表單值
    vendor = request.form.get('vendor', '').strip()
    category = request.form.get('category', '').strip()
    amount = request.form.get('amount', '').strip()
    invoice_no = request.form.get('invoice_no', '').strip() or None
    invoice_date = request.form.get('invoice_date', '').strip()
    remit_date = request.form.get('remit_date', '').strip() or None
    project_no = request.form.get('project_no', '').strip()

    # 發票防呆（排除自己）
    if invoice_no:
        cur.execute(
            "SELECT id FROM reports WHERE invoice_no = %s AND id != %s",
            (invoice_no, report_id)
        )
        if cur.fetchone():
            cur.close(); conn.close()
            # 回到清單頁並帶錯誤訊息（用 flash 或 query param）
            return redirect('/?error=invoice_dup')

    # 更新
    cur.execute("""
        UPDATE reports
        SET vendor = %s, category = %s, amount = %s,
            invoice_no = %s, invoice_date = %s, remit_date = %s,
            project_no = %s, updated_by = %s, updated_at = NOW()
        WHERE id = %s
    """, (vendor, category, amount, invoice_no, invoice_date,
          remit_date, project_no, user['id'], report_id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

### 3.4 POST /toggle-lock-project — 案場鎖定切換

```python
@app.route('/toggle-lock-project', methods=['POST'])
@admin_required
def toggle_lock_project():
    project_no = request.form.get('project_no', '').strip()
    action = request.form.get('action', '').strip()  # 'lock' or 'unlock'

    if not project_no or action not in ('lock', 'unlock'):
        return redirect('/')

    lock_value = True if action == 'lock' else False

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE reports SET is_locked = %s WHERE project_no = %s",
        (lock_value, project_no)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

### 3.5 GET /api/check-vendor — 廠商相似比對

```python
from flask import jsonify

@app.route('/api/check-vendor')
@login_required
def check_vendor():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'similar': []})

    conn = get_conn()
    cur = conn.cursor()

    # 取關鍵字清單
    cur.execute("SELECT keyword FROM vendor_keywords")
    keywords = [row[0] for row in cur.fetchall()]

    # 從輸入中移除關鍵字，得到核心名稱
    core = q
    for kw in keywords:
        core = core.replace(kw, '')
    core = core.strip()

    if not core:
        cur.close(); conn.close()
        return jsonify({'similar': []})

    # 查所有不同的廠商名稱
    cur.execute("SELECT DISTINCT vendor FROM reports WHERE vendor != %s", (q,))
    vendors = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    # 比對核心名稱
    similar = []
    for v in vendors:
        v_core = v
        for kw in keywords:
            v_core = v_core.replace(kw, '')
        v_core = v_core.strip()
        if v_core and core and (v_core == core or core in v_core or v_core in core):
            similar.append(v)

    return jsonify({'similar': similar})
```

### 3.6 POST /delete/<id> — 鎖定檢查

在現有的 SELECT 權限檢查後，加入鎖定檢查：

```python
@app.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    # 取得該筆報告
    cur.execute("SELECT user_id, is_locked FROM reports WHERE id = %s", (report_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)

    # 鎖定檢查
    if row[1]:  # is_locked
        cur.close(); conn.close()
        abort(403)

    # 權限檢查（設計師只能刪自己的）
    if user['role'] == 'designer' and row[0] != user['id']:
        cur.close(); conn.close()
        abort(403)

    cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

### 3.7 GET / — 清單頁查詢調整

管理員版 SELECT 新增 `is_locked`, `updated_by`, `updated_at` 欄位：

```sql
-- 管理員
SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
       r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
       r.stage, r.created_at, u.display_name,
       r.is_locked, r.updated_by, r.updated_at, u2.display_name as updater_name
FROM reports r
JOIN users u ON r.user_id = u.id
LEFT JOIN users u2 ON r.updated_by = u2.id
ORDER BY r.invoice_date DESC, r.created_at DESC

-- 設計師
SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
       r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
       r.stage, r.created_at, NULL as display_name,
       r.is_locked, NULL as updated_by, NULL as updated_at, NULL as updater_name
FROM reports r
WHERE r.user_id = %s
ORDER BY r.invoice_date DESC, r.created_at DESC
```

同時查詢案場鎖定狀態（供案場管理區塊用）：

```sql
SELECT project_no, bool_or(is_locked) as any_locked, COUNT(*) as cnt
FROM reports
GROUP BY project_no
ORDER BY project_no
```

---

## 4. 前端設計

### 4.1 新增 static/app.js

```javascript
// 廠商相似性即時比對
(function() {
    const vendorInput = document.getElementById('vendor');
    const hintBox = document.getElementById('vendor-hint');
    if (!vendorInput || !hintBox) return;

    let timer = null;

    vendorInput.addEventListener('input', function() {
        clearTimeout(timer);
        const q = this.value.trim();
        if (q.length < 2) {
            hintBox.style.display = 'none';
            return;
        }
        timer = setTimeout(function() {
            fetch('/api/check-vendor?q=' + encodeURIComponent(q))
                .then(r => r.json())
                .then(data => {
                    if (data.similar && data.similar.length > 0) {
                        hintBox.textContent =
                            '系統中已有相似廠商：' + data.similar.join('、') +
                            '。是否為同一廠商？';
                        hintBox.style.display = 'block';
                    } else {
                        hintBox.style.display = 'none';
                    }
                })
                .catch(() => { hintBox.style.display = 'none'; });
        }, 300);
    });
})();
```

### 4.2 templates/new.html 修改

名稱輸入框下方新增提醒容器：

```html
<div class="form-group">
    <label for="vendor">名稱 <span class="required">*</span></label>
    <input type="text" id="vendor" name="vendor" required ...>
    <div id="vendor-hint" class="vendor-hint" style="display:none;"></div>
</div>
```

頁尾引入 JS：
```html
<script src="/static/app.js"></script>
```

### 4.3 templates/list.html — 管理員 inline 編輯

**桌面版表格（管理員）：**

每個儲存格變為 `<form>` 內的輸入框，一列共用一個 form：

```html
{% for r in reports %}
<tr class="{{ 'row-locked' if r.is_locked else '' }}">
    {% if user.role == 'admin' %}<td>{{ r.reporter }}</td>{% endif %}
    <td>
        {% if r.is_locked %}
            🔒 {{ r.remit_date or '-' }}
        {% else %}
            <form method="POST" action="/update-report/{{ r.id }}" class="inline-edit-form">
                <!-- 所有欄位都在同一個 form 裡 -->
                ...每個 td 內放對應 input...
            </form>
        {% endif %}
    </td>
    ...
</tr>
{% endfor %}
```

實作策略：每列一個 `<form>`，跨越多個 `<td>`。由於 HTML 規範 form 不能跨 td，改用以下方式：

```html
<tr>
    <td>
        <input form="edit-{{ r.id }}" type="text" name="vendor" value="{{ r.vendor }}">
    </td>
    <td>
        <input form="edit-{{ r.id }}" type="date" name="remit_date" value="{{ r.remit_date or '' }}">
    </td>
    <!-- ... 其他欄位同理 ... -->
    <td>
        <form id="edit-{{ r.id }}" method="POST" action="/update-report/{{ r.id }}">
            <button type="submit" class="btn-save">儲存</button>
        </form>
        {% if not r.is_locked %}
        <form method="POST" action="/delete/{{ r.id }}" onsubmit="return confirm('確定要刪除？')">
            <button type="submit" class="btn-delete">刪除</button>
        </form>
        {% endif %}
    </td>
</tr>
```

**鎖定列（管理員）：** 所有 input 替換為純文字 + 鎖頭 icon，無儲存/刪除按鈕。

**設計師版：** 維持現有純文字卡片/表格，無 inline 編輯。鎖定列額外顯示 🔒 標記。

**手機版卡片（管理員）：** 同桌面邏輯，卡片內每個值改為 input 欄位，底部一個儲存按鈕。鎖定時顯示純文字。

### 4.4 案場管理區塊

清單頁頂部（管理員限定），在 actions 按鈕下方新增可展開的「案場管理」區塊：

```html
{% if user.role == 'admin' %}
<details class="project-lock-panel">
    <summary>案場管理（鎖定 / 解鎖）</summary>
    <div class="project-list">
        {% for p in projects %}
        <div class="project-item">
            <span>{{ p.project_no }}（{{ p.cnt }} 筆）</span>
            <form method="POST" action="/toggle-lock-project" class="inline-form">
                <input type="hidden" name="project_no" value="{{ p.project_no }}">
                {% if p.any_locked %}
                    <input type="hidden" name="action" value="unlock">
                    <button type="submit" class="btn-small btn-success">🔓 解鎖</button>
                {% else %}
                    <input type="hidden" name="action" value="lock">
                    <button type="submit" class="btn-small btn-danger">🔒 鎖定</button>
                {% endif %}
            </form>
        </div>
        {% endfor %}
    </div>
</details>
{% endif %}
```

### 4.5 審計軌跡顯示

**桌面版表格：** 最後一欄新增「最後修改」：

```html
<td class="text-muted">
    {% if r.updater_name %}
        {{ r.updater_name }} · {{ r.updated_at.strftime('%m/%d %H:%M') }}
    {% else %}
        —
    {% endif %}
</td>
```

**手機版卡片：** 卡片底部：

```html
{% if r.updater_name %}
<div class="card-footer text-muted">
    最後修改：{{ r.updater_name }} · {{ r.updated_at.strftime('%m/%d %H:%M') }}
</div>
{% endif %}
```

---

## 5. CSS 新增樣式

```css
/* 廠商相似提醒 */
.vendor-hint {
    background: #FFF3E0;
    color: #E65100;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 0.85rem;
    margin-top: 6px;
    border-left: 3px solid #FF9800;
}

/* 鎖定列 */
.row-locked {
    background: #FAFAFA;
}

.row-locked td {
    color: #999;
}

/* 案場管理面板 */
.project-lock-panel {
    background: #fff;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.project-lock-panel summary {
    cursor: pointer;
    font-weight: 600;
    font-size: 0.95rem;
    color: #444;
}

.project-list {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.project-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    background: #f9f9f9;
    border-radius: 6px;
}

/* inline 編輯輸入框（桌面表格） */
.inline-edit-input {
    padding: 4px 6px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.85rem;
    background: #fafafa;
}

.inline-edit-input:focus {
    border-color: #4A90D9;
    background: #fff;
    outline: none;
}

.inline-edit-input[type="number"] {
    width: 90px;
}

.inline-edit-input[type="date"] {
    width: 140px;
}

.inline-edit-input[type="text"] {
    width: 120px;
}

/* 分類下拉 */
.inline-edit-select {
    padding: 4px 6px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.85rem;
    background: #fafafa;
}

/* 錯誤提示條 */
.error-banner {
    background: #FFEBEE;
    color: #C62828;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 0.9rem;
}

/* 卡片底部審計資訊 */
.card-footer {
    padding-top: 8px;
    border-top: 1px solid #f0f0f0;
    margin-top: 8px;
    font-size: 0.8rem;
}
```

---

## 6. 錯誤處理

### 6.1 發票重複（清單頁 inline 編輯）

`/update-report/<id>` 發票重複時 redirect 帶 query param：

```python
return redirect('/?error=invoice_dup')
```

清單頁模板頂部：

```html
{% if request.args.get('error') == 'invoice_dup' %}
<div class="error-banner">發票號碼重複，請確認是否重複請款。</div>
{% endif %}
```

### 6.2 鎖定狀態操作

- 管理員嘗試編輯鎖定列 → abort(403)
- 任何人嘗試刪除鎖定列 → abort(403)
- 前端已隱藏按鈕，403 為後端防線

---

## 7. 安全設計

| 威脅 | 防禦 |
|------|------|
| 設計師偽造 report_id 刪除他人提報 | SELECT 前查 user_id + abort(403)（V2 已做） |
| 設計師偽造 report_id 編輯他人提報 | `/update-report` 僅 admin_required |
| 繞過前端直接 POST 修改鎖定列 | 後端 SELECT is_locked + abort(403) |
| 重複發票號碼 | INSERT / UPDATE 前 SELECT 檢查 |
| XSS（廠商比對回傳） | JSON API 回傳，前端用 textContent（不用 innerHTML） |
| SQL Injection | 全部用 %s 參數化查詢（V1 已確立） |

---

## 8. 檔案異動清單

| 檔案 | 異動 |
|------|------|
| `migrate_v3.py` | 新增：DB 遷移腳本 |
| `app.py` | 修改：新增 3 個路由、修改 3 個路由、新增 jsonify import |
| `static/app.js` | 新增：廠商相似性 debounce + AJAX |
| `static/style.css` | 修改：新增 vendor-hint、row-locked、project-lock-panel、inline-edit 等樣式 |
| `templates/list.html` | 修改：管理員 inline 編輯、案場管理區塊、鎖定 UI、審計顯示、錯誤提示 |
| `templates/new.html` | 修改：廠商相似提醒 UI、引入 app.js |
| `templates/base.html` | 不改 |
| `templates/login.html` | 不改 |
| `templates/users.html` | 不改 |

---

## 9. 開發順序對應 PRD Phase

| Phase | 內容 | 涉及檔案 | 驗收項 |
|-------|------|---------|--------|
| 1 | DB 遷移 | migrate_v3.py | — |
| 2 | 發票防呆 | app.py, templates/new.html | 3, 4, 5 |
| 3 | 案場鎖定 | app.py, templates/list.html, style.css | 6, 7, 8, 9 |
| 4 | 管理員 inline 編輯 | app.py, templates/list.html, style.css | 10, 11, 12 |
| 5 | 廠商相似比對 | app.py, static/app.js, templates/new.html, style.css | 13, 14, 15 |
| 6 | 審計顯示 + 報表驗證 | templates/list.html | 16, 17 |
| 7 | 部署 + 驗收 | — | 全部 17 項 |
