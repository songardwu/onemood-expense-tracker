# 出帳管理系統｜教學用垂直切片 PRD

**版本:** v1.0 (MVP)
**用途:** Claude Code 實作課程教材,帶 Dawn 從 0 到 1 親手做一個跑得起來的款項登記與年度累計報表工具
**文件性質:** 產品需求規格書(給人看的版本),下一步會拿這份去跟 AI 討論產出 SDD.md

---

## 1. 背景

Dawn 是室內設計工作室的合夥人,負責管理公司的款項出帳——付給廠商的工程款、設計師獎金、辦公室管銷等等。目前的痛點非常具體:她在用 Excel 或紙本手動登帳,要查帳的時候還得回公司開電腦把表格印出來看。這件事她已經「有點受不了」——意思是她不只是覺得不方便,是已經在心裡決定「再這樣下去不行」。

Dawn 本人寫了一份相當精簡的 PRD,只有 7 個功能模組:登入、廠商主檔、款項提報、發票防呆、核對工作台、Excel 報表、歷史查詢。寫得很工程化,而且第二條驗收標準直接寫了「設計師 A 不能讀設計師 B 的資料」這種權限規格——這代表她有一定的工程背景,知道要寫什麼。但即使這麼精簡,放到一天的課裡面還是太多——權限分層、廠商主檔 CRUD、發票防呆、編輯介面、狀態切換,每一塊都要時間。

這份 PRD 把規劃砍到只剩一條主線——**手機友善的款項輸入 + 含年度累計的 Excel 報表**,作為這堂課的教材。一天做完之後,Dawn 會有一個雖然簡單但真的跑得起來的工具,而且**會直接部署到 Vercel + Postgres**,當天就能用手機打開正式網址登第一筆款項。

## 2. 這堂課要達成什麼

這份 PRD 不是要做一個明天就可以給設計師團隊用的完整商業系統,是要讓 Dawn 親身走一遍「從零到一 + 部署到雲」的完整過程。做完這一天,Dawn 應該要能理解:

- 怎麼用 Flask 寫一個能在手機跑的網頁工具
- 怎麼設計資料表 schema(雖然只有一張表)
- 怎麼用 HTML 的 datalist 做「自由輸入 + 下拉建議」
- 怎麼用 pandas 把資料庫的內容做 groupby 彙總,輸出多頁籤 Excel
- 怎麼把本機 Flask 應用部署到 Vercel + Postgres
- 怎麼跟 Claude Code 搭配做事,從寫 code 到部署一條龍

**做完的樣子:** 下午五點之前,Dawn 用手機打開 `xxx.vercel.app` 的網址,看到提報清單。按「新增」,輸入一筆「名稱:好工地 / 類型:水電 / 請款金額:35000 / 分類:案場成本 / 案場名稱:S001 / 階段:水電工程」(發票收據編號留空,因為是收據;匯款日期留空,因為還沒匯),按送出,清單立刻出現這一筆。再輸入幾筆,按「匯出 Excel」,下載一份 .xlsx,打開有兩個頁籤,明細頁籤按廠商類型排序、總覽頁籤顯示三類分計跟年度累計。

## 3. 誰會用、什麼情境

**只有一個使用者:** Dawn(室內設計工作室合夥人)

**唯一情境:**
Dawn 在工地、在咖啡店、在車上,拿出手機打開這個工具,新增一筆剛剛付給師傅的款項。輸入完按送出,就完事了。每月或每季她跟合夥人對帳的時候,在電腦上打開同一個網址,按「匯出 Excel」,下載對帳表跟年度總覽,跟合夥人一起看。

這份 PRD 不考慮其他設計師、不考慮權限分層、不考慮發票防呆、不考慮編輯介面,就一個人、一支手機、一個簡單的登帳跟匯報流程。

## 4. 主線的五個步驟

這份 PRD 只講一條流程,這條流程從頭到尾跑得通就算成功:

1. **打開網頁** — Dawn 用手機(或電腦)打開部署在 Vercel 上的網址,看到提報清單與「新增」按鈕
2. **輸入款項** — 點「新增」,進到提報頁面,填寫名稱、廠商類型、請款金額、款項分類(成本/管銷/獎金 三選一)、發票收據編號(選填)、發票收據日期、匯款日期(選填)、案場名稱、施工階段
3. **送出** — 按送出,系統把這筆寫進 Postgres,立刻回到清單頁,看到新增的這一筆。輸入過的廠商名稱跟廠商類型自動加入 datalist 建議清單
4. **匯出 Excel** — 在清單頁有「匯出 Excel」按鈕,按一下下載一份 .xlsx
5. **看年度總覽** — Excel 打開有兩個頁籤,明細頁籤是對帳明細,總覽頁籤是三類分計加年度累計

## 5. 功能要做哪些

### 5.1 提報清單頁(首頁)

打開網址第一個看到的畫面。一個簡單的清單,顯示所有提報,依日期由近到遠排。每一筆顯示:

- 日期
- 名稱
- 款項分類(成本/管銷/獎金)
- 請款金額
- 案場名稱
- 匯款日期(有填才顯示)
- (右側)刪除按鈕

頁面頂端有兩個按鈕:**「+ 新增提報」**(顯眼大按鈕)、**「匯出 Excel」**

頁面要 RWD:在手機上,清單變成卡片式;在電腦上,清單可以是表格式。

### 5.2 新增提報頁面

點「+ 新增提報」進入。一個簡單的表單:

| 欄位 | 類型 | 必填 | 備註 |
|------|------|------|------|
| 名稱 | text + datalist | 是 | 自由輸入,下拉自動補完 |
| 廠商類型 | text + datalist | 是 | 自由輸入,下拉自動補完 |
| 請款金額 | number | 是 | 手機顯示數字鍵盤 |
| 款項分類 | radio | 是 | 案場成本 / 管銷 / 獎金 |
| 發票收據編號 | text | 否 | 收據沒號碼就留空 |
| 發票收據日期 | date | 是 | 預設今天 |
| 匯款日期 | date | 否 | 尚未匯款就留空 |
| 案場名稱 | text | 是 | 例如 S001 |
| 施工階段 | text | 否 | 例如「水電工程」 |

按「送出」之後寫進資料庫,跳回清單頁,新筆出現在最上方。

**手機友善的細節:**
- 所有輸入框 padding 至少 14px,手指好按
- 金額欄位用 `<input type="number" inputmode="decimal">`,手機跳數字鍵盤
- 日期欄位用 `<input type="date">`,手機跳原生日曆
- 送出按鈕至少 48px 高,放在底部
- 整個表單在手機上是單欄垂直排列,不擠

### 5.3 廠商與類型的 datalist 自動建議

不做廠商主檔 CRUD。但每次有新的名稱或類型被輸入時,系統把它加進一個「歷史輸入清單」。下次輸入時,瀏覽器的 datalist 會顯示所有歷史輸入過的選項當作下拉建議,但使用者也可以打全新的。

技術上:
```html
<input list="vendor-list" name="vendor">
<datalist id="vendor-list">
  <option value="好工地">
  <option value="阿明木作">
  ...
</datalist>
```

`<option>` 的內容由後端從資料庫的「歷史廠商」 distinct 出來填進去。

### 5.4 Excel 報表匯出(主角)

點「匯出 Excel」按鈕後,系統用 pandas 從資料庫撈出所有提報,產出一份兩頁籤的 .xlsx:

**頁籤一:明細**
- 按「廠商類型 → 廠商名稱 → 日期」排序
- 同一廠商的多筆排在一起
- 欄位:日期、廠商類型、名稱、案場名稱、階段、款項分類、請款金額、發票收據編號、匯款日期
- 每個廠商小計列(Subtotal)
- 每個款項分類分計列(Subtotal by Category)
- 最底下總計列(Grand Total)

**頁籤二:總覽**
- 三類分計區塊:案場成本 / 管銷 / 獎金,各顯示「本月請款金額 / 當年累計」
- 三類佔比百分比
- 當年總計
- 給 Dawn 跟合夥人對話用

**技術細節:** pandas 寫法
```python
import pandas as pd
df = pd.read_sql("SELECT * FROM reports", conn)

# 明細頁籤
detail = df.sort_values(['vendor_type', 'vendor', 'date'])

# 總覽頁籤
this_year = df[df['date'].dt.year == today.year]
summary = this_year.groupby('category')['amount'].sum()

with pd.ExcelWriter('out.xlsx') as writer:
    detail.to_excel(writer, sheet_name='明細')
    summary.to_excel(writer, sheet_name='總覽')
```

