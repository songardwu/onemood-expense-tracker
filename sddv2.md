# 出帳管理系統 V2｜系統設計文件 SDD

**版本:** v2.0
**對應 PRD:** prdv2.md v2.0
**前置:** V1 MVP 已部署於 Vercel，資料庫為 Neon Postgres
**核心目標:** 帳號系統 + 資料隔離 + 管理員全域權限

---

## 1. 技術棧變更

| 項目 | V1 | V2 變更 |
|------|-----|---------|
| 認證 | 無 | Flask session（signed cookie） |
| 密碼 | 無 | werkzeug.security（scrypt/pbkdf2） |
| 角色 | 無 | designer / admin |
| 依賴新增 | — | 無新套件，werkzeug 已含於 Flask |
| 環境變數新增 | — | `SECRET_KEY`（session 簽名用） |

`requirements.txt` 不需要變更。

---

## 2. 資料庫變更

### 2.1 新增 `users` 表

```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('designer', 'admin')),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 修改 `reports` 表

```sql
ALTER TABLE reports ADD COLUMN user_id INTEGER REFERENCES users(id);
```

### 2.3 資料遷移（migration script）

```python
# migrate_v2.py — 執行一次
# 1. 建 users 表
# 2. 插入初始管理員帳號（Onemood）
# 3. reports 加 user_id 欄位
# 4. 既有 reports 全部歸屬 Onemood (user_id = 1)
# 5. user_id 設為 NOT NULL

from werkzeug.security import generate_password_hash

def migrate():
    conn = get_conn()
    cur = conn.cursor()

    # 建 users 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('designer', 'admin')),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 插入初始管理員
    pw_hash = generate_password_hash('admin123')
    cur.execute("""
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES ('onemood', 'Onemood', %s, 'admin')
        ON CONFLICT (username) DO NOTHING;
    """, (pw_hash,))

    # reports 加 user_id
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
    """)

    # 既有資料歸屬 Onemood
    cur.execute("UPDATE reports SET user_id = 1 WHERE user_id IS NULL;")

    # 設 NOT NULL
    cur.execute("ALTER TABLE reports ALTER COLUMN user_id SET NOT NULL;")

    conn.commit()
    cur.close()
    conn.close()
```

---

## 3. 認證機制

### 3.1 Session 設定

```python
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.permanent_session_lifetime = timedelta(days=7)
```

登入成功後寫入 session：
```python
session.permanent = True
session['user_id'] = user_id
session['role'] = role
session['display_name'] = display_name
```

### 3.2 取得目前使用者

```python
def get_current_user():
    """從 session 取得目前使用者，回傳 dict 或 None"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return {
        'id': user_id,
        'role': session.get('role'),
        'display_name': session.get('display_name'),
    }
```

### 3.3 裝飾器

```python
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect('/login')
        if user['role'] != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return decorated
