# 出帳管理系統｜實作任務清單 TASK

**對應文件:** prd.md / sdd.md v1.0
**執行方式:** Claude Code 逐步實作，每個 Task 完成後測試再進下一個

---

## 前置狀態（已完成）

- [x] Vercel CLI 安裝 (v51.2.1)
- [x] Vercel 帳號登入 (songardwu-2097s-projects)
- [x] Vercel 專案建立 (onemood-expense-tracker)
- [x] Neon Postgres 建立並連結 (neon-indigo-saddle)
- [x] `.env.local` 環境變數已產生
- [x] `reports` 資料表已建立（含 `remit_date` 欄位）
- [x] `psycopg2-binary`、`python-dotenv` 已安裝

---

## Phase 1 — 骨架跑起來

### Task 1.1：建立 `requirements.txt`
- **檔案：** `requirements.txt`
- **內容：** flask, psycopg2-binary, python-dotenv, pandas, openpyxl

### Task 1.2：建立 `app.py` 骨架
- **檔案：** `app.py`
- **做什麼：**
  - Flask app 初始化，設定 `template_folder`、`static_folder` 用 `BASE_DIR` 絕對路徑
  - `get_conn()` 函式：讀取 `POSTGRES_URL` 或 `DATABASE_URL`，回傳 psycopg2 connection
  - `GET /` 路由：從 reports 撈全部資料（ORDER BY invoice_date DESC, created_at DESC），傳給 `list.html`
  - `if __name__ == '__main__': app.run(debug=True)`
- **DB 欄位順序：** id, vendor, vendor_type, amount, category, invoice_no, invoice_date, remit_date, project_no, stage, created_at

