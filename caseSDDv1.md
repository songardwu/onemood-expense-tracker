# caseSDDv1.md - 【一品沐：案場損益管理系統 — 系統設計文件】

> 對應 PRD：casePRDv2.md
> 版本：v1 | 日期：2026-04-16

---

## 1. 系統架構

### 1.1 技術棧

| 層級 | 技術 | 說明 |
|------|------|------|
| 後端 | Python Flask | SSR（Server-Side Rendering），Jinja2 模板 |
| 資料庫 | PostgreSQL | NUMERIC(12,2) 精度處理金額 |
| 前端 | HTML/CSS/Vanilla JS | 損益 Dashboard 區塊使用 JS fetch API 做即時計算 |
| 部署 | Vercel Serverless | 入口 `api/index.py` → `from app import app` |
| 認證 | Flask session + werkzeug | 密碼 hash、role-based access |
| CSRF | Flask-WTF CSRFProtect | 全域保護 |

### 1.2 模組架構

```
app.py                      ← Flask 初始化 + Blueprint 註冊
├── routes/
│   ├── auth.py              ← 登入/登出
│   ├── reports.py           ← 報帳 CRUD + 匯出 + 鎖定
│   ├── vendors.py           ← 廠商管理
│   ├── users.py             ← 帳號管理
│   └── projects.py          ← 案場損益模組（本文件主要範圍）
├── services/
│   └── utils.py             ← DB 連線、認證裝飾器、假日計算
├── templates/               ← Jinja2 模板
├── static/                  ← CSS + JS
├── migrations/              ← SQL schema 腳本
└── api/index.py             ← Vercel 入口
```

### 1.3 渲染策略

| 區塊 | 渲染方式 | 原因 |
|------|---------|------|
| 案場基本資料 | SSR (form POST + redirect) | 表單操作，不需即時更新 |
| 收入/收款/成本 | SSR (form POST + redirect) | CRUD 操作 |
| 損益 Dashboard | **SSR + JS fetch** | 頁面載入時 SSR 渲染初始值；成本/收入修改後用 JS fetch `/api/projects/<id>/summary` 即時更新數字，不需整頁刷新 |
| 分潤結算 | SSR | 管理者操作，低頻率 |

---

## 2. 資料模型

### 2.1 ER 關係圖

```
users (既有)
  │
  ├──< projects (1:N, designer_id)
  │       │
  │       ├──< project_adjustments (1:N, 追加減明細)
  │       ├──< project_discounts (1:N, 折讓/扣抵明細)
  │       ├──< project_payments (1:N, 收款明細)
  │       ├──< project_costs (1:N, 各科目成本)
  │       │       │
  │       │       └──> cost_categories (N:1, 科目定義)
  │       │
  │       └───> reports (0..1, bonus_report_id, 獎金出帳)
  │
  └──< audit_logs (1:N, changed_by)
```

### 2.2 資料表定義

#### projects（案場主檔）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| case_id | VARCHAR(20) | UNIQUE, NOT NULL | 流水號 `CASE-YYYYMMDD-NNN` |
| case_name | VARCHAR(200) | NOT NULL | 案名（手動輸入） |
| owner_name | VARCHAR(100) | | 業主姓名 |
| owner_phone | VARCHAR(30) | | 業主電話 |
| owner_address | VARCHAR(300) | | 業主地址 |
| contract_date | DATE | | 簽約日期 |
| construction_start | DATE | | 施工開始日 |
| construction_end | DATE | | 施工結束日 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | `active` / `completed` / `closed` |
| designer_id | INTEGER | FK → users(id), NOT NULL | 負責設計師 |
| system_furniture_amount | NUMERIC(12,2) | DEFAULT 0 | 系統家具金額 |
| non_system_furniture_amount | NUMERIC(12,2) | DEFAULT 0 | 非系統家具金額 |
| tax_amount | NUMERIC(12,2) | DEFAULT 0 | 5% 營業稅 |
| deposit_amount | NUMERIC(12,2) | DEFAULT 0 | 裝修押金 |
| deposit_refund | NUMERIC(12,2) | DEFAULT 0 | 實際退還金額 |
| deposit_status | VARCHAR(20) | DEFAULT 'pending' | `pending` / `partial` / `refunded` |
| profit_share_pct | NUMERIC(5,2) | DEFAULT 0 | 設計師分潤比 (%) |
| bonus_checked | BOOLEAN | DEFAULT FALSE | 管理者核對 |
| bonus_disbursed | BOOLEAN | DEFAULT FALSE | 已出帳 |
| bonus_report_id | INTEGER | FK → reports(id) | 關聯報帳紀錄 |
| created_at | TIMESTAMP | DEFAULT NOW() | |
| updated_at | TIMESTAMP | DEFAULT NOW() | |

