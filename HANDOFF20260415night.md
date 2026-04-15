# HANDOFF — 2026-04-15 Night（V1~V4 + UI Redesign + CSRF）

## 專案概述

出帳管理系統（Dawn Expense Tracker）— 室內設計公司 Dawn 的內部請款提報 + 廠商匯款管理 + Excel 匯出工具。

- **線上網址：** https://onemood-expense-tracker.vercel.app
- **GitHub：** https://github.com/songardwu/onemood-expense-tracker
- **技術棧：** Flask + Jinja2 + Neon Postgres + Vercel Serverless
- **程式碼量：** ~3,500 行（app.py 1,119 / CSS 1,120 / 模板 6 個 / JS 60 / 測試 520）
- **管理員登入：** dawn / dawn1234（⚠️ 需更換）
- **設計師登入：** designer_a / test1234

---

## 目前進度

### V1（已完成 ✅）
- 提報 CRUD、Excel 匯出（明細 + 總覽）、RWD 手機/桌面雙版面

### V2（已完成 ✅）
- 使用者認證（登入/登出、Flask session 7 天）
- 角色權限（admin / designer）、資料隔離
- 帳號管理（新增/停用/啟用/重設密碼）
- 跨使用者操作回 403

### V3（已完成 ✅）
- 發票防呆（category / 金額驗證、發票編號重複擋）
- 案場鎖定/解鎖、管理員全欄位 inline 編輯
- 廠商名稱智慧比對（去關鍵字 + 帳號交叉比對）
- 安全性：SECRET_KEY、X-Content-Type-Options、X-Frame-Options、CSP

### V4（已完成 ✅）
- 廠商匯款資料管理（CRUD + 批次 Excel/CSV 匯入 + 範本下載）
- 銀行資訊自動帶入（輸入廠商名 → API 回傳）
- 匯款方式（現金/公司轉帳/個帳轉帳）
- 匯款日期智慧預設（下月 5 日，跳過週末 + 台灣國定假日 2026-2027）
- 清單頁廠商加總（含匯款帳號資訊）+ 匯款方式加總 + 總計
- 廠商重複偵測（名稱相似 OR 帳號相同）
- Excel 匯出新增：匯款方式、銀行名稱、代碼、帳號、戶名

### UI Redesign（已完成 ✅）
- Apple 極簡風格：毛玻璃 navbar、SF Pro 字型、pill 按鈕/radio、CSS variables
- 自適應斷點：< 390px / < 768px / 768px+ / 1200px+
- iPhone safe area、Dark Mode（跟隨系統偏好）、列印樣式
- 「名稱」→「請款名稱」欄位更名
- 匯款日期欄位移至匯款方式前
- 請款加總帶入廠商匯款帳號資訊

### CSRF 防護（已完成 ✅）— 本次新增
- `flask-wtf` CSRFProtect 初始化，使用既有 `SECRET_KEY`
- **全系統 19 個表單皆已加入 CSRF token**：
  - login.html：1 個表單
  - new.html：1 個表單
  - users.html：3 個表單（新增帳號、停用/啟用、重設密碼）
  - list.html：8 個表單（鎖定、編輯、刪除、匯款日期修改）
  - vendors.html：6 個表單（匯入、新增、編輯、刪除 ×2、mobile 編輯）
- CSRF 錯誤回應：400 + 「操作逾時，請重新操作。」
- 測試腳本更新：自動快取 CSRF token，避免每次 POST 重新 GET

### 測試驗證（✅ 69/69 通過）
- `test_scenario.py` 涵蓋 15 大類、69 項，含 CSRF token 注入全通過

---

## 本次異動檔案（CSRF 防護）

