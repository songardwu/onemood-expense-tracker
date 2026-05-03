# TODO — 2026-05-03 Night

> 客戶請款單模組完工 / 下一步、優先順序、阻塞點

---

## 阻塞點（須先解決）

| # | 項目 | 阻塞原因 | 影響範圍 |
|---|------|---------|---------|
| B1 | Vercel Git 連結 | 需 Vercel Dashboard 手動操作 Login Connection → GitHub | preview 環境變數無法設、無 auto-deploy |
| B2 | Admin 密碼更換 | 目前是臨時密碼 `Dawn@2026`（Claude 重設），需登入改為自己的 | 安全風險 |

---

## 下一步（依優先順序）

### P0 — 立即處理

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| 1 | Admin 改密碼 | 登入 `/change-password` 把 `Dawn@2026` 換成自己的 | 2 min |
| 2 | invoices 模組 UAT | 完整跑流程：建請款單 → 開立 → 標收款 → 作廢 | 15 min |

### P1 — 本週內

| # | 項目 | 說明 | 預估 |
|---|------|------|------|
| 3 | Dashboard 首頁總覽 | 取代目前 `/` 出帳列表為老闆視角的總覽（本月損益/待匯款/收款進度） | 1 天 |
| 4 | Vercel Git 連結 | Dashboard → Settings → Login Connections → GitHub → Connect | 10 min |
| 5 | SECRET_KEY preview 環境 | B1 完成後 `vercel env add SECRET_KEY preview` | 2 min |
| 6 | iOS Safari 實機測試 | `/new` input 不縮放、safe area、字型 | 10 min |
| 7 | 跨瀏覽器驗證 | Chrome / Edge / Firefox 桌面版逐頁 | 15 min |

### P2 — 排入驗收

| # | 項目 | 說明 |
|---|------|------|
| 8 | UAT 驗收 | 管理員桌面 + 設計師手機，當面操作驗收 |

### P3 — 未來功能（依需求排入）

| # | 項目 | 說明 |
|---|------|------|
| F1 | 收據附件上傳 | 報帳加附圖（手機拍照即傳，需 Vercel Blob/R2） |
| F2 | 提醒通知中心 | 押金待退/收款逾期/待匯款提醒 |
| F3 | 月度/年度報表 | Chart.js 趨勢圖、廠商佔比、利潤率走勢 |
| F4 | 請款單 PDF 輸出 | 用瀏覽器列印 stylesheet 即可（已有 print CSS） |
| F5 | invoices 編號跨年驗證 | `INV-YYYYMM-NNN` 跨月跨年的流水號正確性 |
| F6 | 完整 audit_log 查詢 UI | 目前 audit 只在案場內可看 |
| F7 | CI 自動化 | GitHub Actions push 時跑測試 |
| F8 | Error Tracking | Sentry Free + UptimeRobot |
| F9 | 台灣假日 2028 更新 | `TW_HOLIDAYS` 只到 2027 年底，2027 Q4 前需更新 |

---

## invoices 模組已知小議題（待回饋後決定要不要修）

- **無樂觀鎖**：draft 編輯只有 admin 在用，多人同編機率低，暫無加 `expected_updated_at`
- **未提供「沒有對應案場時保留歷史 case_id/case_name」**：若案場被刪，invoice_lines.project_id SET NULL 後失去案名顯示
- **status 流轉沒「revert」按鈕**：issued 後不能改回 draft（理論上不該，作廢即可）
- **API 沒做 batch suggest**：每選一個案場打一次 API，多選會多次請求

---

## 技術債（從上一份延續）

- `reports.vendor` 為純文字，未與 `vendors` 表 FK 關聯
- flask-limiter 使用 `memory://`，Vercel 多 instance 間不共享
- 測試腳本因 CSRF 無法直接跑，需考慮測試策略