**索引**：`idx_projects_designer(designer_id)`、`idx_projects_status(status)`

#### project_adjustments（追加減明細）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| project_id | INTEGER | FK → projects(id) CASCADE | |
| adjust_date | DATE | | 追加減日期 |
| description | VARCHAR(300) | | 說明 |
| amount | NUMERIC(12,2) | NOT NULL | 正=追加、負=減少 |
| created_at | TIMESTAMP | DEFAULT NOW() | |

#### project_discounts（折讓/扣抵明細）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| project_id | INTEGER | FK → projects(id) CASCADE | |
| item_name | VARCHAR(200) | NOT NULL | 項目名稱 |
| amount | NUMERIC(12,2) | NOT NULL | 折讓金額（正數） |
| created_at | TIMESTAMP | DEFAULT NOW() | |

#### project_payments（收款明細）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| project_id | INTEGER | FK → projects(id) CASCADE | |
| payment_date | DATE | NOT NULL | 收款日期 |
| payment_method | VARCHAR(20) | NOT NULL | `現金` / `匯款` / `其他` |
| amount | NUMERIC(12,2) | NOT NULL | 實收金額 |
| is_confirmed | BOOLEAN | DEFAULT FALSE | 管理者對帳確認 |
| confirmed_by | INTEGER | FK → users(id) | 確認人 |
| confirmed_at | TIMESTAMP | | 確認時間 |
| created_at | TIMESTAMP | DEFAULT NOW() | |

#### cost_categories（成本科目定義）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| name | VARCHAR(100) | NOT NULL | 科目名稱 |
| cost_type | VARCHAR(20) | NOT NULL | `system` / `non_system` |
| sort_order | INTEGER | DEFAULT 0 | 排序 |
| is_active | BOOLEAN | DEFAULT TRUE | 停用不刪除 |

**預設資料**：系統 6 項 + 非系統 9 項（詳見 migration SQL）

#### project_costs（案場成本）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| project_id | INTEGER | FK → projects(id) CASCADE | |
| category_id | INTEGER | FK → cost_categories(id) | |
| amount | NUMERIC(12,2) | DEFAULT 0 | 該科目合計金額 |

**唯一約束**：`UNIQUE(project_id, category_id)`

#### audit_logs（審計日誌）

| 欄位 | 型別 | 約束 | 說明 |
|------|------|------|------|
| id | SERIAL | PK | |
| table_name | VARCHAR(50) | NOT NULL | 來源資料表 |
| record_id | INTEGER | NOT NULL | 來源記錄 ID |
| field_name | VARCHAR(100) | NOT NULL | 被修改的欄位 |
| old_value | TEXT | | 舊值 |
| new_value | TEXT | | 新值 |
| changed_by | INTEGER | FK → users(id) | 修改人 |
| changed_at | TIMESTAMP | DEFAULT NOW() | |
| reason | TEXT | | 解鎖原因等 |

**索引**：`idx_audit_logs_table_record(table_name, record_id)`

---

## 3. 路由設計

### 3.1 案場基本資料（Phase 1 — 已實作）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/projects` | login_required | 案場列表（設計師看自己、管理者看全部） |
| GET | `/projects/new` | login_required | 新增案場表單 |
| POST | `/projects/create` | login_required | 建立案場，自動產生 case_id |
| GET | `/projects/<id>` | login_required + owner/admin | 案場詳情頁 |
| GET | `/projects/<id>/edit` | login_required + owner/admin | 編輯表單 |
| POST | `/projects/<id>/update` | login_required + owner/admin | 儲存編輯 |
| POST | `/projects/<id>/status` | login_required + 規則 | 狀態變更 |

**狀態變更規則**：
- `active → completed`：設計師或管理者
- `completed → closed`：僅管理者
- `closed → active`：僅管理者（需 audit log 記錄原因）

### 3.2 合約與收入（Phase 2）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| POST | `/projects/<id>/revenue` | login_required + owner/admin | 更新合約金額（系統/非系統家具、稅金） |
| POST | `/projects/<id>/deposit` | login_required + owner/admin | 更新押金資訊 |
| POST | `/projects/<id>/adjustments/add` | login_required + owner/admin | 新增追加減 |
| POST | `/projects/<id>/adjustments/<aid>/delete` | login_required + owner/admin | 刪除追加減 |
| POST | `/projects/<id>/discounts/add` | login_required + owner/admin | 新增折讓 |
| POST | `/projects/<id>/discounts/<did>/delete` | login_required + owner/admin | 刪除折讓 |