```

---

## 4. 路由設計

### 4.1 路由總覽

| 方法 | 路徑 | 功能 | 權限 |
|------|------|------|------|
| GET | `/login` | 登入頁面 | 公開 |
| POST | `/login` | 登入驗證 | 公開 |
| GET | `/logout` | 登出 | 登入 |
| GET | `/` | 清單頁 | 登入（設計師看自己，管理員看全部） |
| GET | `/new` | 新增提報表單 | 登入 |
| POST | `/submit` | 寫入提報 | 登入（自動帶 user_id） |
| POST | `/delete/<id>` | 刪除提報 | 登入（設計師只能刪自己的） |
| POST | `/update-remit-date/<id>` | 修改匯款日期 | 登入（設計師只能改自己的） |
| GET | `/export` | 匯出 Excel | 登入（設計師只匯自己的） |
| GET | `/users` | 帳號管理頁 | admin |
| POST | `/users/create` | 新增帳號 | admin |
| POST | `/users/<id>/toggle` | 啟用/停用帳號 | admin |
| POST | `/users/<id>/reset-password` | 重設密碼 | admin |

### 4.2 認證路由

#### `GET /login` — 登入頁

```python
@app.route('/login', methods=['GET'])
def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')
```

#### `POST /login` — 登入驗證

```python
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, display_name, password_hash, role, is_active
        FROM users WHERE username = %s
    """, (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not check_password_hash(row[2], password):
        return render_template('login.html', error='帳號或密碼錯誤')

    if not row[4]:  # is_active = False
        return render_template('login.html', error='此帳號已停用，請聯繫管理員')

    session.permanent = True
    session['user_id'] = row[0]
    session['display_name'] = row[1]
    session['role'] = row[3]
    return redirect('/')
```

#### `GET /logout` — 登出

```python
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
```

### 4.3 修改既有路由 — 資料隔離

#### `GET /` — 清單頁（加權限過濾）

```python
@app.route('/')
@login_required
def index():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    if user['role'] == 'admin':
        cur.execute("""
            SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
                   r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
                   r.stage, r.created_at, u.display_name
            FROM reports r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.invoice_date DESC, r.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
                   r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
                   r.stage, r.created_at, NULL as display_name
            FROM reports r
            WHERE r.user_id = %s
            ORDER BY r.invoice_date DESC, r.created_at DESC
        """, (user['id'],))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('list.html', reports=rows, user=user)
```

#### `POST /submit` — 寫入提報（自動帶 user_id）

INSERT 語句新增 `user_id` 欄位，值為 `session['user_id']`。

#### `POST /delete/<id>` — 刪除（權限檢查）

```python
@app.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    # 設計師：只能刪自己的
    if user['role'] == 'designer':
        cur.execute("DELETE FROM reports WHERE id = %s AND user_id = %s",
                    (report_id, user['id']))
    else:
        cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

#### `POST /update-remit-date/<id>` — 修改匯款日期（權限檢查）

```python
@app.route('/update-remit-date/<int:report_id>', methods=['POST'])
@login_required
def update_remit_date(report_id):
    user = get_current_user()
    remit_date = request.form.get('remit_date', '').strip() or None
    conn = get_conn()
    cur = conn.cursor()

    if user['role'] == 'designer':
        cur.execute("UPDATE reports SET remit_date = %s WHERE id = %s AND user_id = %s",
                    (remit_date, report_id, user['id']))
    else:
        cur.execute("UPDATE reports SET remit_date = %s WHERE id = %s",
                    (remit_date, report_id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

#### `GET /export` — 匯出 Excel（角色決定範圍）

```python
@app.route('/export')
@login_required
def export():
    user = get_current_user()
    conn = get_conn()

    if user['role'] == 'admin':
        df = pd.read_sql("""
            SELECT u.display_name as reporter, r.invoice_date, r.vendor_type,
                   r.vendor, r.project_no, r.stage, r.category, r.amount,
                   r.invoice_no, r.remit_date
            FROM reports r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.vendor_type, r.vendor, r.invoice_date
        """, conn)
    else:
        df = pd.read_sql("""
            SELECT invoice_date, vendor_type, vendor, project_no, stage,
                   category, amount, invoice_no, remit_date
            FROM reports
            WHERE user_id = %s
            ORDER BY vendor_type, vendor, invoice_date
        """, conn, params=(user['id'],))

    conn.close()

    if df.empty:
        return redirect('/')

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        write_detail_sheet(df, writer, is_admin=(user['role'] == 'admin'))
        write_summary_sheet(df, writer, is_admin=(user['role'] == 'admin'))
    output.seek(0)

    today_str = date.today().strftime('%Y%m%d')
    return send_file(output, ..., download_name=f'出帳報表_{today_str}.xlsx')
```

### 4.4 帳號管理路由（admin 專用）

#### `GET /users` — 帳號管理頁

```python
@app.route('/users')
@admin_required
def user_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, display_name, role, is_active, created_at
        FROM users ORDER BY role, display_name
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('users.html', users=users, user=get_current_user())
```

#### `POST /users/create` — 新增帳號

```python
@app.route('/users/create', methods=['POST'])
@admin_required
def user_create():
    username = request.form.get('username', '').strip()
    display_name = request.form.get('display_name', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'designer')

    # 驗證
    if not username or not display_name or not password:
        # 回傳錯誤...
        pass
    if role not in ('designer', 'admin'):
        role = 'designer'

    pw_hash = generate_password_hash(password)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, display_name, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (username, display_name, pw_hash, role))
        conn.commit()
    except Exception:
        conn.rollback()
        # username 重複等錯誤處理
    cur.close()
    conn.close()
    return redirect('/users')
```

#### `POST /users/<id>/toggle` — 啟用/停用

```python
@app.route('/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def user_toggle(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/users')
```

#### `POST /users/<id>/reset-password` — 重設密碼

```python
@app.route('/users/<int:uid>/reset-password', methods=['POST'])
@admin_required
def user_reset_password(uid):
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        return redirect('/users')
    pw_hash = generate_password_hash(new_password)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, uid))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/users')
```

---

## 5. Excel 匯出邏輯變更

### 5.1 明細頁籤

**管理員版：** 新增「提報人」欄位，排在最前面。

```python
col_map_admin = {
    'reporter': '提報人',
    'invoice_date': '發票收據日期',
    'vendor_type': '廠商類型',
    'vendor': '名稱',
    'project_no': '案場名稱',
    'stage': '階段',
    'category': '款項分類',
    'amount': '請款金額',
    'invoice_no': '發票收據編號',
    'remit_date': '匯款日期',
}
```

**設計師版：** 與 V1 相同，不含「提報人」欄位。

### 5.2 總覽頁籤

**管理員版：** 在原有的三類分計之後，新增「按提報人彙總」區塊：

```python
def write_summary_sheet(df, writer, is_admin=False):
    # ... 原有的三類分計邏輯（不變）...

    if is_admin and 'reporter' in df.columns:
        # 按提報人彙總
        reporter_summary = df.groupby(['reporter', 'category'])['amount'].sum().unstack(fill_value=0)
        reporter_summary['小計'] = reporter_summary.sum(axis=1)

        # 寫入總覽頁籤（接在三類分計下方，空一行）
        startrow = len(summary_df) + 3
        reporter_summary.to_excel(writer, sheet_name='總覽', startrow=startrow)
```

**設計師版：** 與 V1 相同，只有自己的三類分計。

---

## 6. 前端模板變更

### 6.1 新增模板

| 模板 | 用途 |
|------|------|
| `templates/login.html` | 登入頁面 |
| `templates/users.html` | 帳號管理頁面（admin） |

### 6.2 `login.html` — 登入頁

- 簡潔表單：帳號 + 密碼 + 登入按鈕
- 錯誤訊息顯示區
- 手機友善：input padding 14px+，按鈕高 48px+
- 置中卡片式 layout

### 6.3 `base.html` — 加入導覽列

```html
<nav class="navbar">
    {% if user %}
    <span class="nav-user">{{ user.display_name }}</span>
    {% if user.role == 'admin' %}
    <a href="/users" class="nav-link">帳號管理</a>
    {% endif %}
    <a href="/logout" class="nav-link">登出</a>
    {% endif %}
</nav>
```

所有頁面的 render_template 都要傳入 `user=get_current_user()`。

### 6.4 `list.html` — 變更

- **管理員版：** 表格新增「提報人」欄位（`r[11]`），顯示在第一欄
- **設計師版：** 不顯示「提報人」欄位（`r[11]` 為 NULL）
- 用 `{% if user.role == 'admin' %}` 控制是否顯示提報人欄

### 6.5 `users.html` — 帳號管理頁

**帳號清單表格：**
| 帳號 | 姓名 | 角色 | 狀態 | 操作 |

**操作按鈕：**
- 停用/啟用：toggle 按鈕，`POST /users/<id>/toggle`
- 重設密碼：小表單，輸入新密碼 + 確認按鈕，`POST /users/<id>/reset-password`

**新增帳號區塊：**
表單在頁面頂部或 modal：
- 帳號名稱（英文，text）
- 姓名（text）
- 預設密碼（password）
- 角色（select：設計師/管理員）
- 送出按鈕

---

## 7. 環境變數新增

| 變數 | 用途 | 設定位置 |
|------|------|----------|
| `SECRET_KEY` | Flask session 簽名 | Vercel 環境變數 + `.env.local` |

```bash
# .env.local 新增
SECRET_KEY=一組隨機長字串
```

Vercel Dashboard → Settings → Environment Variables → 加入 `SECRET_KEY`。

---

## 8. 檔案結構變更

```
onemood-expense-tracker/
├── api/index.py              # 不變
├── templates/
│   ├── base.html             # 加 navbar（使用者名稱 + 登出 + 帳號管理）
│   ├── login.html            # 【新增】登入頁
│   ├── list.html             # 修改：管理員多「提報人」欄位
│   ├── new.html              # 不變
│   └── users.html            # 【新增】帳號管理頁
├── static/
│   └── style.css             # 新增 navbar、login、users 頁面樣式
├── app.py                    # 大改：認證 + 權限 + 新路由
├── migrate_v2.py             # 【新增】V2 資料庫遷移腳本
├── vercel.json               # 不變
├── requirements.txt          # 不變
└── .env.local                # 新增 SECRET_KEY
```

---

## 9. 安全設計

### 9.1 密碼

- 使用 `werkzeug.security.generate_password_hash(password)` 儲存
- 使用 `check_password_hash(hash, password)` 驗證
- 絕對不存明碼、不 log 密碼

### 9.2 Session

- `app.secret_key` 從環境變數讀取，不 hardcode
- `session.permanent = True`，有效期 7 天
- 登出時 `session.clear()` 完全清除

### 9.3 後端權限檢查（每個路由都要）

- `@login_required`：未登入 → redirect `/login`
- `@admin_required`：非管理員 → redirect `/`
- 設計師操作 reports 時，SQL 一律帶 `WHERE user_id = %s`
- 設計師嘗試操作他人資料 → 不執行（SQL WHERE 條件不符，affected rows = 0）

### 9.4 防止越權存取

不做「先查再判」（TOCTOU），直接在 SQL 中帶條件：

```python
# 正確做法：SQL 直接過濾
cur.execute("DELETE FROM reports WHERE id = %s AND user_id = %s",
            (report_id, user['id']))

# 不做：先查出來再比對（有 race condition 風險）
```

---

## 10. Claude Code 實作順序

### Phase 1 — 資料庫遷移 + 認證骨架
1. 建立 `migrate_v2.py`，執行建表 + 資料遷移
2. `app.py` 加入 session 設定、`get_current_user()`、`@login_required`、`@admin_required`
3. 加入 `GET /login`、`POST /login`、`GET /logout` 路由
4. 建立 `templates/login.html`
5. `.env.local` 加入 `SECRET_KEY`
6. **測試：** 開啟首頁 → 被導到登入頁 → 用 onemood/admin123 登入 → 進入清單頁

### Phase 2 — 資料隔離
7. 修改 `GET /` 路由：根據角色過濾 reports
8. 修改 `POST /submit`：INSERT 帶 user_id
9. 修改 `POST /delete/<id>`：設計師只能刪自己的
10. 修改 `POST /update-remit-date/<id>`：設計師只能改自己的
11. **測試：** 建立測試設計師帳號 → 登入 → 只看到自己的資料

### Phase 3 — 前端調整
12. `base.html` 加 navbar（使用者名稱 + 登出 + 帳號管理入口）
13. `list.html` 管理員版多「提報人」欄位
14. 所有 render_template 傳入 `user=get_current_user()`
15. **測試：** 管理員看到提報人欄位、設計師看不到

### Phase 4 — 帳號管理
16. 加入 `/users`、`/users/create`、`/users/<id>/toggle`、`/users/<id>/reset-password` 路由
17. 建立 `templates/users.html`
18. **測試：** 管理員新增設計師 → 設計師登入 → 停用 → 登入失敗

### Phase 5 — Excel 報表升級
19. 修改 `GET /export`：根據角色決定撈取範圍
20. `write_detail_sheet()` 管理員版加「提報人」欄位
21. `write_summary_sheet()` 管理員版加「按提報人彙總」區塊
22. **測試：** 管理員匯出 → 有提報人 + 人員彙總；設計師匯出 → 只有自己的

### Phase 6 — Vercel 部署
23. Vercel 加入 `SECRET_KEY` 環境變數
24. push + deploy
25. **測試：** 線上跑完 PRD 第 9 節 13 步驗收

---

## 11. 驗收檢查清單

對應 PRD V2 第 9 節的 13 步驗收：

- [ ] 管理員登入，進入帳號管理頁面
- [ ] 新增兩個設計師帳號 designer_a / designer_b
- [ ] 登出，用 designer_a 登入
- [ ] designer_a 提報 3 筆，清單只顯示自己的 3 筆
- [ ] 登出，用 designer_b 登入
- [ ] designer_b 看到空清單，提報 2 筆，只看到 2 筆
- [ ] designer_b 直接打 URL 存取 designer_a 的資料 → 無法看到
- [ ] designer_b 嘗試刪除 designer_a 的提報 → 無法刪除
- [ ] 登出，管理員登入，看到全部 5 筆（含提報人欄位）
- [ ] 管理員匯出 Excel → 有提報人欄位 + 按提報人彙總
- [ ] 管理員停用 designer_a
- [ ] designer_a 嘗試登入 → 登入失敗
- [ ] designer_a 的歷史提報仍在報表中
