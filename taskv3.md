# 出帳管理系統 V3｜實作任務清單 TASK

**對應文件:** prdv3.md / sddv3.md v3.0
**分支:** v3-dev
**執行方式:** Claude Code 逐步實作，每個 Task 完成後測試再進下一個

---

## 前置狀態（已完成）

- [x] V2 已部署上線（認證 + 資料隔離 + 帳號管理 + 403 防護）
- [x] v3-dev 分支已建立
- [x] prdv3.md / sddv3.md 已完成

---

## Phase 1 — 資料庫遷移

### Task 1.1：建立 `migrate_v3.py` 遷移腳本
- **檔案：** `migrate_v3.py`
- **做什麼：**
  - reports 表新增 `is_locked BOOLEAN NOT NULL DEFAULT FALSE`
  - reports 表新增 `updated_by INTEGER REFERENCES users(id)`
  - reports 表新增 `updated_at TIMESTAMP`
  - 建立 `vendor_keywords` 表（id, keyword）
  - 寫入初始關鍵字：公司、行、工作室、企業、設計、工程、有限、股份、實業、工坊
  - 全部用 `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` 確保可重複執行
- **執行：** `python migrate_v3.py`
- **驗證：**
  - [ ] `SELECT is_locked, updated_by, updated_at FROM reports LIMIT 1` 不報錯
  - [ ] `SELECT COUNT(*) FROM vendor_keywords` 回傳 10

---

## Phase 2 — 發票號碼重複防呆

### Task 2.1：修改 POST /submit 加入發票檢查
- **檔案：** `app.py`
- **做什麼：**
  - 在 submit() 的驗證區塊，INSERT 之前加入：
  - 若 `invoice_no` 不為空，`SELECT id FROM reports WHERE invoice_no = %s`
  - 若已存在，append 錯誤「此發票號碼已存在，請確認是否重複請款」
  - invoice_no 為空時跳過（選填欄位）
- **驗證：**
  - [ ] 送出已存在的發票號碼 → 顯示紅字錯誤，表單保留已填值
  - [ ] 送出空的發票號碼 → 正常通過
  - [ ] 送出全新的發票號碼 → 正常通過

---

## Phase 3 — 案場鎖定機制

### Task 3.1：新增 POST /toggle-lock-project 路由
- **檔案：** `app.py`
- **做什麼：**
  - `@admin_required`
  - 接收 form 參數 `project_no` 和 `action`（lock / unlock）
  - `UPDATE reports SET is_locked = %s WHERE project_no = %s`
  - redirect 回 `/`

### Task 3.2：修改 GET / 查詢加入鎖定欄位
- **檔案：** `app.py`
- **做什麼：**
  - 管理員 SELECT 加入 `r.is_locked`, `r.updated_by`, `r.updated_at`, `u2.display_name as updater_name`（LEFT JOIN users u2 ON r.updated_by = u2.id）
  - 設計師 SELECT 加入 `r.is_locked`, `NULL as updated_by`, `NULL as updated_at`, `NULL as updater_name`
  - 新增案場查詢：`SELECT project_no, bool_or(is_locked), COUNT(*) FROM reports GROUP BY project_no ORDER BY project_no`
  - 傳入模板：`reports=rows, user=user, projects=projects`

### Task 3.3：修改 POST /delete 加入鎖定檢查
- **檔案：** `app.py`
- **做什麼：**
  - 現有的 SELECT 改為 `SELECT user_id, is_locked FROM reports WHERE id = %s`
  - 若 `is_locked = True`，abort(403)
  - 權限檢查維持不變

### Task 3.4：清單頁新增案場管理區塊
- **檔案：** `templates/list.html`
- **做什麼：**
  - 管理員限定，在 actions 下方加入 `<details>` 可展開面板
  - 顯示所有案場名稱 + 筆數 + 鎖定/解鎖按鈕
  - 每個按鈕是獨立 form，POST 到 `/toggle-lock-project`