### 3.3 收款（Phase 2）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| POST | `/projects/<id>/payments/add` | login_required + owner/admin | 登錄收款 |
| POST | `/projects/<id>/payments/<pid>/delete` | login_required + owner/admin | 刪除收款 |
| POST | `/projects/<id>/payments/<pid>/confirm` | admin_required | 確認收款 |

### 3.4 支出成本（Phase 3）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| POST | `/projects/<id>/costs` | login_required + owner/admin | 批次更新成本（一次送所有科目） |
| GET | `/api/projects/<id>/summary` | login_required + owner/admin | JSON — 即時損益計算結果 |

### 3.5 成本科目管理（Phase 3）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/cost-categories` | admin_required | 科目列表 |
| POST | `/cost-categories/create` | admin_required | 新增科目 |
| POST | `/cost-categories/<cid>/update` | admin_required | 更新科目 |
| POST | `/cost-categories/<cid>/toggle` | admin_required | 啟用/停用 |

### 3.6 分潤結算（Phase 4）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| POST | `/projects/<id>/settlement` | admin_required | 設定分潤比 |
| POST | `/projects/<id>/bonus-check` | admin_required | 勾選/取消獎金核對 |
| POST | `/projects/<id>/bonus-disburse` | admin_required | 確認出帳 → 產生 reports 紀錄 |

### 3.7 審計日誌（Phase 4）

| 方法 | 路徑 | 權限 | 說明 |
|------|------|------|------|
| GET | `/projects/<id>/logs` | login_required + owner/admin | 顯示該案場所有變更紀錄 |

---

## 4. 權限矩陣

| 操作 | 設計師（本人案場） | 設計師（他人案場） | 管理者 |
|------|:---:|:---:|:---:|
| 查看案場列表 | O（僅自己） | X | O（全部） |
| 新增案場 | O | - | O |
| 編輯案場基本資料 | O（非結案） | X | O |
| 標記已完工 | O | X | O |
| 結案鎖定 | X | X | O |
| 解除結案 | X | X | O |
| 輸入合約金額 | O（非結案） | X | O |
| 登錄收款 | O（非結案） | X | O |
| 確認收款（對帳） | X | X | O |
| 輸入成本 | O（非結案） | X | O |
| 設定分潤比 | X | X | O |
| 勾選獎金核對 | X | X | O |
| 確認出帳 | X | X | O |
| 管理成本科目 | X | X | O |
| 查看審計日誌 | O（本人案場） | X | O |

---

## 5. 公式與計算邏輯

### 5.1 金額公式定義

所有金額使用 `NUMERIC(12,2)` 儲存，避免浮點誤差。

```
# 原簽約總金額
original_contract = system_furniture_amount + non_system_furniture_amount

# 追加減淨額
net_adjustment = SUM(project_adjustments.amount)  -- 含正負值

# 折讓/扣抵合計
total_discount = SUM(project_discounts.amount)

# 結算總價（應收金額）
settlement_price = original_contract + net_adjustment + tax_amount - total_discount
-- 註：押金不納入結算總價

# 押金扣抵
deposit_deduction = deposit_amount - deposit_refund

# 累計實收（僅已確認）
total_received = SUM(project_payments.amount) WHERE is_confirmed = TRUE

# 剩餘尾款
remaining_balance = settlement_price - total_received

# 系統工程成本
cost_system = SUM(project_costs.amount) WHERE category.cost_type = 'system'

# 非系統工程成本
cost_non_system = SUM(project_costs.amount) WHERE category.cost_type = 'non_system'

# 案場總成本
total_cost = cost_system + cost_non_system

# 案場利潤
profit = (original_contract + net_adjustment + total_discount + deposit_deduction) - total_cost
-- 註：稅金為代收代付不計入利潤
-- 註：折讓/扣抵因已收取故計入收入
-- 註：押金扣抵（客戶放棄部分）計入收入

# 設計師獎金
designer_bonus = profit * (profit_share_pct / 100)

# 公司收益
company_profit = profit - designer_bonus
```

### 5.2 即時計算 API 回應格式

`GET /api/projects/<id>/summary` 回傳 JSON：