### 5.5 刪除提報

清單頁每一筆右側有刪除按鈕。點下去跳出確認對話框「確定要刪除這筆嗎?」按確認就刪除,清單立刻更新。

不做修改功能。要改就刪掉重新輸入。

## 6. 資料表 schema(只有一張表)

```sql
CREATE TABLE reports (
  id SERIAL PRIMARY KEY,
  vendor TEXT NOT NULL,
  vendor_type TEXT NOT NULL,
  amount NUMERIC NOT NULL,
  category TEXT NOT NULL CHECK (category IN ('案場成本', '管銷', '獎金')),
  invoice_no TEXT,
  invoice_date DATE NOT NULL,
  remit_date DATE,
  project_no TEXT NOT NULL,
  stage TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`invoice_no` 沒有 UNIQUE constraint(因為很多是收據,沒號碼)。`vendor` 跟 `vendor_type` 沒有外鍵,直接存字串(沒有廠商主檔)。

開發階段用 SQLite,部署階段用 Vercel Postgres——schema 幾乎一樣,SQLite 的 SERIAL 改成 INTEGER PRIMARY KEY AUTOINCREMENT 即可。

## 7. 刻意不做的事(很重要)

| 不做的東西 | 為什麼不做 |
|-----------|-----------|
| 帳號登入、密碼 | MVP 階段只有 Dawn 一個人用 |
| 設計師 vs 管理員角色分層 | 沒登入就沒角色 |
| 「設計師 A 不能看 B 的資料」權限驗收 | 沒登入就沒權限 |
| 廠商主檔(廠商列表頁、新增廠商 modal) | 用 datalist 取代,省一塊 CRUD |
| 廠商銀行帳號、銀行代碼 | 不從系統匯款,登帳不需要 |
| 發票圖檔上傳 | 檔案處理另一塊工,V2 |
| 發票重複檢核(unique 索引) | 收據沒號碼,做了反而綁手綁腳 |
| 管理員 inline 編輯提報 | 改就刪,V2 再做編輯介面 |
| 已匯款狀態切換、轉歷史紀錄 | V2 做狀態機 |
| 月份/設計師/案場名稱/廠商類別篩選查詢 | 資料量小不需要,Excel 篩選就好 |
| Audit Log 修改記錄 | V2 做編輯時一起做 |
| 多公司、多工作室 | 只有 Dawn 一家 |
| 月結帳單列印 | Excel 就是帳單 |
| 設計師個人入口 | V2 做登入時補 |

## 8. 部署到 Vercel + Postgres(課程後半段)

這是 Dawn 的 MVP 跟一般教學切片不一樣的地方——做完主線之後,**最後 30-45 分鐘要把它部署到 Vercel**,讓 Dawn 帶走的不是「能在筆電跑的 demo」,而是「**晚上回家就可以用手機開始登帳的雲端工具**」。

### 8.1 為什麼選 Vercel + Postgres

- **Vercel**:免費額度夠 Dawn 一個人用一輩子。連結 GitHub 自動部署。免費 SSL。
- **Postgres**(Vercel 提供):serverless 環境不能用 SQLite(每次冷啟動檔案系統會重置),所以正式部署要用 Postgres。Vercel 內建 Postgres,一鍵建立。

### 8.2 部署流程(6 步)

**Step 1 — Flask 改成 Vercel handler**

在專案根目錄建一個 `api/index.py`,把 Flask app 暴露給 Vercel:

```python
# api/index.py
from app import app  # 你的 Flask app

