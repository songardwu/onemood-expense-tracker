# 出帳管理系統 V2｜實作任務清單 TASK

**對應文件:** prdv2.md / sddv2.md v2.0
**分支:** v2-dev
**執行方式:** Claude Code 逐步實作，每個 Task 完成後測試再進下一個

---

## 前置狀態（已完成）

- [x] V1 MVP 已部署上線 (onemood-expense-tracker.vercel.app)
- [x] Neon Postgres 已建立，`reports` 表已有資料
- [x] `v2-dev` 分支已建立並切換
- [x] prdv2.md / sddv2.md 已完成

---

## Phase 1 — 資料庫遷移 + 認證骨架

### Task 1.1：建立 `migrate_v2.py` 遷移腳本
- **檔案：** `migrate_v2.py`
- **做什麼：**
  - import `get_conn` from app + `generate_password_hash` from werkzeug
  - 建立 `users` 表（id, username, display_name, password_hash, role, is_active, created_at）
  - 插入初始管理員帳號：username=`dawn`, display_name=`Dawn`, password=`admin123`, role=`admin`
  - `reports` 表新增 `user_id INTEGER REFERENCES users(id)`
  - 既有 reports 全部 `UPDATE SET user_id = 1`（歸屬 Dawn）
  - `ALTER COLUMN user_id SET NOT NULL`
- **執行：** `python migrate_v2.py`
- **驗證：**
  - [ ] users 表存在，有 1 筆 Dawn 管理員
  - [ ] reports 每筆都有 user_id = 1

### Task 1.2：`.env.local` 加入 `SECRET_KEY`
- **檔案：** `.env.local`
- **做什麼：** 新增一行 `SECRET_KEY=一組隨機字串`（用 python `secrets.token_hex(32)` 產生）

### Task 1.3：`app.py` 加入認證基礎設施
- **檔案：** `app.py`
- **做什麼：**
  - `from werkzeug.security import generate_password_hash, check_password_hash`
  - `from datetime import timedelta`
  - `app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret')`
  - `app.permanent_session_lifetime = timedelta(days=7)`
  - 新增 `get_current_user()` 函式：從 session 讀 user_id / role / display_name，回傳 dict 或 None
  - 新增 `@login_required` 裝飾器：未登入 → redirect `/login`
  - 新增 `@admin_required` 裝飾器：非 admin → redirect `/`

### Task 1.4：建立登入/登出路由
- **檔案：** `app.py`
- **做什麼：**
  - `GET /login`：已登入則 redirect `/`，否則 render `login.html`
  - `POST /login`：
    - 從 users 表查 username
    - `check_password_hash` 驗證密碼
    - 檢查 `is_active`，停用帳號回傳「此帳號已停用」
    - 驗證失敗統一回傳「帳號或密碼錯誤」（不分開提示）
    - 成功：session 寫入 user_id / display_name / role，`session.permanent = True`，redirect `/`
  - `GET /logout`：`session.clear()`，redirect `/login`

### Task 1.5：建立 `templates/login.html`
- **檔案：** `templates/login.html`
- **做什麼：**
  - 繼承 `base.html`（但不需要 navbar）
  - 置中卡片 layout，標題「出帳管理系統」
  - 表單：帳號（text）+ 密碼（password）+ 登入按鈕
  - 錯誤訊息區：`{% if error %}` 紅字提示
  - 手機友善：input padding 14px+，按鈕高 48px+

### Task 1.6：測試 Phase 1
- **驗證：**
  - [ ] 瀏覽器打開 `/` → 被導到 `/login`
  - [ ] 輸入錯誤帳密 → 顯示「帳號或密碼錯誤」
  - [ ] 輸入 dawn / admin123 → 登入成功，進入清單頁
  - [ ] 清單頁看到既有資料（V1 的測試資料）
  - [ ] 點「登出」→ 回到登入頁
  - [ ] 再次開 `/` → 被導回登入頁（session 已清）

---

## Phase 2 — 資料隔離

### Task 2.1：修改 `GET /` 清單頁路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - admin：`SELECT ... FROM reports r JOIN users u ON r.user_id = u.id`，撈全部，多撈 `u.display_name`
  - designer：`SELECT ... FROM reports r WHERE r.user_id = %s`，只撈自己的，display_name 填 NULL
  - render 時傳入 `user=get_current_user()`

### Task 2.2：修改 `POST /submit` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - INSERT 語句新增 `user_id` 欄位，值為 `get_current_user()['id']`
  - 驗證失敗的 render 也要傳 `user=get_current_user()`

### Task 2.3：修改 `POST /delete/<id>` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - designer：`DELETE FROM reports WHERE id = %s AND user_id = %s`（SQL 直接帶條件）
  - admin：`DELETE FROM reports WHERE id = %s`（不限 user_id）

### Task 2.4：修改 `POST /update-remit-date/<id>` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - designer：`UPDATE ... WHERE id = %s AND user_id = %s`
  - admin：`UPDATE ... WHERE id = %s`