```json
{
  "original_contract": 1500000,
  "net_adjustment": 50000,
  "tax_amount": 77500,
  "total_discount": 15000,
  "settlement_price": 1612500,
  "deposit_amount": 30000,
  "deposit_refund": 20000,
  "deposit_deduction": 10000,
  "total_received": 1200000,
  "remaining_balance": 412500,
  "cost_system": 450000,
  "cost_non_system": 380000,
  "total_cost": 830000,
  "profit": 715000,
  "profit_share_pct": 10,
  "designer_bonus": 71500,
  "company_profit": 643500,
  "bonus_checked": false,
  "bonus_disbursed": false,
  "bonus_report_id": null,
  "disbursed_amount": null,
  "bonus_diff": null
}
```

當 `bonus_disbursed = true` 時，額外回傳：
- `disbursed_amount`：已出帳金額（從 reports 取得）
- `bonus_diff`：`designer_bonus - disbursed_amount`（差異警示用）

### 5.3 押金狀態自動判定

```python
if deposit_refund == 0 and deposit_amount > 0:
    deposit_status = 'pending'     # 待退
elif deposit_refund < deposit_amount:
    deposit_status = 'partial'     # 部分退還
else:
    deposit_status = 'refunded'    # 已退
```

---

## 6. 前端頁面規格

### 6.1 頁面清單

| 頁面 | Template | 說明 |
|------|----------|------|
| 案場列表 | `projects.html` | Desktop 表格 + Mobile 卡片（已實作） |
| 新增/編輯案場 | `project_form.html` | 表單頁（已實作） |
| 案場詳情 | `project_detail.html` | 六區塊單頁呈現（Phase 2-4 逐步擴充） |

### 6.2 案場詳情頁區塊規劃

案場詳情頁採**單頁六區塊**設計，使用 Bento Grid 排版：

```
┌─────────────────────────┬─────────────────────────┐
│   區塊一：基本資料         │   施工資訊               │
│   (bento-cell--half)     │   (bento-cell--half)     │
├─────────────────────────┴─────────────────────────┤
│   區塊二：合約與收款進度 (bento-cell--full)            │
│   ┌───────────────┬───────────────────────────┐   │
│   │ 合約金額       │ 收款明細表格               │   │
│   │ 追加減明細     │ [新增收款] 按鈕            │   │
│   │ 折讓明細       │ 累計實收 / 剩餘尾款        │   │
│   │ 押金資訊       │                           │   │
│   └───────────────┴───────────────────────────┘   │
├───────────────────────────────────────────────────┤
│   區塊三：系統工程成本 (bento-cell--half)              │
│   區塊四：非系統工程成本 (bento-cell--half)            │
├───────────────────────────────────────────────────┤
│   區塊五：損益 Dashboard (bento-cell--full)           │
│   總成本 | 利潤 | 利潤率                              │
├───────────────────────────────────────────────────┤
│   區塊六：結算與分潤 (bento-cell--full)               │
│   分潤比 | 獎金 | 公司收益 | [核對] [確認出帳]        │
└───────────────────────────────────────────────────┘
```

### 6.3 視覺規則

| 情境 | 呈現 |
|------|------|
| 利潤為負 | 數值 `color: var(--red)` |
| 獎金為負 | 數值 `color: var(--red)` |
| 收款未確認 | 列背景 `opacity: 0.5`，左側「待確認」badge |
| 收款已確認 | 正常顯示，左側綠色「已確認」badge |
| 出帳後差異 | 橘色警示區塊，顯示差異金額 |
| 案場已結案 | 全頁操作按鈕 disabled，狀態 badge 橘色 |

---

## 7. 獎金出帳整合機制

### 7.1 出帳流程

```
[管理者設定分潤比]
        ↓
[Dashboard 顯示獎金數字]
        ↓
[管理者勾選「獎金核對」] → bonus_checked = TRUE
        ↓
[「確認出帳」按鈕啟用]
        ↓
[管理者點擊「確認出帳」]
        ↓
[後端建立 reports 紀錄]
  ├── vendor = users.display_name (WHERE id = designer_id)
  ├── category = '設計師獎金'
  ├── project_no = case_name
  ├── amount = designer_bonus
  ├── user_id = 管理者的 user_id
  └── RETURNING id → 存入 projects.bonus_report_id
        ↓
[projects.bonus_disbursed = TRUE]
```

### 7.2 出帳後差異偵測

每次載入案場詳情頁，當 `bonus_disbursed = TRUE` 時：

```python
disbursed_report = SELECT amount FROM reports WHERE id = bonus_report_id
current_bonus = profit * profit_share_pct / 100
diff = current_bonus - disbursed_report.amount

if diff != 0:
    顯示警示：「已出帳 {disbursed} / 目前應為 {current} / 差異 {diff}」
```

---