| 檔案 | 變更 | 說明 |
|------|------|------|
| `app.py` | +10 行 | 新增 `from flask_wtf.csrf import CSRFProtect`、`csrf = CSRFProtect(app)`、400 error handler |
| `requirements.txt` | +1 行 | 新增 `flask-wtf` |
| `templates/login.html` | +1 行 | CSRF hidden input |
| `templates/new.html` | +1 行 | CSRF hidden input |
| `templates/users.html` | +3 行 | 3 個表單各加 CSRF hidden input |
| `templates/list.html` | +8 行 | 8 個表單各加 CSRF hidden input |
| `templates/vendors.html` | +6 行 | 6 個表單各加 CSRF hidden input |
| `test_scenario.py` | 重構 | 新增 `extract_csrf()`、`_csrf_cache` 快取機制、login 先 GET 取 token、post 自動注入 |

---

## 全部檔案總覽

| 檔案 | 行數 | 說明 |
|------|------|------|
| `app.py` | 1,119 | 全部商業邏輯：路由、認證、權限、CRUD、Excel、API、假日計算、CSRF |
| `static/style.css` | 1,120 | Apple 極簡風格、CSS variables、Dark Mode、全裝置自適應 |
| `static/app.js` | 60 | 廠商銀行資訊自動帶入（fetch API） |
| `templates/base.html` | 31 | 毛玻璃 navbar、Dark Mode theme-color |
| `templates/list.html` | 311 | 清單頁：6 種顯示路徑 + 加總面板含帳號資訊 |
| `templates/new.html` | 119 | 提報表單：pill radio、placeholder |
| `templates/login.html` | 32 | 登入頁：極簡白底 |
| `templates/users.html` | 84 | 帳號管理 |
| `templates/vendors.html` | 151 | 廠商資料管理 |
| `test_scenario.py` | 520 | 全功能 scenario test（69 項） |
| `requirements.txt` | 6 | flask, flask-wtf, psycopg2-binary, python-dotenv, pandas, openpyxl |
| `vercel.json` | — | Vercel 部署設定 |
| `api/index.py` | — | Vercel serverless 入口 |

---

## 資料庫現況

| 表 | 欄位數 | 索引 | 說明 |
|----|--------|------|------|
| `users` | 7 | PK + username unique | dawn(admin) + 2 位設計師 |
| `reports` | 16 | PK only（⚠️ 缺索引） | 測試資料約 11 筆 |
| `vendors` | 10 | PK + name unique | 5 家測試廠商含銀行資訊 |
| `vendor_keywords` | — | PK + keyword unique | 廠商名稱比對關鍵字 |

### reports 欄位（SELECT 順序）
```
r[0]=id, r[1]=vendor, r[2]=vendor_type, r[3]=amount, r[4]=category,
r[5]=invoice_no, r[6]=invoice_date, r[7]=remit_date, r[8]=project_no,
r[9]=stage, r[10]=created_at, r[11]=display_name, r[12]=is_locked,
r[13]=updated_by, r[14]=updated_at, r[15]=updater_name, r[16]=payment_method
```

---

## 安全防護現況

| 防護項目 | 狀態 | 實作方式 |
|---------|------|---------|
| CSRF | ✅ 已完成 | flask-wtf CSRFProtect，19 個表單全覆蓋 |
| 密碼雜湊 | ✅ | werkzeug PBKDF2 |
| SQL Injection | ✅ | psycopg2 parameterized queries（全部用 `%s`） |
| XSS | ✅ | Jinja2 auto-escaping + CSP header |
| Clickjacking | ✅ | X-Frame-Options: DENY |
| MIME Sniffing | ✅ | X-Content-Type-Options: nosniff |
| Session 加密 | ✅ | Flask signed cookie + SECRET_KEY |
| HTTPS | ✅ | Vercel 強制 HTTPS + SESSION_COOKIE_SECURE |
| Session HttpOnly | ⚠️ 未設定 | 需加 `SESSION_COOKIE_HTTPONLY = True` |
| Session SameSite | ⚠️ 未設定 | 需加 `SESSION_COOKIE_SAMESITE = 'Lax'` |
| Rate Limiting | ❌ 未實作 | 登入可無限嘗試 |
| 密碼複雜度 | ❌ 未實作 | 無最小長度要求 |

