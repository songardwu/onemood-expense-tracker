# HANDOFF — 2026-04-16 Night

> 接手指南：目前做到哪、改了什麼、下一步看什麼

---

## 系統現況

- **狀態**：Production，已部署至 Vercel
- **URL**：https://onemood-expense-tracker.vercel.app
- **分支**：`master`（最新 commit `9d69b86`）
- **資料庫**：Neon PostgreSQL，11 張表，schema 穩定

---

## 本次 Session 改動（3 commits）

### Commit 1: `2b84572` — 核心穩定性修復
| 檔案 | 改動 |
|------|------|
| `routes/reports.py` | 報表分頁從 Python 記憶體切片改為 SQL `COUNT` + `LIMIT/OFFSET`；廠商加總改 `GROUP BY` SQL 聚合 |
| `routes/projects.py` | 所有金額計算改用 `Decimal` 精度（新增 `_d()` helper）；除法用 `Decimal('100')` |
| `routes/vendors.py` | 硬刪除改軟刪除（`is_active` toggle）；匯入結果從 session 改 flask flash message |
| `templates/vendors.html` | 刪除按鈕改為啟用/停用 toggle；停用列加 `row-disabled` 樣式；flash message 顯示 |
| `templates/list.html` | 擴充錯誤訊息處理（missing_fields, invalid_category, invalid_method, invalid_amount） |
| `templates/project_detail.html` | 獎金出帳加 JS `confirm()` 二次確認，顯示金額 |

### Commit 2: `9d69b86` — 進階防護
| 檔案 | 改動 |
|------|------|
| `services/utils.py` | 新增 `check_optimistic_lock()` 函式 |
| `routes/projects.py` | 收入/押金/成本更新前加樂觀鎖檢查 |
| `templates/project_detail.html` | 表單加 `expected_updated_at` hidden field；conflict error banner |
| `routes/reports.py` | 廠商相似偵測加 `len(core) >= 2` 門檻，防止短字串誤判 |
| `routes/vendors.py` | 匯入結果改 flash（同 commit 1 延續） |

### Commit 3: `7ea8ee7` — 文件整理
| 檔案 | 改動 |
|------|------|
| `TODO.md` | 四份 TODO 整併為一份 |
| `taskv6.md` | 驗收清單更新為 42/46 完成 |
| `prdv6.md` | Section 15 清單更新 16/20 完成 |
| `templates/users.html` | 修復帳號列表雙重 bento-cell 包裝 |

---

## 已確認可運作

- [x] 報帳列表 SQL 分頁 + 篩選 + 匯出
- [x] 廠商軟刪除 toggle（啟用/停用）
- [x] 廠商匯入 flash message（不再存 session）
- [x] 案場損益 Decimal 精度計算
- [x] 樂觀鎖（併發編輯衝突偵測）
- [x] 獎金出帳 JS confirm
- [x] 廠商相似偵測不再對短名稱誤報
- [x] Vercel Production 部署正常

---

## 未確認 / 待驗證

- [ ] iOS Safari 實機 — input 不縮放、safe area
- [ ] Dark Mode — 各頁面可讀性
- [ ] 跨瀏覽器 — Edge / Firefox 桌面版
- [ ] 4G 慢速網路 — FCP ≤ 2s
- [ ] UAT — 管理員 + 設計師當面驗收

---

## 接手應該先看的檔案

1. **`app.py`** — Flask 主程式，所有設定與 Blueprint 註冊在此
2. **`services/utils.py`** — 共用工具函式（DB 連線、認證、分頁、樂觀鎖、審計）
3. **`routes/projects.py`** — 最複雜的模組，案場損益全部邏輯
4. **`routes/reports.py`** — 報帳核心，SQL 分頁和加總邏輯
5. **`migrations/001_create_projects.sql`** — 完整案場相關 schema
6. **`TODO.md`** — 整併後的待辦清單

---

## 環境設定

```bash
# 本地開發
cp .env.local.example .env.local   # 填入 POSTGRES_URL + SECRET_KEY
pip install -r requirements.txt
python app.py

# Vercel 部署
vercel --prod

# 環境變數（Vercel Dashboard）
SECRET_KEY        → Production ✅ / Development ✅ / Preview ❌（需 Git 連結）
POSTGRES_URL      → 已設定
```

---

## 下一步建議

**先做 Admin 密碼更換**（2 分鐘），這是唯一的安全風險。其餘 P1 項目可在本週內完成驗證。功能面已穩定，暫無需新增功能。