### Task 3.5：清單頁鎖定列 UI
- **檔案：** `templates/list.html`, `static/style.css`
- **做什麼：**
  - 被鎖定的列加 `row-locked` class
  - 鎖定列顯示 🔒 標記
  - 鎖定列隱藏刪除按鈕
  - CSS 新增 `.row-locked`, `.project-lock-panel`, `.project-list`, `.project-item` 樣式
- **驗證：**
  - [ ] 管理員鎖定案場 X → X 的所有列顯示鎖頭、無刪除按鈕
  - [ ] 管理員解鎖案場 X → 恢復正常
  - [ ] 設計師仍可對已鎖定案場新增提報
  - [ ] 直接 POST /delete 鎖定列 → 403

---

## Phase 4 — 管理員全欄位 inline 編輯

### Task 4.1：新增 POST /update-report/<id> 路由
- **檔案：** `app.py`
- **做什麼：**
  - `@admin_required`
  - SELECT 檢查 is_locked，鎖定則 abort(403)
  - 取表單值：vendor, category, amount, invoice_no, invoice_date, remit_date, project_no
  - 發票防呆：invoice_no 不為空時 SELECT 檢查重複（排除自己 id）
  - 重複則 redirect `/?error=invoice_dup`
  - UPDATE 全部欄位 + `updated_by = user_id`, `updated_at = NOW()`
  - redirect 回 `/`

### Task 4.2：桌面版表格改為 inline 編輯（管理員）
- **檔案：** `templates/list.html`
- **做什麼：**
  - 管理員版的每個 `<td>` 改為 input 欄位
  - 使用 HTML `form` 屬性：`<input form="edit-{{ r[0] }}">`，各 input 散佈在 td 中
  - 每列尾端放 `<form id="edit-{{ r[0] }}" method="POST" action="/update-report/{{ r[0] }}">`
  - 欄位類型：
    - 名稱 → text input
    - 款項分類 → select（案場成本/管銷/獎金）
    - 請款金額 → number input
    - 發票收據編號 → text input
    - 發票收據日期 → date input
    - 匯款日期 → date input
    - 案場名稱 → text input
  - 鎖定列：全部改為純文字 + 🔒
  - 設計師版：維持現有純文字不變

### Task 4.3：手機版卡片改為 inline 編輯（管理員）
- **檔案：** `templates/list.html`
- **做什麼：**
  - 管理員版的卡片，每個 card-value 改為 input
  - 卡片底部一個儲存按鈕
  - 鎖定列：純文字 + 🔒，無儲存/刪除按鈕
  - 設計師版：維持現狀

### Task 4.4：新增 inline 編輯相關 CSS
- **檔案：** `static/style.css`
- **做什麼：**
  - `.inline-edit-input` 系列（text / number / date 寬度）
  - `.inline-edit-select`
  - `.error-banner`（發票重複提示條）
- **驗證：**
  - [ ] 管理員可 inline 修改所有欄位並儲存
  - [ ] 修改後 updated_by / updated_at 正確寫入
  - [ ] 鎖定列所有 input 消失、只剩文字
  - [ ] 修改發票號碼為重複值 → 頂部紅字提示
  - [ ] 設計師版清單無任何 input

### Task 4.5：清單頁錯誤提示
- **檔案：** `templates/list.html`
- **做什麼：**
  - 頂部加入條件渲染：`{% if request.args.get('error') == 'invoice_dup' %}` 顯示紅字 error-banner

---

## Phase 5 — 廠商相似性即時比對

### Task 5.1：新增 GET /api/check-vendor 路由
- **檔案：** `app.py`
- **做什麼：**
  - `from flask import jsonify`
  - `@login_required`
  - 參數 `q`（query string），長度 < 2 回空陣列
  - 取 vendor_keywords 所有關鍵字
  - 從使用者輸入和既有廠商名稱各自移除關鍵字，比對核心名稱
  - 回傳 `{'similar': [...]}`

