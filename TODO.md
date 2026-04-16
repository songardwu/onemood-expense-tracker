# TODO — 整併版（2026-04-16 截止）

> 整併自 TODO20260415.md / TODO20260415night.md / TODO20260416morning.md / TODO20260416Night.md
> 僅保留尚未完成的項目

---

## 手動操作（需人工執行）

| # | 項目 | 預估時間 | 說明 |
|---|------|---------|------|
| M1 | Admin 密碼更換 | 2 min | 登入後到 `/change-password` 修改 |
| M2 | Vercel Git 連結 | 10 min | Dashboard → Settings → Login Connections → 加 GitHub → 專案 Settings → Git → Connect |
| M3 | SECRET_KEY 環境變數 | 5 min | M2 完成後，`vercel env add SECRET_KEY preview` + `development` |
| M4 | iOS Safari 實機測試 | 10 min | `/new` 點 input 無縮放、safe area 正常、字型正確 |
| M5 | Dark Mode 驗證 | 5 min | 系統切 dark mode 確認暖棕背景、文字可讀、hamburger nav 配色 |
| M6 | 跨瀏覽器驗證 | 15 min | Chrome + Edge + Firefox 桌面版逐頁確認 |
| M7 | 4G 效能測試 | 5 min | Chrome DevTools → Throttle: Fast 3G → `/new` FCP ≤ 2s |
| M8 | UAT 驗收 | 1 hr | 管理員桌面 + 設計師手機當面驗收 |

---

## 未來開發（不急，依需求排入）

| # | 項目 | 說明 |
|---|------|------|
| F1 | 完整審計日誌 | 新增 `audit_log` 表記錄所有 INSERT/UPDATE/DELETE |
| F2 | 可編輯已提報項目 | 設計師修改已送出的提報 |
| F3 | Dashboard 統計圖表 | Chart.js 月度趨勢 + 廠商佔比 + 案場花費（已暫緩） |
| F4 | CI 自動化 | GitHub Actions push 時跑 test_scenario.py |
| F5 | Error Tracking | Sentry Free + UptimeRobot 監控 |
| F6 | 台灣假日 2028 更新 | `TW_HOLIDAYS` 只到 2027 年底，2027 Q4 前需更新 |

---

## 已完成項目摘要

<details>
<summary>展開查看（共 40+ 項）</summary>

### 安全性
- [x] CSRF 防護（flask-wtf，19 表單）
- [x] CSRF error handler（CSRFError 專用 exception）
- [x] Session fixation 防護（登入前 session.clear）
- [x] Session Cookie 安全（HttpOnly + SameSite=Lax）
- [x] Rate Limiting（flask-limiter，登入 5/min）
- [x] Logout GET→POST + CSRF
- [x] 密碼最低 6 字元
- [x] debug=True 修正（環境變數控制）
- [x] vendor_create/import 改 admin_required
- [x] 廠商匯入檔案驗證（2MB + 500 筆上限）
- [x] DELETE/UPDATE 路由 403 回傳

### 穩定性
- [x] DB 連線管理（Flask g + teardown_appcontext）
- [x] Decimal 精度（DecimalJSONProvider）
- [x] 部分寫入 rollback
- [x] DB Index（5 條）

### 功能
- [x] 搜尋篩選（日期/廠商/案場/類別）
- [x] 篩選後匯出 Excel
- [x] 分頁機制（50 筆/頁）
- [x] 設計師改密碼（/change-password）
- [x] 登入紀錄（login_logs + IP 追蹤）
- [x] 案場損益管理（Phase 1-4）

### UI/UX
- [x] 大地色系 Design Token
- [x] Bento Grid 全頁面排版
- [x] Noto Serif TC 標題 + Noto Sans TC 內文
- [x] Dark Mode 暖棕色版
- [x] 手機響應式 + hamburger nav
- [x] mobile cards（users / cost_categories / login_logs）
- [x] WCAG AA 無障礙（skip link / semantic / aria / scope）
- [x] prefers-reduced-motion guard
- [x] Print stylesheet
- [x] iOS input font-size ≥ 16px

### 部署
- [x] Vercel Production 部署
- [x] git tag v4-final
- [x] Before/After 對比截圖

</details>

---

## 技術決策記錄

- **DB 連線池**：Neon pooler endpoint 已在 server-side 處理，Vercel serverless 不需 app-level pool
- **CSP unsafe-inline**：僅 style-src，54 處 inline style 重構成本高，無 script-src 風險，接受現狀
- **密碼政策**：維持最低 6 字元，不加複雜度要求，不加首次登入強制改密碼
- **Dashboard D9**：已暫緩，列為 F3 未來開發

---

*整併日期：2026-04-16*
*原始檔案：TODO20260415.md / TODO20260415night.md / TODO20260416morning.md / TODO20260416Night.md*
