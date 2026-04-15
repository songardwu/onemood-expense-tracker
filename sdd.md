# 出帳管理系統｜系統設計文件 SDD

**版本:** v1.0 (MVP)
**對應 PRD:** prd.md v1.0
**用途:** 給 Claude Code 實作用的技術規格，涵蓋檔案結構、路由、資料庫操作、Excel 匯出邏輯、Vercel 部署設定

---

## 1. 技術棧

| 層級 | 技術 | 說明 |
|------|------|------|
| 後端框架 | Flask | 輕量 Python web framework |
| 資料庫 | Neon Postgres (Vercel) | 開發與正式環境共用同一個 |
| DB Driver | psycopg2-binary | 原生 SQL，不用 ORM |
| Excel 產出 | pandas + openpyxl | groupby 彙總 + 多頁籤 .xlsx |
| 前端 | HTML + 原生 CSS/JS | 不用任何前端框架 |
| 部署 | Vercel (Python Runtime) | serverless，GitHub 自動部署 |
| 環境變數 | python-dotenv | 本機讀 `.env.local` |

---

## 2. 專案檔案結構

```
onemood-expense-tracker/
├── api/
│   └── index.py              # Vercel serverless 入口
├── templates/
│   ├── base.html             # 共用 layout（head、PWA meta、nav）
│   ├── list.html             # 清單頁（首頁）
│   └── new.html              # 新增提報表單頁
├── static/
│   └── style.css             # RWD 樣式
├── app.py                    # Flask 主程式（路由 + DB 邏輯）
├── vercel.json               # Vercel 部署設定
├── requirements.txt          # Python 依賴清單
├── .env.local                # 本機環境變數（已存在，不進 git）
├── .gitignore
├── prd.md                    # 產品需求文件
└── sdd.md                    # 本文件
```

---

## 3. 資料庫設計

### 3.1 資料表（已建立）

```sql
CREATE TABLE reports (
  id SERIAL PRIMARY KEY,
  vendor TEXT NOT NULL,            -- 名稱
  vendor_type TEXT NOT NULL,       -- 廠商類型
  amount NUMERIC NOT NULL,         -- 請款金額
  category TEXT NOT NULL           -- 款項分類：案場成本 / 管銷 / 獎金
    CHECK (category IN ('案場成本', '管銷', '獎金')),
  invoice_no TEXT,                 -- 發票收據編號（選填）
  invoice_date DATE NOT NULL,      -- 發票收據日期
  remit_date DATE,                 -- 匯款日期（選填）
  project_no TEXT NOT NULL,        -- 案場名稱
  stage TEXT,                      -- 施工階段（選填）
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 連線方式

統一使用 Neon Postgres，開發與正式共用同一資料庫：

```python
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('.env.local')  # 本機開發時載入

def get_conn():
    url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    return psycopg2.connect(url)
```

**不做 SQLite 雙軌**——省掉兩套 SQL 方言的維護成本，開發即正式。

---

## 4. Flask 路由設計

### 4.1 路由總覽

| 方法 | 路徑 | 功能 | 回傳 |
|------|------|------|------|
| GET | `/` | 清單頁（首頁） | HTML |
| GET | `/new` | 新增提報表單 | HTML |
| POST | `/submit` | 寫入一筆提報 | redirect → `/` |
| POST | `/delete/<id>` | 刪除一筆提報 | redirect → `/` |
| GET | `/export` | 匯出 Excel | .xlsx 檔案下載 |

### 4.2 各路由細節

#### `GET /` — 清單頁

```python
@app.route('/')
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, vendor, vendor_type, amount, category,
               invoice_no, invoice_date, remit_date, project_no, stage, created_at
        FROM reports
        ORDER BY invoice_date DESC, created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('list.html', reports=rows)
```

#### `GET /new` — 新增表單頁

```python
@app.route('/new')
def new_report():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT vendor FROM reports ORDER BY vendor")
    vendors = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT vendor_type FROM reports ORDER BY vendor_type")
    vendor_types = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('new.html', vendors=vendors, vendor_types=vendor_types)
