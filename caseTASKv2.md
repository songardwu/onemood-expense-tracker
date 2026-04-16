# caseTASKv2.md - 【一品沐：案場損益管理系統 — 開發任務清單】

> 對應 SDD：caseSDDv2.md | PRD：casePRDv2.md
> 版本：v2 | 日期：2026-04-16

---

## 狀態說明

- `[DONE]` 已完成
- `[TODO]` 待開發
- `[DEP]` 有前置依賴（括號內標明依賴項）

---

## Phase 0 — Blueprint 重構

> 目標：將單體 app.py 拆分為模組化架構，為案場模組建立乾淨的擴充基礎。

- [DONE] P0-1. 建立 `routes/` 和 `services/` 目錄結構
- [DONE] P0-2. 抽出 `services/utils.py`（DB 連線、認證裝飾器、假日計算）
- [DONE] P0-3. 抽出 `routes/auth.py`（登入/登出）
- [DONE] P0-4. 抽出 `routes/reports.py`（報帳 CRUD + 匯出 + 鎖定 + 廠商比對 API）
- [DONE] P0-5. 抽出 `routes/vendors.py`（廠商管理 CRUD + 匯入匯出）
- [DONE] P0-6. 抽出 `routes/users.py`（帳號管理）
- [DONE] P0-7. 重寫 `app.py` 為 Flask 初始化 + Blueprint 註冊（57 行）
- [DONE] P0-8. 驗證全部 23 條路由正確註冊，Vercel 入口相容

**完成定義**：所有現有功能不受影響，路由 URL 不變。

---

## Phase 1 — DB Schema + 案場基本資料 CRUD

> 目標：建立案場資料模型與基本增刪改查，設計師可建立並管理自己的案場。

- [DONE] P1-1. 設計完整 DB Schema（7 張表：projects, project_adjustments, project_discounts, project_payments, cost_categories, project_costs, audit_logs）
- [DONE] P1-2. 撰寫 `migrations/001_create_projects.sql`，含預設成本科目 seed data
- [DONE] P1-3. 建立 `routes/projects.py` Blueprint（7 條路由）
  - GET `/projects` — 案場列表（設計師看自己、管理者看全部）
  - GET `/projects/new` — 新增表單
  - POST `/projects/create` — 建立案場（自動產生 case_id 流水號）
  - GET `/projects/<id>` — 案場詳情
  - GET `/projects/<id>/edit` — 編輯表單
  - POST `/projects/<id>/update` — 儲存編輯
  - POST `/projects/<id>/status` — 狀態變更
- [DONE] P1-4. 建立 `templates/projects.html`（列表頁，Desktop 表格 + Mobile 卡片）
- [DONE] P1-5. 建立 `templates/project_form.html`（新增/編輯共用表單）
- [DONE] P1-6. 建立 `templates/project_detail.html`（詳情頁，區塊一：基本資料 + 施工資訊）
- [DONE] P1-7. 導覽列新增「案場管理」連結
- [DONE] P1-8. 新增 CSS（status-completed/closed badge、detail-table、form-grid）
- [DONE] P1-9. 在 `app.py` 註冊 projects Blueprint，驗證 30 條路由全數正確

**完成定義**：可新增、編輯、查看案場，狀態可流轉，權限隔離正確。

---

## Phase 2 — 收入 / 收款 / 押金 / 對帳確認

> 目標：完成合約金額管理、收款追蹤與對帳確認機制。對應 PRD 第二區塊。

### 合約收入

- [TODO] P2-1. 在 `project_detail.html` 擴充區塊二：合約金額表單
  - 系統家具金額 / 非系統家具金額 / 5% 營業稅
  - 顯示計算：原簽約總金額 = 系統 + 非系統
- [TODO] P2-2. 新增路由 `POST /projects/<id>/revenue` — 更新合約金額
  - 驗證：金額為合法數字
  - 權限：owner/admin + 非結案
  - 寫入 audit_log

### 追加減明細

- [TODO] P2-3. 在區塊二新增追加減明細子區塊
  - 表格：日期 / 說明 / 金額（含正負）/ 刪除按鈕
  - 底部新增表單：日期 + 說明 + 金額
  - 顯示淨追加減合計
