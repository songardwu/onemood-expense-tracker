# HANDOFF — 2026-05-03 Night

> 客戶請款單模組（invoices）完工日 / 接手指南

---

## 系統現況

- **狀態**：Production 穩定（13 張表 + 6 個 Blueprint 全上線）
- **URL**：https://onemood-expense-tracker.vercel.app
- **GitHub**：https://github.com/songardwu/onemood-expense-tracker
- **分支**：`master`（最新 commit `3a2f82f`，遠端已同步）
- **資料庫**：Neon PostgreSQL，13 張表（invoices/invoice_lines 已 migrate）

---

## 本次 Session 完成的工作（5 commits）

### Commit 1: `ed460f0` — UI 8 項改善
| 區塊 | 改動 |
|------|------|
| Navbar | 改森林綠 + 品牌圖示 + active 指示 |
| 按鈕 | hover shadow lift 取代 scale |
| 表格 | zebra stripe + accent header + 金額加粗 |
| 卡片 | 左側色帶（依分類上色） |
| 登入頁 | 三層漸層 + tagline + fadeInUp |
| 動畫 | 全站 fadeInUp/fadeIn + details 三角箭頭 |
| 空狀態 | 5 個 inline SVG 插圖 |
| Dashboard | 損益情感色 + 收款進度條 |

### Commit 2: `90d857a` — 文件整理
| 檔案 | 內容 |
|------|------|
| `sddv20260416.md` | 完整系統設計文件 |
| `HANDOFF20260416Night.md` | 簡潔交接版 |
| `TODO20260416Night.md` | 阻塞點 + 優先順序 |

### Commit 3: `33eaf3f` — invoices schema（cherry-pick from worktree）
| 檔案 | 內容 |
|------|------|
| `migrations/002_create_invoices.sql` | invoices + invoice_lines + project_payments.invoice_id |
| `migrate_v5.py` | 對 Neon 執行的腳本 |

### Commit 4: `bc42f0d` — HANDOFF 20260503 morning
- invoices 模組 7 項決策結論 + 下一步方向

### Commit 5: `3a2f82f` — invoices 模組完整實作（**今天主要工作**）
| 檔案 | 內容 |
|------|------|
| `routes/invoices.py` | 8 路由 + 1 API + 4 helper（~370 行） |
| `templates/invoices.html` | 列表（年/月/狀態篩選 + 分頁 + 空狀態） |
| `templates/invoice_form.html` | 新增/編輯（多行明細 + JS 動態加減 + 自動建議金額） |
| `templates/invoice_detail.html` | 檢視 + status 流轉 + 對應收款 |
| `app.py` | 註冊 invoices blueprint |
| `templates/base.html` | navbar 加「客戶請款」連結 |

---

## DB Migration 已執行

```
[OK] invoices table created
[OK] invoice_lines table created
[OK] project_payments.invoice_id added
[OK] indexes created
Migration v5 done.
```

---

## 已確認可運作

- [x] Flask app 載入正常
- [x] 9 個 invoices routes 全部註冊（`/invoices`, `/invoices/new`, ..., `/api/invoice-suggest/<pid>`）
- [x] 3 個 invoices templates Jinja2 編譯通過
- [x] 未登入存取 `/invoices` 正確 302 redirect
- [x] Production 部署成功（Vercel）
- [x] Admin 密碼已重設（臨時 `Dawn@2026`）
- [x] UI 8 項改善已 push 到 master 並部署

---

## 待驗證（你需要實際操作確認）

- [ ] 登入 → navbar「客戶請款」→ 列表能開
- [ ] 「+ 新增請款單」→ 填客戶/月份 → 加明細 → 選案場應自動帶建議金額
- [ ] 建立後 detail 頁顯示正確（明細表 + 開立按鈕）
- [ ] 「開立請款單」→ status 變 issued
- [ ] 「標記已收款」→ status 變 paid
- [ ] 「作廢」→ status 變 void
- [ ] designer 角色登入 → 只能看自己案場相關的請款單
- [ ] iOS / Edge / Firefox 跨瀏覽器
- [ ] 4G 慢速網路效能

---

## 接手應該先看的檔案

1. **`routes/invoices.py`** — 新模組主程式，跟 `routes/projects.py` 同風格
2. **`templates/invoice_form.html`** — 含 JS 動態加減行邏輯（純 vanilla JS）
3. **`migrations/002_create_invoices.sql`** — schema 設計
4. **`HANDOFF20260503.md`** — 上半天的決策紀錄（7 項議題結論）
5. **`TODO20260503night.md`** — 下一步優先順序

---

## 核心邏輯重點

### 編號生成
```
INV-YYYYMM-NNN  (例: INV-202605-001)
```
每月重新從 001 開始，跨月跨年自動分組。

### 權限
- **admin**：全 CRUD + 狀態流轉
- **designer**：只能看自己案場相關的 invoices（透過 `EXISTS (SELECT 1 FROM invoice_lines il JOIN projects p ...)` 子查詢過濾）

### 狀態機
```
draft ─┬─→ issued ─┬─→ paid ─→ void
       └─→ void    └─→ void
```
- `draft` 可編輯/刪除
- `issued` 後僅能流轉狀態（不可改內容）
- 每次轉狀態寫 `audit_logs`

### 半自動金額
- API `/api/invoice-suggest/<pid>` 計算 `settlement_price - total_received`
- 沿用 `_get_project_summary` 的計算邏輯（內部複製避免 circular import）
- 前端 select 變更時自動填入 description 與 amount，可手動覆蓋

---

## 環境設定

```bash
# 本地開發
python app.py

# Vercel 部署
vercel --prod

# Migration（已跑過 v5，後續若有 v6 才需跑）
python migrate_v5.py

# 環境變數狀態
SECRET_KEY      → Production [OK] / Development [OK] / Preview [BLOCKED] (需 Git 連結)
POSTGRES_URL    → 已設定
```

---

## 下一步建議

**先做 Admin 改密碼 + invoices UAT**。

UAT 完成且確認 invoices 流程順暢之後，最該做的是 **Dashboard 首頁總覽** — 因為現在 `/` 還是出帳列表，但你做完品牌化 navbar + invoices 模組後，老闆登入第一畫面應該是「全公司本月金流」總覽，而不是一堆細項。Dashboard 預估 1 天可完成（純 SQL aggregate + 卡片排版，無新表）。