```

#### `POST /submit` — 寫入提報

```python
@app.route('/submit', methods=['POST'])
def submit():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (vendor, vendor_type, amount, category,
                             invoice_no, invoice_date, remit_date, project_no, stage)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        request.form['vendor'],
        request.form['vendor_type'],
        request.form['amount'],
        request.form['category'],
        request.form.get('invoice_no') or None,
        request.form['invoice_date'],
        request.form.get('remit_date') or None,
        request.form['project_no'],
        request.form.get('stage') or None,
    ))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

**伺服器端驗證：** 檢查必填欄位不為空、`amount` 為正數、`category` 為三個允許值之一。驗證失敗回傳表單頁並顯示錯誤訊息。

#### `POST /delete/<id>` — 刪除提報

```python
@app.route('/delete/<int:report_id>', methods=['POST'])
def delete(report_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')
```

#### `GET /export` — 匯出 Excel

詳見第 5 節。

---

## 5. Excel 匯出邏輯

### 5.1 整體流程

```
使用者點「匯出 Excel」
  → GET /export
  → pandas 從 Postgres 撈全部 reports
  → 產出兩個 DataFrame（明細 + 總覽）
  → 用 ExcelWriter 寫入 BytesIO
  → 回傳為 .xlsx 檔案下載
```

### 5.2 頁籤一：明細

**排序：** 廠商類型 → 名稱 → 日期

**欄位：** 日期、廠商類型、名稱、案場名稱、階段、款項分類、請款金額、發票收據編號、匯款日期

**小計邏輯：**
- 每個廠商一列 Subtotal
- 每個款項分類一列 Subtotal by Category
- 最底下一列 Grand Total

```python
from io import BytesIO
import pandas as pd
from datetime import date

@app.route('/export')
def export():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT invoice_date, vendor_type, vendor, project_no, stage,
               category, amount, invoice_no, remit_date
        FROM reports
        ORDER BY vendor_type, vendor, invoice_date
    """, conn)
    conn.close()

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        write_detail_sheet(df, writer)
        write_summary_sheet(df, writer)
    output.seek(0)

    today_str = date.today().strftime('%Y%m%d')
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'出帳報表_{today_str}.xlsx'
    )
```

### 5.3 明細頁籤產出函式

```python
def write_detail_sheet(df, writer):
    """
    產出明細頁籤，含廠商小計、分類小計、總計列。
    """
    rows = []
    col_map = {
        'invoice_date': '發票收據日期', 'vendor_type': '廠商類型', 'vendor': '名稱',
        'project_no': '案場名稱', 'stage': '階段', 'category': '款項分類',
        'amount': '請款金額', 'invoice_no': '發票收據編號', 'remit_date': '匯款日期'
    }

    # 按廠商分組，插入小計列
    for vendor, group in df.groupby('vendor', sort=False):
        for _, row in group.iterrows():
            rows.append(row.to_dict())
        rows.append({
            'vendor': f'【{vendor} 小計】',
            'amount': group['amount'].sum()
        })

    # 按款項分類分計
    for cat, group in df.groupby('category'):
        rows.append({
            'category': f'【{cat} 分計】',
            'amount': group['amount'].sum()
        })

    # 總計
    rows.append({
        'vendor': '【總計】',
        'amount': df['amount'].sum()
    })

    result = pd.DataFrame(rows)
    result.rename(columns=col_map, inplace=True)
    result.to_excel(writer, sheet_name='明細', index=False)
```

### 5.4 總覽頁籤產出函式