- [TODO] P2-4. 新增路由 `POST /projects/<id>/adjustments/add` — 新增追加減
- [TODO] P2-5. 新增路由 `POST /projects/<id>/adjustments/<aid>/delete` — 刪除追加減
  - 寫入 audit_log

### 折讓/扣抵明細

- [TODO] P2-6. 在區塊二新增折讓明細子區塊
  - 表格：項目名稱 / 金額 / 刪除按鈕
  - 底部新增表單：項目名稱 + 金額
  - 顯示折讓合計
- [TODO] P2-7. 新增路由 `POST /projects/<id>/discounts/add` — 新增折讓
- [TODO] P2-8. 新增路由 `POST /projects/<id>/discounts/<did>/delete` — 刪除折讓
  - 寫入 audit_log

### 押金

- [TODO] P2-9. 在區塊二新增押金子區塊
  - 欄位：押金金額 / 實際退還金額 / 狀態（自動判定）
  - 顯示押金扣抵金額 = 押金 - 退還
- [TODO] P2-10. 新增路由 `POST /projects/<id>/deposit` — 更新押金資訊
  - 自動判定 deposit_status（pending / partial / refunded）
  - 寫入 audit_log

### 結算總價

- [TODO] P2-11. 在區塊二顯示結算總價計算結果
  - 公式：原簽約總金額 + 追加減淨額 + 5% 營業稅 - 折讓合計
  - SSR 計算，顯示在頁面上方

### 收款明細

- [TODO] P2-12. 在區塊二新增收款明細子區塊
  - 表格：日期 / 付款方式 / 金額 / 確認狀態 / 操作
  - 未確認列 `opacity: 0.5` + 「待確認」badge
  - 已確認列正常 + 「已確認」badge（綠色）
  - 底部新增表單：日期 + 付款方式（現金/匯款/其他 select）+ 金額
- [TODO] P2-13. 新增路由 `POST /projects/<id>/payments/add` — 登錄收款
  - 設計師登錄 → `is_confirmed = FALSE`
- [TODO] P2-14. 新增路由 `POST /projects/<id>/payments/<pid>/delete` — 刪除收款
  - 寫入 audit_log
- [TODO] P2-15. 新增路由 `POST /projects/<id>/payments/<pid>/confirm` — 確認收款
  - 權限：admin_required
  - 設定 confirmed_by、confirmed_at
  - 寫入 audit_log

### 收款彙整

- [TODO] P2-16. 在區塊二顯示收款彙整
  - 累計實收（僅已確認）/ 剩餘尾款（結算總價 - 累計實收）

### 驗證

- [TODO] P2-17. 在 `routes/projects.py` 的 `project_detail` 路由中查詢所有子表資料傳入 template
- [TODO] P2-18. 驗證 AC2（折讓減少尾款但計入利潤）— 前置：需 Phase 3 Dashboard
- [TODO] P2-19. 驗證 AC5（未確認收款不計入累計實收）
- [TODO] P2-20. 驗證 AC6（押金部分退還，扣抵金額正確）— 前置：需 Phase 3 Dashboard

**完成定義**：案場詳情頁完整顯示區塊二所有資訊，收款對帳機制運作正確，所有金額變更有 audit log。

**AC 覆蓋**：AC2（部分）、AC5、AC6（部分）

---

## Phase 3 — 支出明細 + 損益 Dashboard + 科目管理

> 目標：完成成本輸入與損益即時計算。對應 PRD 第三、四、五區塊。

### 成本科目管理

- [TODO] P3-1. 建立 `templates/cost_categories.html`（科目管理頁面）
  - 系統工程 / 非系統工程分區顯示
  - 每個科目：名稱 / 排序 / 啟用狀態 / 編輯按鈕
  - 底部新增表單：名稱 + 類型（system/non_system）
- [TODO] P3-2. 新增路由 `GET /cost-categories` — 科目列表（admin_required）
- [TODO] P3-3. 新增路由 `POST /cost-categories/create` — 新增科目
- [TODO] P3-4. 新增路由 `POST /cost-categories/<cid>/update` — 更新科目名稱/排序
- [TODO] P3-5. 新增路由 `POST /cost-categories/<cid>/toggle` — 啟用/停用
- [TODO] P3-6. 導覽列新增「成本科目」連結（僅管理者可見）

