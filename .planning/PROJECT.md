# Dawn Expense Tracker — V5 UI Redesign

## What This Is

Dawn 室內設計公司的內部出帳管理系統。設計師提報請款、管理員審核匯款、系統自動計算匯款日期並匯出 Excel。V5 目標是將 UI 從冷白 Apple 極簡風格改版為暖大地色系 + Bento Grid 排版，強化室內設計品牌識別，同時維持完美的手機自適應和 WCAG AA 無障礙標準。

## Core Value

設計師和管理員能在任何裝置上快速、無壓力地完成請款提報與審核，UI 視覺傳達「健康、自然、高級感」的室內設計品牌形象。

## Requirements

### Validated

- ✓ 請款提報 CRUD（新增/編輯/刪除） — V1
- ✓ Excel 匯出（明細 + 總覽 + 銀行資訊） — V1+V4
- ✓ RWD 手機/桌面雙版面 — V1
- ✓ 使用者認證（登入/登出/Session 7 天） — V2
- ✓ 角色權限（admin/designer）+ 資料隔離 — V2
- ✓ 帳號管理（新增/停用/啟用/重設密碼） — V2
- ✓ 發票防呆（category/金額驗證/重複擋） — V3
- ✓ 案場鎖定/解鎖 — V3
- ✓ 管理員全欄位 inline 編輯 — V3
- ✓ 廠商名稱智慧比對 + 重複偵測 — V3+V4
- ✓ Security Headers（CSP/X-Frame/nosniff） — V3
- ✓ 廠商匯款資料 CRUD + 批次匯入 — V4
- ✓ 銀行資訊自動帶入 — V4
- ✓ 匯款方式（現金/公司轉帳/個帳轉帳） — V4
- ✓ 匯款日期智慧預設（下月5日，跳週末+台灣假日） — V4
- ✓ 請款加總（廠商/匯款方式/總計 + 帳號資訊） — V4
- ✓ CSRF 防護（19 個表單） — V4+
- ✓ Session Cookie 安全（Secure+HttpOnly+SameSite） — V4+
- ✓ 69/69 scenario test 全通過 — V4+

### Active

- [ ] 暖大地色系色彩計畫（#F5F2ED 背景 + #333/#666 文字 + #4A5D4E/#7A6652 強調色）
- [ ] Noto Serif TC 標題 + Noto Sans TC 內文字型系統
- [ ] 全頁面 Bento Grid 排版（清單/新增/廠商/帳號管理）
- [ ] Dark Mode 大地色暗色版（跟隨系統偏好）
- [ ] WCAG AA 無障礙對比度全通過
- [ ] 按鈕微圓角（4-6px）+ 0.3s transition
- [ ] 手機端完美自適應（含 iPhone safe area）
- [ ] 字型載入優化（font-display: swap + 限定字重）

### Out of Scope

- 功能邏輯修改 — 純 UI 改版，不碰 app.py 路由/商業邏輯
- 新功能（分頁、篩選、Dashboard） — 另案處理
- DB 結構變更 — 無需
- Rate Limiting / 密碼複雜度 — 安全加固項，另案
- app.py 拆分重構 — 技術債，另案

## Context

- **技術棧**：Flask + Jinja2 + psycopg2 + Neon Postgres + Vercel Serverless
- **現有 CSS**：1,120 行 Apple 極簡風格，CSS custom properties 架構
- **流量分佈**：手機 51%，桌面 49%
- **使用者**：Dawn 管理員 + 2-3 位設計師
- **設計規範文件**：`prdv5.md`（完整色彩/字體/組件/無障礙驗證）
- **開發分支**：`v5-ui-redesign`（從 master 分出）
- **功能模組健康度**：14 模組中 11 個優秀、3 個可用，無需修復即可改版

## Constraints

- **純 CSS/模板改動**：不修改 app.py 商業邏輯，確保 69 項功能測試不受影響
- **WCAG AA**：所有色彩組合對比度 ≥ 4.5（正文）/ ≥ 3.0（大字），已預先驗證
- **字型效能**：CJK 字集大，必須限制字重載入（Serif 700 + Sans 400 only）
- **手機優先**：51% 流量來自手機，觸控區域最小 44px，input ≥ 16px

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 胡桃棕從 #8C7662 調整為 #7A6652 | 原色白字對比度 4.30 未達 WCAG AA 4.5 標準 | ✓ Good — 調整後 5.45 PASS |
| 雙強調色（森林綠+胡桃棕） | 綠色主 CTA + 棕色次要，豐富層次且不雜亂 | — Pending |
| Bento Grid 全頁面套用 | 統一視覺語言，表單頁用卡片包裹但內部線性 | — Pending |
| 保留 Dark Mode | 使用者已習慣跟隨系統，用大地色重設計暗色版 | — Pending |
| Google Fonts 載入策略 | font-display: swap + subset 限制，避免 CJK 全量載入白屏 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after initialization*