### Task 2.5：修改 `GET /new` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - render 時傳入 `user=get_current_user()`

### Task 2.6：測試 Phase 2
- **前置：** 手動建立一個測試設計師帳號（直接 SQL 或稍後透過帳號管理）
- **驗證：**
  - [ ] dawn 登入 → 看到全部 reports
  - [ ] 測試設計師登入 → 看到 0 筆（空清單）
  - [ ] 設計師新增 1 筆 → 清單顯示 1 筆
  - [ ] 設計師嘗試刪除 dawn 的資料（直接 POST 表單）→ 不生效
  - [ ] dawn 登入 → 看到所有資料（含設計師剛新增的）

---

## Phase 3 — 前端調整

### Task 3.1：修改 `templates/base.html` 加入 navbar
- **檔案：** `templates/base.html`
- **做什麼：**
  - `<body>` 內頂部加 `<nav class="navbar">`
  - 左側：系統名稱「出帳管理」
  - 右側：`{% if user %}`
    - 顯示使用者名稱 `{{ user.display_name }}`
    - admin 才顯示「帳號管理」連結 (`/users`)
    - 「登出」連結 (`/logout`)
  - login 頁不需要 navbar → 用 `{% block navbar %}` 或條件判斷

### Task 3.2：修改 `templates/list.html` 加入提報人欄位
- **檔案：** `templates/list.html`
- **做什麼：**
  - 桌面表格：`{% if user.role == 'admin' %}` 時，第一欄加「提報人」(`r[11]`)
  - 手機卡片：admin 時，卡片頂部顯示提報人名稱
  - 設計師版：不顯示提報人相關欄位
  - 注意：r 的 index 對照
    - r[0]=id, r[1]=vendor, r[2]=vendor_type, r[3]=amount, r[4]=category
    - r[5]=invoice_no, r[6]=invoice_date, r[7]=remit_date, r[8]=project_no
    - r[9]=stage, r[10]=created_at, r[11]=display_name（admin 才有值）

### Task 3.3：修改 `templates/new.html`
- **檔案：** `templates/new.html`
- **做什麼：** 確保頁面有 `user` 變數供 navbar 使用（base.html 需要）

### Task 3.4：`static/style.css` 新增 navbar 樣式
- **檔案：** `static/style.css`
- **做什麼：**
  - `.navbar`：背景 #4A90D9，白字，高 50px，flex 左右分佈
  - `.nav-user`：白色粗體
  - `.nav-link`：白色底線連結
  - 手機版：字體稍小，間距壓縮
  - login 頁面不顯示 navbar

### Task 3.5：測試 Phase 3
- **驗證：**
  - [ ] 所有頁面頂部有 navbar，顯示使用者名稱 + 登出
  - [ ] admin 登入 → navbar 有「帳號管理」連結
  - [ ] admin 清單頁 → 表格有「提報人」欄位
  - [ ] designer 登入 → navbar 沒有「帳號管理」
  - [ ] designer 清單頁 → 沒有「提報人」欄位
  - [ ] login 頁面 → 沒有 navbar

---

## Phase 4 — 帳號管理

### Task 4.1：建立帳號管理路由
- **檔案：** `app.py`
- **做什麼：**
  - `GET /users`（`@admin_required`）：撈 users 全部，render `users.html`
  - `POST /users/create`（`@admin_required`）：
    - 接收 username, display_name, password, role
    - 驗證：username / display_name / password 不為空，role 為 designer 或 admin
    - `generate_password_hash(password)` 後 INSERT
    - username 重複 → 回傳錯誤提示
    - 成功 → redirect `/users`
  - `POST /users/<id>/toggle`（`@admin_required`）：
    - `UPDATE users SET is_active = NOT is_active WHERE id = %s`
    - redirect `/users`
  - `POST /users/<id>/reset-password`（`@admin_required`）：
    - 接收 new_password，`generate_password_hash` 後 UPDATE
    - redirect `/users`

### Task 4.2：建立 `templates/users.html`
- **檔案：** `templates/users.html`
- **做什麼：**
  - 繼承 `base.html`
  - 頁面標題「帳號管理」
  - **新增帳號區塊：** 表單（帳號、姓名、預設密碼、角色 select）+ 送出按鈕
  - **帳號清單表格：**
    - 欄位：帳號、姓名、角色、狀態、操作
    - 角色顯示：designer → 「設計師」、admin → 「管理員」
    - 狀態：啟用中（綠）/ 已停用（灰）
    - 操作欄：
      - 「停用」/「啟用」按鈕 → `POST /users/<id>/toggle`
      - 「重設密碼」：小型 inline 表單（密碼 input + 確認按鈕）
    - 管理員自己的帳號不顯示停用按鈕（防止自己停用自己）
  - 錯誤訊息區：`{% if error %}` 顯示
  - RWD：手機版表格改卡片式或水平滾動