### Task 1.3：建立 `templates/base.html`
- **檔案：** `templates/base.html`
- **做什麼：**
  - HTML5 文件，`lang="zh-Hant"`
  - PWA meta tags：viewport, apple-mobile-web-app-capable, apple-mobile-web-app-status-bar-style, theme-color (#4A90D9)
  - `<title>出帳管理</title>`
  - 引入 `/static/style.css`
  - `{% block content %}{% endblock %}`

### Task 1.4：建立 `templates/list.html`
- **檔案：** `templates/list.html`
- **做什麼：**
  - 繼承 `base.html`
  - 頂端兩個按鈕：「+ 新增提報」(連結 `/new`)、「匯出 Excel」(連結 `/export`)
  - 桌面版：`<table>` 顯示，欄位：發票收據日期、名稱、款項分類、請款金額、案場名稱、匯款日期、刪除
  - 手機版（≤768px）：卡片式 `.card`，每筆一張卡片
  - 空狀態顯示「目前沒有提報資料」
  - 請款金額顯示千分位格式
  - 匯款日期為空時顯示「-」

### Task 1.5：建立 `static/style.css`
- **檔案：** `static/style.css`
- **做什麼：**
  - Mobile first 設計
  - 基礎：字體 16px、背景 #F5F5F5、主色 #4A90D9
  - 按鈕：全寬、高 48px+、圓角
  - 「+ 新增提報」為主色填滿、「匯出 Excel」為外框樣式
  - 卡片：白底、淡灰邊框、padding 16px、margin-bottom 12px
  - 刪除按鈕：紅色小按鈕
  - `@media (min-width: 769px)`：卡片隱藏改顯示 table、按鈕 inline 排列
  - 表單 input：padding 14px、border-radius 8px、寬度 100%
  - 送出按鈕：高 48px、寬 100%、主色填滿

### Task 1.6：測試 Phase 1
- **指令：** `flask run` 或 `python app.py`
- **驗證：**
  - [ ] 瀏覽器打開 `http://localhost:5000`，看到空清單頁
  - [ ] 看到「+ 新增提報」和「匯出 Excel」按鈕
  - [ ] 空狀態文字「目前沒有提報資料」有顯示
  - [ ] 縮小視窗到手機寬度，版面正常切換

---

## Phase 2 — 新增提報功能

### Task 2.1：建立 `templates/new.html` 表單頁
- **檔案：** `templates/new.html`
- **做什麼：**
  - 繼承 `base.html`
  - 頁面標題「新增提報」
  - `<form method="POST" action="/submit">`
  - 欄位順序與規格：

    | 欄位 | name 屬性 | type | 必填 | 備註 |
    |------|-----------|------|------|------|
    | 名稱 | vendor | text + datalist (vendor-list) | required | |
    | 廠商類型 | vendor_type | text + datalist (vendor-type-list) | required | |
    | 請款金額 | amount | number, inputmode="decimal", min="1" | required | step="1" |
    | 款項分類 | category | radio | required | 案場成本 / 管銷 / 獎金 |
    | 發票收據編號 | invoice_no | text | 選填 | |
    | 發票收據日期 | invoice_date | date | required | value="{{ today }}" |
    | 匯款日期 | remit_date | date | 選填 | |
    | 案場名稱 | project_no | text | required | |
    | 施工階段 | stage | text | 選填 | |

  - datalist 由後端傳入 `vendors` 和 `vendor_types` 列表
  - 送出按鈕：「送出」，高 48px、寬 100%
  - 返回連結：「← 回清單」連結到 `/`
  - 錯誤訊息區：`{% if error %}` 顯示紅字提示

### Task 2.2：加入 `GET /new` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 撈 `SELECT DISTINCT vendor FROM reports ORDER BY vendor`
  - 撈 `SELECT DISTINCT vendor_type FROM reports ORDER BY vendor_type`
  - 傳入 `today = date.today().isoformat()`
  - render `new.html`，傳入 vendors, vendor_types, today

### Task 2.3：加入 `POST /submit` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 從 `request.form` 取得所有欄位
  - 伺服器端驗證：
    - vendor, vendor_type, amount, category, invoice_date, project_no 不為空
    - amount 轉為數字且 > 0
    - category 在 ['案場成本', '管銷', '獎金'] 之中
  - 驗證失敗：重新 render `new.html`，帶 error 訊息 + 保留已填欄位值
  - 驗證通過：INSERT INTO reports（9 個欄位），commit，redirect('/')
  - invoice_no、remit_date、stage 為空時存 None

### Task 2.4：測試 Phase 2
- **驗證：**
  - [ ] 點「+ 新增提報」進入表單頁
  - [ ] 所有欄位正常顯示，發票收據日期預設今天
  - [ ] 填完必填欄位按送出 → 回到清單頁看到新筆
  - [ ] 故意漏填必填欄位 → 看到錯誤提示
  - [ ] 請款金額手機上跳數字鍵盤
  - [ ] 清單頁的請款金額有千分位、匯款日期空的顯示「-」

---

## Phase 3 — datalist 自動建議

### Task 3.1：驗證 datalist 功能
- **不需要額外程式碼**，Task 2.1/2.2 已包含 datalist 實作
- **驗證：**
  - [ ] 新增第一筆（名稱：好工地、類型：水電）
  - [ ] 新增第二筆時，名稱欄位輸入「好」→ 下拉出現「好工地」建議
  - [ ] 類型欄位輸入「水」→ 下拉出現「水電」建議
  - [ ] 可以選擇建議，也可以打全新的值

---

## Phase 4 — 刪除功能

### Task 4.1：加入 `POST /delete/<id>` 路由
- **檔案：** `app.py`
- **做什麼：**
  - 接收 `report_id` 參數
  - `DELETE FROM reports WHERE id = %s`
  - commit，redirect('/')

### Task 4.2：清單頁加入刪除按鈕
- **檔案：** `templates/list.html`
- **做什麼：**
  - 每筆資料加一個 `<form method="POST" action="/delete/{{ id }}">`
  - `onsubmit="return confirm('確定要刪除這筆嗎？')"`
  - 紅色小按鈕「刪除」
  - 手機版卡片：刪除按鈕放在卡片右上角或底部

### Task 4.3：測試 Phase 4
- **驗證：**
  - [ ] 點刪除 → 跳出確認對話框
  - [ ] 按「取消」→ 不刪除
  - [ ] 按「確定」→ 該筆消失，清單立刻更新

---

## Phase 5 — Excel 匯出

### Task 5.1：實作 `GET /export` 路由
- **檔案：** `app.py`
- **做什麼：**
  - `pd.read_sql()` 撈全部 reports
  - 如果沒有資料，redirect('/') 並顯示提示
  - 呼叫 `write_detail_sheet(df, writer)` 和 `write_summary_sheet(df, writer)`
  - BytesIO 產出，`send_file()` 回傳
  - 檔名：`出帳報表_YYYYMMDD.xlsx`

### Task 5.2：實作 `write_detail_sheet()`
- **檔案：** `app.py`
- **做什麼：**
  - 欄位中英對照 col_map：
    - invoice_date → 發票收據日期
    - vendor_type → 廠商類型
    - vendor → 名稱
    - project_no → 案場名稱
    - stage → 階段
    - category → 款項分類
    - amount → 請款金額
    - invoice_no → 發票收據編號
    - remit_date → 匯款日期
  - 按廠商分組（groupby vendor, sort=False），每組後插入小計列
  - 按款項分類分計（groupby category），插入分計列
  - 最底下插入總計列
  - rename 欄位為中文，寫入「明細」頁籤

### Task 5.3：實作 `write_summary_sheet()`
- **檔案：** `app.py`
- **做什麼：**
  - 篩選當年資料（invoice_date 年份 == 今年）
  - 篩選當月資料（再篩月份 == 本月）
  - 三個分類（案場成本、管銷、獎金）各算：本月請款金額、當年累計、佔比(%)
  - 最後一列合計
  - 寫入「總覽」頁籤

### Task 5.4：測試 Phase 5
- **前置：** 確保資料庫有 8-10 筆測試資料，三種分類都有
- **驗證：**
  - [ ] 點「匯出 Excel」→ 下載 `出帳報表_YYYYMMDD.xlsx`
  - [ ] 打開 Excel，有「明細」和「總覽」兩個頁籤
  - [ ] 明細頁籤：按廠商類型排序、有廠商小計列、有分類分計列、有總計列
  - [ ] 總覽頁籤：三類分計、本月請款金額、當年累計、佔比、合計列
  - [ ] 手動改一筆日期為去年 → 重新匯出 → 當年累計數字變小（去年那筆不計入）

---

## Phase 6 — Vercel 部署

### Task 6.1：建立 `api/index.py`
- **檔案：** `api/index.py`
- **做什麼：**
  - `sys.path.insert` 把根目錄加入 path
  - `from app import app`

### Task 6.2：建立 `vercel.json`
- **檔案：** `vercel.json`
- **內容：**
  ```json
  {
    "version": 2,
    "builds": [
      { "src": "api/index.py", "use": "@vercel/python" }
    ],
    "routes": [
      { "src": "/static/(.*)", "dest": "/api/index.py" },
      { "src": "/(.*)", "dest": "/api/index.py" }
    ]
  }
  ```

### Task 6.3：建立 `.gitignore`
- **檔案：** `.gitignore`
- **內容：**
  ```
  .env.local
  __pycache__/
  *.pyc
  .vercel/
  dev.db
  *.xlsx
  ```

### Task 6.4：Git 初始化 + Push 到 GitHub
- **指令：**
  1. `git init`
  2. `git add` 所有檔案（排除 .gitignore 中的項目）
  3. `git commit -m "初版：出帳管理系統 MVP"`
  4. 建立 GitHub repo（用 `gh repo create`）
  5. `git push -u origin main`
- **注意：** 確認 `.env.local` 沒有被 commit

### Task 6.5：Vercel 部署
- **做什麼：**
  - Vercel 已連結專案 (onemood-expense-tracker)
  - 環境變數已透過 Neon 整合自動注入
  - `vercel --prod` 或 push 觸發自動部署
- **確認：** 部署成功拿到 `xxx.vercel.app` 網址

### Task 6.6：測試 Phase 6
- **驗證：**
  - [ ] 手機打開 `xxx.vercel.app`，看到清單頁
  - [ ] 新增一筆 → 清單更新
  - [ ] datalist 下拉建議正常
  - [ ] 刪除一筆 → 確認後消失
  - [ ] 匯出 Excel → 下載成功、兩頁籤內容正確
  - [ ] Safari/Chrome「加到主畫面」→ 全螢幕開啟正常

---

## 最終驗收（對應 PRD 第 9 節）

| # | 驗收項目 | 狀態 |
|---|---------|------|
| 1 | 手機打開網址，看到清單頁 + 「+ 新增提報」按鈕 | [ ] |
| 2 | 點新增，填完送出，回到清單看到新筆 | [ ] |
| 3 | 第二次輸入時 datalist 出現歷史建議 | [ ] |
| 4 | 連續輸入 8-10 筆，涵蓋三種分類 | [ ] |
| 5 | 匯出 Excel，明細頁籤按廠商類型排序、有小計/總計 | [ ] |
| 6 | 總覽頁籤顯示三類分計、佔比、年度累計 | [ ] |
| 7 | 改某筆日期為去年 → 重新匯出 → 年度累計數字改變 | [ ] |
| 8 | 刪除功能正常（confirm → 刪除 → 清單更新） | [ ] |
| 9 | 手機 RWD 卡片式顯示正常 | [ ] |
| 10 | 加到手機主畫面後可全螢幕開啟 | [ ] |