### 案場成本輸入

- [TODO] P3-7. 在 `project_detail.html` 擴充區塊三（系統工程成本）和區塊四（非系統工程成本）
  - 每個 bento-cell--half 一區
  - 表格：科目名稱 / 金額輸入框
  - 底部顯示小計 A / 小計 B
  - 一個「儲存成本」按鈕批次送出所有科目
- [TODO] P3-8. 新增路由 `POST /projects/<id>/costs` — 批次更新成本
  - 接收所有科目的 category_id + amount
  - UPSERT 到 project_costs（利用 UNIQUE 約束）
  - 逐筆比對舊值，有變動的寫入 audit_log
  - 權限：owner/admin + 非結案
- [TODO] P3-9. 在 `project_detail` 路由查詢 cost_categories + project_costs 傳入 template

### 損益 Dashboard

- [TODO] P3-10. 在 `project_detail.html` 擴充區塊五（損益分析 Dashboard）
  - 顯示：案場總成本 / 案場利潤 / 利潤率
  - 利潤為負 → `color: var(--red)`
  - 押金資訊：押金收入 / 實際退還 / 扣抵金額
- [TODO] P3-11. 新增 API 路由 `GET /api/projects/<id>/summary` — JSON 即時損益計算
  - 回傳完整計算結果（參見 SDD 5.2 格式）
  - 權限：login_required + owner/admin
- [TODO] P3-12. 撰寫前端 JS：成本儲存後 fetch summary API 更新 Dashboard 數字
  - 不需整頁刷新，僅更新區塊五的數值
  - 在 `static/app.js` 或新增 `static/project.js`

### 驗證

- [TODO] P3-13. 驗證 AC1（輸入裝修審查費 → 利潤與獎金同步扣除）
- [TODO] P3-14. 驗證 AC2（折讓減少尾款但正確計入利潤）— 完整驗證
- [TODO] P3-15. 驗證 AC6（押金扣抵正確計入利潤）— 完整驗證

**完成定義**：成本可輸入並即時反映到損益 Dashboard，科目可由管理者擴充，所有公式計算正確。

**AC 覆蓋**：AC1、AC2（完整）、AC6（完整）

---

## Phase 4 — 分潤結算 + 獎金出帳 + Audit Log + 結案鎖定

> 目標：完成分潤計算、獎金出帳整合、完整審計日誌、結案鎖定機制。對應 PRD 第六區塊 + 系統核心機制。

### 分潤設定

- [TODO] P4-1. 在 `project_detail.html` 擴充區塊六（結算與分潤）
  - 分潤比 (%) 輸入框（僅管理者可編輯）
  - 顯示：設計師獎金 / 公司收益
  - 獎金為負 → 紅字
- [TODO] P4-2. 新增路由 `POST /projects/<id>/settlement` — 設定分潤比
  - 權限：admin_required
  - 寫入 audit_log

### 獎金核對與出帳

- [TODO] P4-3. 在區塊六新增「獎金核對」勾選框 + 「確認出帳」按鈕
  - 核對未勾選 → 出帳按鈕 disabled
  - 核對已勾選 → 出帳按鈕啟用
  - 已出帳 → 兩個控制項都 disabled
- [TODO] P4-4. 新增路由 `POST /projects/<id>/bonus-check` — 勾選/取消獎金核對
  - 切換 bonus_checked
  - 寫入 audit_log
- [TODO] P4-5. 新增路由 `POST /projects/<id>/bonus-disburse` — 確認出帳
  - 前置檢查：bonus_checked = TRUE 且 bonus_disbursed = FALSE
  - 建立 reports 紀錄：
    - vendor = 設計師 display_name
    - category = '設計師獎金'
    - project_no = case_name
    - amount = 計算出的獎金
    - user_id = 管理者 id
  - 取得 RETURNING id → 存入 projects.bonus_report_id
  - 設定 bonus_disbursed = TRUE
  - 寫入 audit_log

### 出帳後差異警示

- [TODO] P4-6. 在區塊六新增差異警示區塊
  - 條件：bonus_disbursed = TRUE 且 current_bonus != disbursed_amount
  - 顯示：「已出帳 XX / 目前應為 YY / 差異 ZZ」
  - 樣式：橘色警示背景