### Task 5.2：建立 static/app.js
- **檔案：** `static/app.js`（新建）
- **做什麼：**
  - 監聽 `#vendor` 的 input 事件
  - debounce 300ms
  - fetch `/api/check-vendor?q=...`
  - 有相似結果：顯示 `#vendor-hint`（textContent，防 XSS）
  - 無結果或長度 < 2：隱藏

### Task 5.3：修改提報表單 UI
- **檔案：** `templates/new.html`
- **做什麼：**
  - 名稱 input 下方加 `<div id="vendor-hint" class="vendor-hint" style="display:none;"></div>`
  - 頁尾加 `<script src="/static/app.js"></script>`

### Task 5.4：新增提醒樣式
- **檔案：** `static/style.css`
- **做什麼：**
  - `.vendor-hint`（橘色背景、左側邊框）
- **驗證：**
  - [ ] 輸入「大明工程公司」，DB 有「大明設計公司」→ 顯示橘色提醒
  - [ ] 提醒不阻擋送出
  - [ ] 輸入完全不同名稱 → 無提醒
  - [ ] 輸入不到 2 字 → 無提醒

---

## Phase 6 — 審計軌跡顯示 + 報表驗證

### Task 6.1：桌面版表格顯示最後修改
- **檔案：** `templates/list.html`
- **做什麼：**
  - 表頭新增「最後修改」欄
  - 有 updater_name 時顯示「修改人 · mm/dd HH:MM」
  - 無則顯示「—」

### Task 6.2：手機版卡片顯示最後修改
- **檔案：** `templates/list.html`
- **做什麼：**
  - 卡片底部新增 card-footer
  - 有 updater_name 時顯示，無則不顯示

### Task 6.3：新增 card-footer CSS
- **檔案：** `static/style.css`
- **做什麼：**
  - `.card-footer`（上邊框 + 灰字 + 小字）

### Task 6.4：Excel 報表驗證
- **做什麼：**
  - 匯出 Excel，人工比對明細頁金額加總 = 網頁清單頁顯示
  - 確認鎖定/未鎖定資料都正常匯出
- **驗證：**
  - [ ] Excel 金額加總 = 網頁金額加總
  - [ ] 鎖定資料正常出現在 Excel

---

## Phase 7 — 部署 + 完整驗收

### Task 7.1：本地全功能測試
- **做什麼：** 跑 PRD V3 全部 17 項驗收標準

### Task 7.2：Git commit + merge
- **做什麼：**
  - v3-dev commit
  - merge 到 master
  - push

### Task 7.3：Vercel 部署
- **做什麼：**
  - `npx vercel --prod`
  - 線上驗證登入 + 核心功能

### Task 7.4：線上完整驗收
- **做什麼：** 線上跑一遍 17 項驗收
- **驗收清單：**
  - [ ] 1. 設計師 A 看不到設計師 B 的資料
  - [ ] 2. 設計師無法存取管理員編輯功能
  - [ ] 3. 重複發票號碼 → 阻擋 + 紅字
  - [ ] 4. 管理員編輯時發票重複 → 阻擋
  - [ ] 5. 空發票號碼 → 不檢查
  - [ ] 6. 鎖定案場 → 編輯按鈕消失
  - [ ] 7. 鎖定案場 → 設計師仍可新增提報
  - [ ] 8. 解鎖案場 → 編輯恢復
  - [ ] 9. 鎖定列顯示鎖頭
  - [ ] 10. 管理員 inline 改全欄位
  - [ ] 11. 修改後 updated_by / updated_at 正確
  - [ ] 12. 清單顯示最後修改人+時間
  - [ ] 13. 相似廠商即時提醒
  - [ ] 14. 提醒不阻擋送出
  - [ ] 15. 不相似不提醒
  - [ ] 16. Excel 金額 = 網頁金額
  - [ ] 17. 鎖定不影響 Excel 匯出