## 8. Audit Log 實作策略

### 8.1 觸發時機

| 操作 | table_name | field_name |
|------|-----------|------------|
| 修改合約金額 | projects | system_furniture_amount / non_system_furniture_amount |
| 修改稅金 | projects | tax_amount |
| 修改押金 | projects | deposit_amount / deposit_refund / deposit_status |
| 新增/刪除追加減 | project_adjustments | amount |
| 新增/刪除折讓 | project_discounts | amount |
| 新增/刪除收款 | project_payments | amount |
| 確認收款 | project_payments | is_confirmed |
| 修改成本 | project_costs | amount |
| 設定分潤比 | projects | profit_share_pct |
| 獎金核對 | projects | bonus_checked |
| 確認出帳 | projects | bonus_disbursed |
| 狀態變更 | projects | status |
| 結案解鎖 | projects | status（含 reason） |

### 8.2 寫入方式

在 `services/utils.py` 新增通用函式：

```python
def write_audit_log(cur, table_name, record_id, field_name,
                    old_value, new_value, user_id, reason=None):
    cur.execute("""
        INSERT INTO audit_logs (table_name, record_id, field_name,
                                old_value, new_value, changed_by, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (table_name, record_id, field_name,
          str(old_value) if old_value is not None else None,
          str(new_value) if new_value is not None else None,
          user_id, reason))
```

---

## 9. 安全設計

### 9.1 既有安全機制（延用）

- CSRF token 保護所有 POST 請求
- HTTP 安全 headers（X-Content-Type-Options、X-Frame-Options、CSP）
- Session cookie：HttpOnly、SameSite=Lax、Secure（生產環境）
- 密碼 werkzeug hash

### 9.2 案場模組新增安全措施

| 風險 | 防禦 |
|------|------|
| 越權存取他人案場 | 每個路由檢查 `designer_id == user.id` 或 `role == admin` |
| 結案後竄改 | `status == closed` 時拒絕所有寫入操作（admin 解鎖除外） |
| 金額注入 | 後端驗證所有金額為合法數字，使用參數化查詢 |
| 獎金重複出帳 | `bonus_disbursed` 為 TRUE 時，出帳按鈕 disabled |
| Audit Log 完整性 | 日誌表無 UPDATE/DELETE 路由，僅允許 INSERT |

---

## 10. 開發計畫與交付物

| Phase | 範圍 | 路由 | Template 變更 | 狀態 |
|-------|------|------|--------------|------|
| Phase 0 | Blueprint 重構 | 0 新增 | 0 | **已完成** |
| Phase 1 | DB Schema + 案場 CRUD | 7 路由 | 3 頁面 | **已完成** |
| Phase 2 | 收入/收款/押金/對帳 | 8 路由 | 擴充 project_detail | 待開發 |
| Phase 3 | 支出 + Dashboard + 科目管理 | 5 路由 + 1 API | 擴充 project_detail + 新頁面 | 待開發 |
| Phase 4 | 分潤 + 出帳 + Audit Log | 4 路由 | 擴充 project_detail | 待開發 |

### Phase 間依賴

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
                                  ↓           ↓
                            Dashboard      出帳整合
                          (需要成本資料)   (需要利潤計算)
```

Phase 2 和 Phase 3 的前端擴充都是在 `project_detail.html` 上逐步增加區塊，不會互相衝突。

---

## 11. AC 驗收對照表

| AC | 涉及 Phase | 驗證方式 |
|----|-----------|---------|
| AC1 裝修審查費 | Phase 3 | 輸入審查費 → 呼叫 summary API → 驗證 profit 減少 |
| AC2 折讓與應收 | Phase 2+3 | 新增折讓 → 驗證尾款減少 + 利潤不減少 |
| AC3 權限 | Phase 1-4 | 設計師 session 嘗試存取他人案場 → 403 |
| AC4 負數利潤 | Phase 3+4 | 成本 > 收入 → 獎金為負紅字 → 管理者不按出帳 |
| AC5 收款對帳 | Phase 2 | 新增收款(未確認) → total_received 不變 → 確認 → 計入 |
| AC6 押金扣抵 | Phase 2+3 | 設定 deposit_refund < deposit_amount → 驗證 profit 增加 |
| AC7 獎金出帳 | Phase 4 | 確認出帳 → 查詢 reports → 驗證欄位對應 |
| AC8 負數獎金 | Phase 4 | 負數獎金 → 不按出帳 → reports 無新紀錄 |
| AC9 差異警示 | Phase 4 | 出帳後修改成本 → 頁面顯示差異提醒 |