- [TODO] P4-7. 在 summary API 中加入 disbursed_amount 和 bonus_diff 欄位

### Audit Log 完善

- [TODO] P4-8. 在 `services/utils.py` 新增 `write_audit_log()` 通用函式
- [TODO] P4-9. 回溯 Phase 2-3 所有寫入路由，確認每個金額/狀態變更都呼叫 audit_log
  - DEP: P4-8
- [TODO] P4-10. 新增路由 `GET /projects/<id>/logs` — 審計日誌頁面
  - 顯示該案場所有 audit_logs，按時間倒序
  - 欄位：時間 / 操作人 / 欄位 / 舊值 → 新值 / 原因
  - 權限：owner/admin
- [TODO] P4-11. 在 `project_detail.html` 新增「查看修改紀錄」連結

### 結案鎖定完善

- [TODO] P4-12. 完善結案鎖定邏輯：closed 狀態下所有寫入路由回傳 403
  - 涵蓋：revenue、deposit、adjustments、discounts、payments、costs、settlement、bonus
- [TODO] P4-13. 結案解鎖時，彈出原因輸入框，寫入 audit_log（含 reason 欄位）
  - 前端：JS confirm 或 modal 輸入原因
  - 後端：`POST /projects/<id>/status` 增加 reason 參數

### 權限最終驗證

- [TODO] P4-14. 驗證 AC3（設計師無法編輯分潤比及他人案場）
- [TODO] P4-15. 驗證 AC4（負數利潤 → 獎金負數紅字 → 管理者可選擇不出帳）
- [TODO] P4-16. 驗證 AC7（確認出帳 → reports 產生正確紀錄）
- [TODO] P4-17. 驗證 AC8（負數獎金 → 不按出帳 → 無紀錄產生）
- [TODO] P4-18. 驗證 AC9（出帳後修改成本 → 差異警示顯示）

**完成定義**：分潤計算正確、獎金出帳產生 reports 紀錄、差異警示運作、審計日誌完整、結案鎖定全面生效。

**AC 覆蓋**：AC3、AC4、AC7、AC8、AC9

---

## 任務統計

| Phase | 任務數 | 狀態 |
|-------|-------|------|
| Phase 0 | 8 | 全部 DONE |
| Phase 1 | 9 | 全部 DONE |
| Phase 2 | 20 | 全部 TODO |
| Phase 3 | 15 | 全部 TODO |
| Phase 4 | 18 | 全部 TODO |
| **合計** | **70** | **17 DONE / 53 TODO** |

## 依賴關係

```
P0 (DONE) → P1 (DONE) → P2 → P3 → P4
                          │     │     │
                          │     │     ├── P4-9 depends on P4-8
                          │     │     └── P4-6,7 depends on P4-5
                          │     │
                          │     ├── P3-10~12 depends on P3-7~9 (成本資料)
                          │     └── P3-13~15 完整驗證 AC (需 P2 資料)
                          │
                          ├── P2-17 整合查詢（所有 P2 子表）
                          └── P2-18,20 部分 AC 驗證延後到 P3
```

## AC 追蹤矩陣

| AC | 說明 | 相關任務 | 可驗證時機 |
|----|------|---------|-----------|
| AC1 | 裝修審查費 | P3-8, P3-11, P3-13 | Phase 3 完成後 |
| AC2 | 折讓與應收 | P2-6~8, P3-10~11, P3-14 | Phase 3 完成後 |
| AC3 | 權限 | P1-3, P4-2, P4-14 | Phase 4 完成後 |
| AC4 | 負數利潤 | P3-10, P4-1, P4-15 | Phase 4 完成後 |
| AC5 | 收款對帳 | P2-12~16, P2-19 | Phase 2 完成後 |
| AC6 | 押金扣抵 | P2-9~10, P3-10~11, P3-15 | Phase 3 完成後 |
| AC7 | 獎金出帳 | P4-5, P4-16 | Phase 4 完成後 |
| AC8 | 負數獎金出帳 | P4-3, P4-5, P4-17 | Phase 4 完成後 |
| AC9 | 出帳後差異 | P4-6~7, P4-18 | Phase 4 完成後 |