---

## 已確認事項

| 項目 | 驗證方式 | 結果 |
|------|---------|------|
| 登入/登出/未登入跳轉 | scenario test #1 | ✅ |
| 廠商 CRUD + 權限 | scenario test #2 | ✅ |
| 廠商銀行 API + 重複偵測 | scenario test #3 | ✅ |
| 報表新增 + 匯款日期預設 + 匯款方式 | scenario test #4 | ✅ |
| 廠商加總 + 方式加總 + 總計 | scenario test #5 | ✅ |
| 管理員 inline 編輯 | scenario test #6 | ✅ |
| 案場鎖定/解鎖 | scenario test #7 | ✅ |
| 設計師資料隔離 | scenario test #8 | ✅ |
| 跨使用者操作 403 | scenario test #9 | ✅ |
| 輸入驗證（category / 金額） | scenario test #10 | ✅ |
| Security Headers | scenario test #11 | ✅ |
| 台灣假日匯款日期計算 | scenario test #12 | ✅ |
| Excel 匯出（含 V4 新欄位） | scenario test #13 | ✅ |
| 導航列 | scenario test #14 | ✅ |
| **CSRF 防護全表單覆蓋** | scenario test 全程帶 token | ✅ |
| 請款加總含匯款帳號資訊 | 手動驗證 | ✅ |
| Apple 極簡 UI + Dark Mode | 手動驗證 | ✅ |

---

## 接手指南

### 先看什麼（按順序）
1. **本文件** — 全貌、安全現況、資料庫結構
2. **`TODO20260415night.md`** — 待辦優先順序、阻塞點、PM 建議
3. **`app.py`** — 所有邏輯集中在此，重點區段：
   - 第 1~80 行：設定、假日定義、`default_remit_date()`
   - 第 102 行：`csrf = CSRFProtect(app)` — CSRF 初始化
   - 第 151~155 行：CSRF 錯誤處理（⚠️ 需精準化，見 TODO P0 #3）
   - `index()` 函數（~第 213 行起）：清單頁 + 加總 + 重複偵測 — **最複雜的函數**
   - `/vendors` 路由群：廠商 CRUD + 批次匯入
   - `/api/vendor-bank`：銀行資訊 API
4. **`static/style.css`** — CSS variables 在 `:root` 定義所有設計 token
5. **`test_scenario.py`** — 69 項測試，當功能清單讀；注意 `_csrf_cache` 機制

### 本地開發
```bash
pip install flask flask-wtf psycopg2-binary python-dotenv pandas openpyxl
# 環境變數：npx vercel env pull .env.local
python app.py   # → http://127.0.0.1:5000

# 跑測試（需先啟動 server）
python test_scenario.py
```

### 部署
```bash
git push origin master   # 自動觸發 Vercel 部署
```

---

## 架構筆記

- **無 ORM** — psycopg2 raw SQL，散佈在 app.py 各路由
- **CSRF** — flask-wtf CSRFProtect，token 透過 `csrf_token()` Jinja2 函數注入所有表單
- **Session** — Flask signed cookie，不依賴 server-side store（適合 serverless）
- **密碼** — werkzeug PBKDF2
- **資料隔離** — SQL WHERE 層級（設計師只看自己的 reports）
- **Excel** — pandas + openpyxl，BytesIO 串流（不落地檔案）
- **RWD** — Mobile first，768px 分界（卡片 ↔ 表格）
- **設計系統** — CSS custom properties（`--accent`, `--surface` 等），改主題色只需改 `:root`
- **Dark Mode** — `prefers-color-scheme: dark` media query，自動跟隨系統
- **廠商比對** — `vendor_keywords` 去關鍵字後比對 + 銀行帳號交叉比對
- **假日** — 2026-2027 台灣國定假日 hardcoded（`TW_HOLIDAYS` set）
- **SESSION_COOKIE_SECURE** — `bool(os.environ.get('VERCEL'))`，僅 Vercel 啟用