### Task 4.3：`static/style.css` 新增帳號管理頁樣式
- **檔案：** `static/style.css`
- **做什麼：**
  - 新增帳號表單樣式（與 report-form 類似）
  - 帳號清單表格樣式
  - 狀態 badge：啟用中（綠色）/ 已停用（灰色）
  - 操作按鈕樣式

### Task 4.4：測試 Phase 4
- **驗證：**
  - [ ] admin 登入 → 點「帳號管理」→ 看到帳號清單（只有 Dawn）
  - [ ] 新增 designer_a（帳號 designer_a / 姓名 設計師A / 密碼 test123 / 角色 設計師）
  - [ ] 新增 designer_b（同上，改名稱和帳號）
  - [ ] 帳號清單顯示 3 筆
  - [ ] 登出 → 用 designer_a / test123 登入 → 成功
  - [ ] 回管理員 → 停用 designer_a → designer_a 嘗試登入 → 失敗
  - [ ] 重新啟用 designer_a → 登入成功
  - [ ] 重設 designer_a 密碼為 newpass → 用 newpass 登入成功
  - [ ] 重複帳號名稱 → 顯示錯誤提示

---

## Phase 5 — Excel 報表升級

### Task 5.1：修改 `GET /export` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 加 `@login_required`
  - admin：SQL JOIN users，多撈 `u.display_name as reporter`，撈全部
  - designer：SQL 只撈自己的（`WHERE user_id = %s`），不撈 reporter
  - 傳 `is_admin` 參數給 `write_detail_sheet` / `write_summary_sheet`

### Task 5.2：修改 `write_detail_sheet()`
- **檔案：** `app.py`
- **做什麼：**
  - 接收 `is_admin` 參數
  - admin 版 `col_map`：最前面加 `'reporter': '提報人'`
  - designer 版：與 V1 相同，不含提報人

### Task 5.3：修改 `write_summary_sheet()`
- **檔案：** `app.py`
- **做什麼：**
  - 接收 `is_admin` 參數
  - 原有三類分計邏輯不變
  - admin 版：在三類分計下方，新增「按提報人彙總」區塊
    - `df.groupby(['reporter', 'category'])['amount'].sum().unstack(fill_value=0)`
    - 加「小計」欄
    - 寫入同一個「總覽」頁籤，空一行接在下方
  - designer 版：不加提報人彙總

### Task 5.4：測試 Phase 5
- **前置：** 確保 designer_a 和 designer_b 各有幾筆提報
- **驗證：**
  - [ ] admin 匯出 Excel → 明細頁籤第一欄有「提報人」
  - [ ] admin 匯出 Excel → 總覽頁籤有「按提報人彙總」區塊
  - [ ] designer_a 匯出 Excel → 明細只有自己的資料，無「提報人」欄位
  - [ ] designer_a 匯出 Excel → 總覽只有自己的三類分計，無提報人彙總

---

## Phase 6 — Vercel 部署 + 完整驗收

### Task 6.1：Vercel 新增環境變數
- **做什麼：** 在 Vercel Dashboard 或 CLI 加入 `SECRET_KEY`

### Task 6.2：Git commit + push + deploy
- **指令：**
  1. `git add -A`
  2. `git commit -m "V2: 帳號系統 + 權限控管 + 資料隔離"`
  3. `git push origin v2-dev`
  4. `vercel --prod`
- **確認：** 部署成功

### Task 6.3：線上執行 migration
- **做什麼：** 確認線上資料庫已跑過 migrate_v2.py（因為開發用同一個 Neon Postgres，本機 migrate 等於線上 migrate）

### Task 6.4：完整驗收測試（PRD V2 第 9 節 13 步）

| # | 測試步驟 | 預期結果 | 狀態 |
|---|----------|----------|------|
| 1 | 管理員 dawn/admin123 登入 → 進帳號管理 | 看到帳號清單 | [ ] |
| 2 | 新增 designer_a + designer_b | 帳號清單 3 筆 | [ ] |
| 3 | 登出 → designer_a 登入 | 登入成功 | [ ] |
| 4 | designer_a 提報 3 筆 | 清單顯示 3 筆 | [ ] |
| 5 | 登出 → designer_b 登入 | 登入成功 | [ ] |
| 6 | designer_b 看到空清單 → 提報 2 筆 | 清單顯示 2 筆 | [ ] |
| 7 | designer_b URL 直打存取 designer_a 的資料 | 無法看到 | [ ] |
| 8 | designer_b 嘗試刪除 designer_a 的提報 | 無法刪除 | [ ] |
| 9 | 管理員登入 → 清單頁 | 看到全部 5 筆 + 提報人欄位 | [ ] |
| 10 | 管理員匯出 Excel | 有提報人 + 按提報人彙總 | [ ] |
| 11 | 管理員停用 designer_a | 帳號狀態變「已停用」 | [ ] |
| 12 | designer_a 嘗試登入 | 登入失敗「此帳號已停用」 | [ ] |
| 13 | 管理員匯出 Excel | designer_a 歷史提報仍在報表中 | [ ] |
