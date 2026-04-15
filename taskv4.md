# TASK V4 — 廠商匯款資料管理（任務分解）

## Phase 1：DB Migration
- [T1] 建立 migrate_v4.py
  - CREATE TABLE vendors
  - ALTER TABLE reports ADD COLUMN payment_method
- [T2] 執行 migration，驗證表結構

## Phase 2：廠商管理頁 CRUD
- [T3] app.py — GET /vendors 路由
- [T4] app.py — POST /vendors/create 路由（設計師+管理員）
- [T5] app.py — POST /vendors/update/<id> 路由（admin only）
- [T6] app.py — POST /vendors/delete/<id> 路由（admin only）
- [T7] templates/vendors.html — 桌面表格 + 手機卡片
  - 管理員：inline 編輯 + 刪除
  - 設計師：純文字 + 新增表單
  - 錯誤訊息顯示（重複、缺欄位等）
- [T8] static/style.css — 廠商頁樣式

## Phase 3：批次匯入 + 範本下載
- [T9] app.py — GET /vendors/template 範本下載
- [T10] app.py — POST /vendors/import 批次匯入
  - 解析 Excel / CSV
  - 欄位對應（中文表頭）
  - 新增 / 更新 / 跳過邏輯
  - 回傳匯入結果統計
- [T11] vendors.html — 匯入表單 + 結果顯示區塊

## Phase 4：提報頁連結
- [T12] app.py — GET /api/vendor-bank API
- [T13] templates/new.html — 新增匯款方式 radio + 銀行資訊提示框
- [T14] static/app.js — 擴充：選廠商 → 查詢銀行資訊 → 顯示
- [T15] app.py — 修改 /submit，加入 payment_method 欄位

## Phase 5：清單頁 + inline 編輯
- [T16] app.py — 修改 index() 查詢加入 payment_method
- [T17] templates/list.html — 桌面/手機新增匯款方式欄
  - admin inline: select
  - designer: 純文字
- [T18] app.py — 修改 /update-report 加入 payment_method

## Phase 6：Excel 匯出合併
- [T19] app.py — 修改 export() 查詢 LEFT JOIN vendors
- [T20] app.py — 修改 write_detail_sheet col_map 加入新欄位

## Phase 7：整合測試
- [T21] 全功能手動 / 自動測試
- [T22] 部署驗證

---

## 依賴關係

```
T1─T2 → T3~T8（Phase 2 依賴 DB）
       → T9~T11（Phase 3 依賴 DB）
       → T12~T15（Phase 4 依賴 DB + Phase 2 的 vendors 資料）
T3~T8 + T15 → T16~T18（Phase 5 需要 payment_method 欄位）
T16~T18 → T19~T20（Phase 6 需要查詢結構）
All → T21~T22
```

## 預估異動量

| 檔案 | 新增/修改 | 預估行數 |
|------|----------|---------|
| migrate_v4.py | 新增 | ~20 |
| app.py | 修改 | +200 |
| templates/vendors.html | 新增 | ~250 |
| templates/new.html | 修改 | +30 |
| templates/list.html | 修改 | +40 |
| static/app.js | 修改 | +30 |
| static/style.css | 修改 | +50 |
