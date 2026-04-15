# PRD V4 — 廠商匯款資料管理

## 背景

目前系統只記錄請款資訊，但匯款時需要另外查廠商銀行帳戶。
V4 新增廠商匯款資料功能，讓管理員與設計師能維護廠商銀行資訊，
並在提報流程、清單、匯出報表中自動帶入，減少人工查帳。

---

## 新增資料表：`vendors`

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | SERIAL PK | |
| name | VARCHAR UNIQUE NOT NULL | 廠商名稱（與 reports.vendor 關聯） |
| bank_name | VARCHAR NOT NULL | 銀行分行名稱（如：台北富邦銀行中山分行） |
| bank_code | VARCHAR NOT NULL | 銀行代碼（如：012-0456） |
| account_no | VARCHAR NOT NULL | 銀行帳號 |
| account_name | VARCHAR NOT NULL | 戶名 |
| created_by | INTEGER REFERENCES users(id) | 建立者 |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_by | INTEGER REFERENCES users(id) | 最後修改者 |
| updated_at | TIMESTAMP | |

- 一個廠商對應一組銀行帳戶（1:1，name 為 UNIQUE）

## 修改資料表：`reports`

| 新增欄位 | 型別 | 說明 |
|----------|------|------|
| payment_method | VARCHAR | 匯款方式：現金 / 公司轉帳 / 個帳轉帳 |

---

## 功能需求

### F1：廠商資料管理頁（/vendors）

- 所有登入使用者可查看廠商清單
- 顯示欄位：廠商名稱、銀行分行名稱、銀行代碼、帳號、戶名
- **設計師**：可新增，不可修改、不可刪除
- **管理員**：可新增、可 inline 修改、可刪除
- 入口：主清單頁加按鈕連結

### F2：批次匯入（/vendors/import）

- 支援 Excel（.xlsx）與 CSV（.csv）上傳
- 欄位對應：名稱、銀行分行名稱、銀行代碼、帳號、戶名
- 匯入邏輯：
  - 名稱不存在 → 新增
  - 名稱已存在 → **管理員**覆蓋更新 / **設計師**跳過並提示
- 匯入結果頁顯示：成功 N 筆、跳過 N 筆、失敗 N 筆（附原因）
- 權限：設計師、管理員皆可操作

### F3：提報連結 — 新增提報時自動帶入

- `/new` 頁面選擇廠商名稱後，自動顯示該廠商銀行資訊（唯讀提示）
- 新增「匯款方式」欄位（radio）：現金 / 公司轉帳 / 個帳轉帳
- 匯款方式為必填

### F4：清單頁顯示

- 清單表格/卡片新增顯示「匯款方式」欄位
- 管理員 inline 編輯可修改匯款方式

### F5：Excel 匯出合併

- 匯出明細表新增欄位：匯款方式、銀行分行名稱、銀行代碼、帳號、戶名
- 以 reports.vendor LEFT JOIN vendors.name 自動合併

### F6：匯入範本下載

- 提供「下載範本」按鈕（/vendors/template）
- 產出含表頭的空白 Excel 檔，方便使用者填寫後上傳

---

## 驗收標準

| # | 驗收項目 |
|---|---------|
| AC1 | 廠商管理頁可查看所有廠商銀行資訊 |
| AC2 | 設計師可新增廠商，不可修改/刪除 |
| AC3 | 管理員可新增、inline 修改、刪除廠商 |
| AC4 | Excel 批次匯入成功，重複名稱依權限處理 |
| AC5 | CSV 批次匯入成功 |
| AC6 | 匯入結果顯示成功/跳過/失敗統計 |
| AC7 | 新增提報選廠商後自動帶出銀行資訊 |
| AC8 | 新增提報必填匯款方式 |
| AC9 | 清單頁顯示匯款方式 |
| AC10 | 管理員可 inline 編輯匯款方式 |
| AC11 | Excel 匯出包含匯款方式 + 廠商銀行欄位 |
| AC12 | 範本下載功能正常 |
| AC13 | 權限控制正確（設計師不可改、不可刪廠商） |
| AC14 | 手機版 RWD 正常顯示 |

---

## 建議開發順序

1. DB migration（vendors 表 + reports.payment_method）
2. 廠商管理頁 CRUD（/vendors）
3. 批次匯入 + 範本下載
4. 提報頁連結（自動帶入 + 匯款方式）
5. 清單頁 + inline 編輯（匯款方式）
6. Excel 匯出合併
7. 測試驗收