```python
def write_summary_sheet(df, writer):
    """
    產出總覽頁籤：三類分計（本月/當年累計）、佔比、年度總計。
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    # 確保日期欄位是 datetime
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])

    year_df = df[df['invoice_date'].dt.year == current_year]
    month_df = year_df[year_df['invoice_date'].dt.month == current_month]

    categories = ['案場成本', '管銷', '獎金']
    summary_rows = []

    year_total = year_df['amount'].sum()

    for cat in categories:
        month_amount = month_df[month_df['category'] == cat]['amount'].sum()
        year_amount = year_df[year_df['category'] == cat]['amount'].sum()
        pct = (year_amount / year_total * 100) if year_total > 0 else 0
        summary_rows.append({
            '款項分類': cat,
            '本月請款金額': month_amount,
            '當年累計': year_amount,
            '佔比(%)': round(pct, 1)
        })

    # 合計列
    summary_rows.append({
        '款項分類': '合計',
        '本月請款金額': month_df['amount'].sum(),
        '當年累計': year_total,
        '佔比(%)': 100.0 if year_total > 0 else 0
    })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_excel(writer, sheet_name='總覽', index=False)
```

---

## 6. 前端設計

### 6.1 共用 Layout — `base.html`

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="theme-color" content="#4A90D9">
    <title>出帳管理</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

### 6.2 清單頁 — `list.html`

**桌面版：** 表格（`<table>`），欄位：日期、名稱、款項分類、請款金額、案場名稱、匯款日期、刪除按鈕

**手機版（≤ 768px）：** 隱藏表格，改為卡片式（`.card`），每張卡片一筆，關鍵資訊垂直排列

**頂端按鈕：**
- 「+ 新增提報」— 大按鈕，連結到 `/new`
- 「匯出 Excel」— 次要按鈕，連結到 `/export`

**刪除互動：**
```html
<form method="POST" action="/delete/{{ report.id }}"
      onsubmit="return confirm('確定要刪除這筆嗎？')">
    <button type="submit" class="btn-delete">刪除</button>
</form>
```

### 6.3 新增提報頁 — `new.html`

**表單結構：** 單欄垂直排列，所有欄位 label + input 堆疊

**datalist 自動建議：**
```html
<input list="vendor-list" name="vendor" required>
<datalist id="vendor-list">
    {% for v in vendors %}
    <option value="{{ v }}">
    {% endfor %}
</datalist>

<input list="vendor-type-list" name="vendor_type" required>
<datalist id="vendor-type-list">
    {% for vt in vendor_types %}
    <option value="{{ vt }}">
    {% endfor %}
</datalist>
```

**欄位細節：**
| 欄位 | HTML | 屬性 |
|------|------|------|
| 名稱 | `<input list="vendor-list">` | required |
| 廠商類型 | `<input list="vendor-type-list">` | required |
| 請款金額 | `<input type="number" inputmode="decimal" min="1">` | required, step="1" |
| 款項分類 | 三個 `<input type="radio" name="category">` | required |
| 發票收據編號 | `<input type="text">` | 選填 |
| 發票收據日期 | `<input type="date">` | required, 預設今天 |
| 匯款日期 | `<input type="date">` | 選填 |
| 案場名稱 | `<input type="text">` | required |
| 施工階段 | `<input type="text">` | 選填 |

**日期預設值：** 由後端傳入 `today = date.today().isoformat()`，前端 `value="{{ today }}"`

**送出按鈕：** 高度 48px 以上，放在表單最底部，寬度 100%

### 6.4 CSS RWD 策略 — `style.css`

```
Mobile first 設計

基礎樣式（手機）：
- 卡片式清單
- 表單單欄垂直
- 按鈕全寬、高 48px+
- input padding 14px+
- 字體 16px（防止 iOS 自動縮放）

@media (min-width: 769px) 桌面樣式：
- 清單改為 <table> 顯示
- 表單寬度限制 600px 置中
- 按鈕改為 inline 排列
```

**配色：** 簡潔中性色系，主色 `#4A90D9`，背景 `#F5F5F5`，卡片白底帶淡灰邊框

---

## 7. Vercel 部署設定

### 7.1 `api/index.py`

```python
import os
import sys

# 讓 Vercel 的 serverless function 能 import 根目錄的 app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
```

Flask app 的 `template_folder` 和 `static_folder` 需要指向正確路徑：

```python
# app.py 頂部
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
```

### 7.2 `vercel.json`

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

所有請求（含靜態檔案）都導向 Flask 處理。

### 7.3 `requirements.txt`

