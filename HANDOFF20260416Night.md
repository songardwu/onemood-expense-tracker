# HANDOFF 20260416 Night — 交接文件（更新版）

## 本次完成的工作

### 一、案場模組整合測試（Phase 1-4）
- 撰寫 `test_projects.py`（25 項自動化測試），全部通過
- 發現並修復 **獎金出帳 500 error**：`routes/projects.py` bonus_disburse 的 category 值 `'設計師獎金'` 違反 `reports_category_check` 約束，改為 `'獎金'`

### 二、全站四維審查 + 修復
以下為已改檔案及修改內容：

#### 資安 Security
| 修復 | 檔案 | 說明 |
|------|------|------|
| S1 Session Fixation | `routes/auth.py` | 登入前加 `session.clear()` |
| S2 Rate Limiting | `app.py` | 加 flask-limiter，`/login` 限 5 次/分 |
| S3 Logout GET→POST | `routes/auth.py`, `templates/base.html` | logout 改 POST + CSRF |
| S5 密碼長度 | `routes/users.py` | 新增/重設密碼最少 6 字元 |
| S6 debug=True | `app.py` | 改為 `os.environ.get('FLASK_DEBUG') == '1'` |

#### 穩定性 Stability
| 修復 | 檔案 | 說明 |
|------|------|------|
| T1 DB 連線洩漏 | `services/utils.py`, `app.py`, 所有 routes | Flask g + teardown_appcontext 自動回收；移除全部手動 conn.close() |
| T3 Decimal 精度 | `routes/projects.py`, `app.py` | _get_project_summary 回傳原生 Decimal；加 DecimalJSONProvider |
| T5 部分寫入 | `routes/projects.py` | update_costs 加 try/except rollback |

#### 無障礙 Accessibility
| 修復 | 檔案 | 說明 |
|------|------|------|
| A1 Skip Link | `templates/base.html`, `static/style.css` | 加「跳至主要內容」隱藏連結 |
| A2 `<main>` | `templates/base.html` | `<div class="container">` 改 `<main id="main-content" role="main">` |
| A3 動態 title | 全部 templates | 加 `{% block title %}` 每頁獨立標題 |
| A4 table scope | 全部有 `<th>` 的 templates | 加 `scope="col"` |
| A5 aria-label | project_detail, cost_categories, vendors, users | inline 表單輸入加 aria-label |
| A6 btn-small | `static/style.css` | padding 5px→8px, min-height: 36px |
| A7 radio | `static/style.css` | `display:none` 改 `opacity:0; position:absolute` |

#### 響應式 Responsive
| 修復 | 檔案 | 說明 |
|------|------|------|
| R1 Hamburger Nav | `templates/base.html`, `static/style.css` | 手機版漢堡選單（<768px 收合） |
| R2 手機卡片 | `templates/users.html`, `templates/cost_categories.html` | 新增 `.mobile-cards` 視圖 |
| R3 固定寬度 | `templates/cost_categories.html` | 移除 `style="width:160px"` 和 `width:200px` |
| R4 480px 斷點 | `static/style.css` | 新增 480-767px 中間斷點 |
| R5 Dashboard 小螢幕 | `static/style.css` | <390px 強制 2 欄 + 縮小字體 |

### 三、P2 品質強化（本輪新增）

| 修復 | 檔案 | 說明 |
|------|------|------|
| CSRF handler | `app.py` | `@app.errorhandler(400)` + 字串比對 → `@app.errorhandler(CSRFError)` |
| 分頁機制 | `services/utils.py`, `routes/reports.py`, `routes/projects.py`, `templates/list.html`, `templates/projects.html`, `templates/project_logs.html`, `templates/pagination.html`, `static/style.css` | 50 筆/頁分頁，含頁碼導覽 UI |
| DB 連線池評估 | 無程式碼改動 | Neon pooler 已在 server-side 處理，Vercel serverless 不需 app-level pool |
| CSP 評估 | 無程式碼改動 | `style-src unsafe-inline` 為低風險，54 處 inline style 重構成本高，維持現狀 |

### 四、已改檔案清單
```
app.py                          — Decimal JSON, limiter, teardown, debug fix, CSRFError handler
services/utils.py               — Flask g 連線管理, close_db, get_page_info 分頁工具
routes/auth.py                  — session fixation, logout POST, rate limit
routes/projects.py              — conn.close 移除, Decimal, rollback, bonus fix, 分頁
routes/reports.py               — conn.close 移除, 連線合併, 分頁
routes/vendors.py               — conn.close 移除
routes/users.py                 — conn.close 移除, 密碼長度
templates/base.html             — skip link, main, title, hamburger, logout POST
templates/list.html             — title, scope, 分頁
templates/new.html              — title
templates/projects.html         — title, scope, 分頁
templates/project_detail.html   — title, scope, aria-label
templates/project_form.html     — title
templates/project_logs.html     — title, scope, 分頁
templates/cost_categories.html  — title, scope, aria-label, 移除固定寬, mobile cards
templates/users.html            — title, scope, aria-label, autocomplete, mobile cards
templates/vendors.html          — title, scope, aria-label
templates/pagination.html       — 新增：共用分頁 macro
static/style.css                — skip-link, hamburger, btn-small, radio, 480px breakpoint, pagination
.env.local                      — 加 FLASK_DEBUG=1
```

### 五、已確認正常運作
- Dev server 可正常啟動（http://127.0.0.1:5000）
- 登入頁正常載入（CSRF token 正確產出）
- 25 項整合測試全部 PASS（bonus disburse 修復後）
- flask-limiter 已安裝
- App import 驗證通過（所有模組正確載入）

### 六、尚未確認
- Vercel 部署（需推送後驗證）
- Dark mode 下 hamburger nav 配色（需實機測試）
- 分頁 UI 在大量資料下的實際表現

## 接手者應先看什麼
1. **`app.py`** — 了解 limiter、DecimalJSONProvider、teardown、CSRFError 架構
2. **`services/utils.py`** — 了解 `get_conn()` Flask g 行為 + `get_page_info()` 分頁工具
3. **`templates/base.html`** — 了解 hamburger nav + logout POST 的新結構
4. **`templates/pagination.html`** — 了解分頁 macro 用法
5. **`TODO20260416Night.md`** — 確認剩餘項目（僅剩 P3）
6. **`test_projects.py`** — 可直接執行驗證所有功能正常