# Vercel 會自動把 HTTP request 轉給這個 app
```

**Step 2 — SQLite 改成 Postgres**

開發階段用 SQLite,正式部署用 Vercel Postgres。改 connection 字串跟 driver:

```python
# 開發
DATABASE_URL = "sqlite:///dev.db"
# 正式
DATABASE_URL = os.environ['POSTGRES_URL']  # Vercel 自動注入
```

加裝 `psycopg2-binary` 跟 `python-dotenv`。

**Step 3 — 建 vercel.json**

```json
{
  "version": 2,
  "builds": [
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "api/index.py" }
  ]
}
```

**Step 4 — push 到 GitHub + 連 Vercel**

把專案 push 到一個 GitHub repo。在 Vercel Dashboard 點「Import Project」,選那個 repo,Vercel 自動偵測 Python 專案、自動安裝依賴、自動部署。幾分鐘後拿到 `xxx.vercel.app` 的網址。

**Step 5 — 在 Vercel 建 Postgres + 灌 schema**

在 Vercel Dashboard → Storage → Create → Postgres,一鍵建立。Vercel 會自動把 connection string 注入到環境變數 `POSTGRES_URL`。

在 Vercel 的 SQL Editor 跑一次建表 SQL(第 6 節的 schema)。

**Step 6 — 手機加到主畫面**

用手機 Safari 或 Chrome 打開 `xxx.vercel.app`,選「分享 → 加到主畫面」。一個圖示出現在手機桌面,點下去像 App 一樣全螢幕開啟。

從此 Dawn 就有一個自己的登帳 App。

## 9. 怎樣算做完了

課程結束前,跟著 Claude Code 建出來的系統,應該可以跑完下面這條路:

1. 用手機打開 `xxx.vercel.app`,看到空的提報清單跟「+ 新增」按鈕
2. 點「+ 新增」,進到表單頁面
3. 輸入「名稱:好工地 / 類型:水電 / 請款金額:35000 / 分類:案場成本 / 發票收據編號:空白 / 日期:今天 / 匯款日期:空白 / 案場名稱:S001 / 階段:水電工程」
4. 按送出,跳回清單頁,看到這筆出現在最上方
5. 再點「+ 新增」,輸入第二筆,輸入名稱「好工地」時下拉出現建議,輸入類型「水電」時也出現建議——代表 datalist 記憶有作用
6. 連續輸入 8-10 筆,涵蓋不同廠商、不同類型、三種分類都有
7. 按「匯出 Excel」,下載一份 .xlsx
8. 打開 Excel 看到兩個頁籤——「明細」按廠商類型排序、有小計、有總計;「總覽」顯示三類分計、佔比、年度累計
9. 在資料庫直接把某筆的日期改成去年,重新匯出,「總覽」頁籤的「當年累計」數字變了——證明年度邏輯有動
10. 用手機把 vercel.app 加到主畫面,從桌面圖示開啟,完整流程能跑

這條路跑得通 = 這堂課達成目的 = 這份 PRD 任務完成。

## 10. 技術跟時程

- **技術棧:** Flask + SQLite(本機) / Postgres(正式) + pandas + openpyxl
- **前端:** HTML + 原生 JavaScript(datalist、表單、按鈕)
- **部署:** Vercel + Vercel Postgres
- **時程:** 一天,大概 6–8 小時。前 5-6 小時做主線,後 30-45 分鐘做 Vercel 部署
- **誰寫 code:** 全程 Claude Code 寫,Dawn 負責下指令、驗收、確認
- **怎麼跑(本機):** Flask 啟動,瀏覽器 localhost,可以即時測試
- **怎麼跑(正式):** Vercel 自動部署,push 到 GitHub 觸發

**特別注意事項:**

- 開發階段 SQLite 跟正式階段 Postgres 的 schema 要保持一致——任何時候改 schema 都要兩邊一起改
- Vercel 的免費 Postgres 有空間限制,Dawn 一個人用一輩子也用不完,不用擔心
- 部署完之後,本機開發還是用 SQLite,不要每次都連 Vercel Postgres(會慢)

## 11. 下一步要做什麼

這份 PRD 完成之後,下一步是拿它去跟 AI 討論,產出 **SDD.md**(系統設計文件),內容包括:

- 專案檔案結構(api/index.py, app.py, templates/, static/)
- Flask 路由設計(/ 清單頁、/new 新增頁、/submit 送出、/delete/<id>、/export Excel 匯出)
- pandas 的 groupby 與 multi-sheet 寫法
- vercel.json 跟環境變數設定
- Postgres 跟 SQLite 的兼容寫法
- Claude Code 的實作指令順序

SDD.md 不在這份文件裡,會另外做。

---

**提醒:** 這份是教學用的砍到剩主線的版本,不是要拿去給設計師團隊用的正式系統。完整版請看 Dawn 自己寫的原版 PRD——登入、權限、廠商主檔、編輯介面、狀態切換、發票上傳那些東西,主線穩了之後再一塊一塊補回來。最重要的是:**今天部署到 Vercel 之後,Dawn 晚上回家就可以開始用手機登第一筆款項,徹底告別「要回公司開電腦印表格」的日子**。