```
flask
psycopg2-binary
python-dotenv
pandas
openpyxl
```

### 7.4 環境變數

Vercel 已自動注入以下變數（透過 Neon 整合）：

| 變數 | 用途 |
|------|------|
| `POSTGRES_URL` | 主要連線字串（pooled） |
| `DATABASE_URL` | 同上備用 |
| `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` | 個別欄位 |

本機開發時由 `.env.local` 提供（已存在，已加入 `.gitignore`）。

---

## 8. 伺服器端驗證

在 `/submit` 路由中進行基本驗證：

| 檢查項目 | 規則 | 失敗處理 |
|----------|------|----------|
| 必填欄位 | vendor, vendor_type, amount, category, invoice_date, project_no 不為空 | 回傳表單頁 + 錯誤訊息 |
| 請款金額 | 必須為正數 | 回傳表單頁 + 錯誤訊息 |
| 款項分類 | 必須為「案場成本」「管銷」「獎金」之一 | 回傳表單頁 + 錯誤訊息 |

不做複雜驗證（如日期範圍、案場名稱格式）。資料庫的 CHECK constraint 是最後防線。

---

## 9. Claude Code 實作指令順序

以下是建議的實作步驟，每步完成後可立即測試：

### Phase 1 — 骨架跑起來
1. 建立 `requirements.txt`
2. 建立 `app.py`：Flask app 初始化 + `get_conn()` + `GET /` 路由（空清單頁）
3. 建立 `templates/base.html`：共用 layout + PWA meta tags
4. 建立 `templates/list.html`：清單頁模板（先顯示空狀態）
5. 建立 `static/style.css`：基礎 RWD 樣式
6. **測試：** `flask run` → 瀏覽器打開 localhost → 看到空清單頁

### Phase 2 — 新增功能
7. 加 `GET /new` 路由 + `templates/new.html` 表單頁
8. 加 `POST /submit` 路由（含伺服器端驗證）
9. **測試：** 新增一筆 → 回到清單頁看到新資料

### Phase 3 — datalist 自動建議
10. `/new` 路由撈 DISTINCT vendor / vendor_type，傳給模板
11. `new.html` 加入 `<datalist>` 元素
12. **測試：** 輸入第二筆時，下拉出現第一筆的廠商建議

### Phase 4 — 刪除功能
13. 加 `POST /delete/<id>` 路由
14. `list.html` 每筆加刪除按鈕 + confirm()
15. **測試：** 刪除一筆 → 清單立刻更新

### Phase 5 — Excel 匯出
16. 實作 `GET /export` 路由
17. 實作 `write_detail_sheet()`：明細頁籤 + 小計/分計/總計
18. 實作 `write_summary_sheet()`：總覽頁籤 + 本月/年度/佔比
19. **測試：** 輸入 8-10 筆測試資料 → 匯出 → 打開 Excel 驗證兩個頁籤

### Phase 6 — Vercel 部署
20. 建立 `api/index.py`
21. 建立 `vercel.json`
22. 建立 `.gitignore`
23. `git init` → push 到 GitHub
24. Vercel Dashboard 連結 GitHub repo → 自動部署
25. **測試：** 手機打開 `xxx.vercel.app` → 完整流程跑一遍

---

## 10. 驗收檢查清單

對應 PRD 第 9 節的 10 條驗收路徑：

- [ ] 手機打開網址，看到清單頁 + 「+ 新增提報」按鈕
- [ ] 點新增，進入表單，填完送出，回到清單看到新筆
- [ ] 第二次輸入時 datalist 出現歷史建議
- [ ] 連續輸入 8-10 筆，涵蓋三種分類
- [ ] 匯出 Excel，明細頁籤按廠商類型排序、有小計/總計
- [ ] 總覽頁籤顯示三類分計、佔比、年度累計
- [ ] 修改某筆日期為去年 → 重新匯出 → 年度累計數字改變
- [ ] 刪除功能正常（confirm → 刪除 → 清單更新）
- [ ] 手機 RWD 卡片式顯示正常
- [ ] 加到手機主畫面後可全螢幕開啟
