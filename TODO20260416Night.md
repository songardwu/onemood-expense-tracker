# TODO — 2026-04-16 Night

> 下一步、優先順序、阻塞點

---

## 阻塞點（須先解決）

| # | 項目 | 阻塞原因 | 影響範圍 |
|---|------|---------|---------|
| B1 | Vercel Git 連結 | 需在 Vercel Dashboard 手動操作 Login Connection → GitHub，CLI 無法完成 | 無法設 preview 環境變數、無法 auto-deploy |
| B2 | Admin 密碼更換 | 初始密碼 `admin123` 仍在使用，需人工登入修改 | 安全風險 |

---

## 下一步（依優先順序）

### P0 — 立即處理

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| 1 | Admin 密碼更換 | 登入 `/change-password` 修改初始密碼 | 2 min |
| 2 | Vercel Git 連結 | Dashboard → Settings → Login Connections → GitHub → 專案 Git Connect | 10 min |
| 3 | SECRET_KEY preview 環境 | Git 連結完成後 `vercel env add SECRET_KEY preview` | 2 min |

### P1 — 本週內

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| 4 | iOS Safari 實機測試 | `/new` input 無縮放、safe area、字型 | 10 min |
| 5 | 跨瀏覽器驗證 | Chrome + Edge + Firefox 桌面版逐頁 | 15 min |
| 6 | 4G 效能測試 | Chrome DevTools Throttle → FCP ≤ 2s | 5 min |
| 7 | Dark Mode 驗證 | 暖棕背景、文字可讀、nav 配色 | 5 min |

### P2 — 排入驗收

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| 8 | UAT 驗收 | 管理員桌面 + 設計師手機，當面操作驗收 | 1 hr |

### P3 — 未來功能（依需求排入）

| # | 項目 | 說明 |
|---|------|------|
| F1 | Dashboard 統計圖表 | Chart.js 月度趨勢、廠商佔比、案場花費 |
| F2 | 付款排程管理 | 待匯款清單、到期提醒、批次匯出 |
| F3 | 預算管理 | 科目預算設定、超支警示、達成率 |
| F4 | 完整審計日誌 | 新增 audit_log 記錄所有 INSERT/UPDATE/DELETE |
| F5 | 可編輯已提報項目 | 設計師修改已送出的提報 |
| F6 | CI 自動化 | GitHub Actions push 時跑測試 |
| F7 | Error Tracking | Sentry Free + UptimeRobot |
| F8 | 台灣假日 2028 更新 | `TW_HOLIDAYS` 只到 2027，需 2027 Q4 前更新 |

---

## 技術債

- `reports.vendor` 為純文字，未與 `vendors` 表 FK 關聯
- flask-limiter 使用 `memory://`，Vercel 多 instance 間不共享
- 測試腳本因 CSRF 無法直接跑，需考慮測試策略
