# Task V6 — 開發執行清單

**對應：** prdv6.md V6.1 + sddv6.md
**分支：** `v5-ui-redesign`
**上線最低路徑：** Phase 1 → 2 → 3 → 5（Phase 4 為 SHOULD）

---

## Phase 1: Design Token System + Font Setup

### T1-01: 新增 @font-face fallback metric override

**檔案：** `static/style.css` line 1（新增在最頂部，`:root` 之前）
**做什麼：**
```css
@font-face {
    font-family: 'Noto Serif TC Fallback';
    src: local('PingFang TC'), local('Microsoft JhengHei');
    ascent-override: 88%;
    descent-override: 22%;
    line-gap-override: 0%;
    size-adjust: 97%;
}
```
**驗收：** CSS 解析無錯誤
**狀態：** [ ]

---

### T1-02: 重寫 `:root` — Primitive tokens

**檔案：** `static/style.css` line 12-39（覆寫現有 `:root`）
**做什麼：** 在 `:root` 頂部新增 primitive 層：
```css
:root {
    /* --- Primitive Tokens --- */
    --color-cream: #F5F2ED;
    --color-white: #FFFFFF;
    --color-charcoal: #333333;
    --color-warm-grey: #666666;
    --color-forest: #4A5D4E;
    --color-forest-dark: #3D4F41;
    --color-walnut: #7A6652;
    --color-walnut-dark: #6B5944;
    --color-red: #D64545;
    --color-red-light: rgba(214, 69, 69, 0.08);
    --color-green: #34c759;
    --color-green-light: rgba(52, 199, 89, 0.08);
    --color-orange: #ff9500;
    --color-orange-light: rgba(255, 149, 0, 0.08);
```
**驗收：** 純新增，不影響任何現有樣式
**狀態：** [ ]

---

### T1-03: 重寫 `:root` — Semantic tokens（覆寫現有值）

**檔案：** `static/style.css` 同一個 `:root` 區塊
**做什麼：** 將現有 semantic token 值改為引用 primitive：
```css
    /* --- Semantic Tokens (覆寫現有) --- */
    --bg: var(--color-cream);             /* was #f5f5f7 */
    --surface: var(--color-white);        /* was #ffffff — 不變 */
    --text-primary: var(--color-charcoal);/* was #1d1d1f */
    --text-secondary: var(--color-warm-grey); /* was #6e6e73 */
    --text-tertiary: #999;               /* was #aeaeb2 */
    --border: rgba(51, 51, 51, 0.12);    /* was #d2d2d7 */
    --border-light: rgba(51, 51, 51, 0.06); /* was #e8e8ed */
    --accent: var(--color-forest);        /* was #0071e3 藍→綠 */
    --accent-hover: var(--color-forest-dark);
    --accent-light: rgba(74, 93, 78, 0.08);
    --red: var(--color-red);
    --red-light: var(--color-red-light);
    --orange: var(--color-orange);
    --orange-light: var(--color-orange-light);
    --green: var(--color-green);
    --green-light: var(--color-green-light);
```
**注意：** 因為所有組件都引用這些 token，改值後全站自動變色。
**驗收：** 打開任何頁面 → 背景變暖奶油色、按鈕變森林綠
**狀態：** [ ]

---

### T1-04: 新增 semantic tokens — 按鈕/Bento/字型

**檔案：** `static/style.css` 同一個 `:root` 區塊
**做什麼：**
```css
    /* --- 新增 tokens --- */
    --accent-secondary: var(--color-walnut);
    --accent-secondary-hover: var(--color-walnut-dark);
    --btn-default: var(--color-charcoal);

    --font: 'Noto Sans TC', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
    --font-heading: 'Noto Serif TC', 'Noto Serif TC Fallback', 'PMingLiU', serif;
    --font-mono: "SF Mono", SFMono-Regular, Menlo, monospace;

    --bento-gap: 16px;
    --bento-radius: 12px;
    --bento-padding: 20px;

    --shadow-s: 0 1px 3px rgba(74, 93, 78, 0.06);
    --shadow-m: 0 4px 14px rgba(74, 93, 78, 0.08);
    --shadow-l: 0 8px 30px rgba(74, 93, 78, 0.10);
    --transition: 0.3s ease;

    --radius-s: 6px;    /* was 8px — 微圓角 */
    --radius-m: 8px;    /* was 12px */
    --radius-l: 12px;   /* was 16px */
    --radius-xl: 16px;  /* was 20px */
}
```
**驗收：** 無視覺變化（新 token 尚未被引用）
**狀態：** [ ]

---

### T1-05: 修改 CSP header

**檔案：** `app.py` line 164
**做什麼：**
```python
# Before
response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"

# After
response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'"
```
**驗收：** DevTools Console 無 CSP 錯誤
**狀態：** [ ]

---

### T1-06: 加 Google Fonts 到 base.html

**檔案：** `templates/base.html` line 6（`<meta name="viewport">` 之後）
**做什麼：**
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC&family=Noto+Serif+TC:wght@700&display=swap" rel="stylesheet">
```
**驗收：** Network tab 看到 fonts.googleapis.com 請求成功（200）
**狀態：** [ ]

---

### T1-07: 加 Google Fonts 到 login.html

**檔案：** `templates/login.html` line 6（login 不繼承 base.html，需單獨加）
**做什麼：** 同 T1-06 的三行 `<link>` 加入 login.html 的 `<head>`
**驗收：** 登入頁字型正確載入
**狀態：** [ ]

---

### T1-08: 修改 theme-color meta

**檔案：** `templates/base.html` line 8-9
**做什麼：**
```html
<!-- Before -->
<meta name="theme-color" content="#f5f5f7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">

<!-- After -->
<meta name="theme-color" content="#F5F2ED" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1E1A17" media="(prefers-color-scheme: dark)">
```
**同步修改：** `templates/login.html` line 7-8（相同變更）
**驗收：** 手機瀏覽器頂部狀態列顏色改為暖色
**狀態：** [ ]

---

### T1-09: Typography — heading 改 Serif

**檔案：** `static/style.css` line 110-124（Typography 區段）
**做什麼：**
```css
h1, h2, h3 {
    font-family: var(--font-heading);
}

h1 {
    font-size: 32px;       /* was 28px */
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.3;
    color: var(--text-primary);
    margin-bottom: 20px;
}

h2 {
    font-size: 24px;       /* was 20px */
    font-weight: 700;      /* was 600 */
    letter-spacing: -0.01em;
    line-height: 1.4;
    color: var(--text-primary);
    margin-bottom: 14px;
}
```
**驗收：** 所有頁面標題顯示 Noto Serif TC（宋體風格）
**狀態：** [ ]

---

### T1-10: Typography — body 改 Sans + 字級行高調整

**檔案：** `static/style.css` line 47-54（body 區段）
**做什麼：**
```css
body {
    font-family: var(--font);  /* 已被 T1-04 更新為 Noto Sans TC */
    font-size: 16px;           /* was 15px — 防 iOS zoom */
    line-height: 1.7;          /* was 1.5 — CJK 需要更多行高 */
    background: var(--bg);
    color: var(--text-primary);
    min-height: 100vh;
}
```
**驗收：** 內文字型為 Noto Sans TC；行距更寬鬆
**狀態：** [ ]

---

### T1-11: WCAG 對比度驗證註解

**檔案：** `static/style.css`（`:root` 區塊上方或下方）
**做什麼：** 加入 CSS 註解記錄對比度驗證結果：
```css
/*
 * WCAG AA Contrast Verification (Light Mode)
 * ──────────────────────────────────────────
 * #333 vs #F5F2ED = 11.31  PASS (text-primary vs bg)
 * #666 vs #F5F2ED = 5.14   PASS (text-secondary vs bg)
 * #FFF vs #4A5D4E = 7.08   PASS (white vs accent-primary)
 * #FFF vs #7A6652 = 5.45   PASS (white vs accent-secondary)
 * #FFF vs #333    = 12.63  PASS (white vs btn-default)
 * #4A5D4E vs #F5F2ED = 6.34 PASS (forest text vs bg)
 * #7A6652 vs #F5F2ED = 4.88 PASS (walnut text vs bg)
 */
```
**驗收：** 註解正確存在
**狀態：** [ ]

---

### T1-12: Phase 1 檢查點

**做什麼：**
1. 開 `/login` → 確認背景暖奶油色、標題 Serif、按鈕綠色、無 CSP 錯誤
2. 開 `/` → 確認全站變色、字型正確
3. 開 DevTools Network → 確認 Google Fonts 載入成功
4. 跑 69/69 測試 → 全數通過
**狀態：** [ ]

---

## Phase 2: Bento Grid + Template 重構

### T2-01: 新增 Bento Grid CSS

**檔案：** `static/style.css`（在 Summary Panel 區段之後，Responsive 之前，約 line 950）
**做什麼：**
```css
/* --- Bento Grid --- */
.bento-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--bento-gap);
    margin-bottom: 24px;
}

.bento-cell {
    background: var(--surface);
    border-radius: var(--bento-radius);
    padding: var(--bento-padding);
    box-shadow: var(--shadow-s);
}

@media (min-width: 768px) {
    .bento-grid {
        grid-template-columns: repeat(12, 1fr);
    }
    .bento-cell--hero { grid-column: span 8; }
    .bento-cell--side { grid-column: span 4; }
    .bento-cell--half { grid-column: span 6; }
    .bento-cell--full { grid-column: span 12; }
}
```
**驗收：** CSS 解析無錯誤（尚未套用到模板）
**狀態：** [ ]

---

### T2-02: `/new` 新增提報頁 — Bento 包裹（最優先）

**檔案：** `templates/new.html`
**做什麼：** 現有 `<form class="report-form">` 已被 `.card` 包裹（class 在 CSS）。改為 Bento 結構：
```html
<!-- line 10 附近：用 bento-grid 包裹整個表單 -->
<div class="bento-grid">
    <div class="bento-cell bento-cell--full">
        <form method="POST" action="/submit" class="report-form">
            <!-- 表單內容不動 -->
        </form>
    </div>
</div>
```
**注意：** 檢查現有 CSS 裡 `.card`（如果 new.html 用了的話）是否需要移除或調整。實際上 new.html 的表單是用 `report-form` class 包裹，外層有 form-group，可以直接用 bento-cell 替代外部 card。
**驗收：** 手機端表單正常顯示；桌面端表單置中於卡片內
**狀態：** [ ]

---

### T2-03: `/` 清單頁 — Bento Grid 結構

**檔案：** `templates/list.html`
**做什麼：** 將現有的線性結構改為 Bento Grid：
```html
<h1>出帳管理</h1>

{% if request.args.get('error') == 'invoice_dup' %}
<div class="error-banner">...</div>
{% endif %}

<div class="bento-grid bento-grid--list">
    <!-- 操作按鈕區 -->
    <div class="bento-cell bento-cell--full">
        <div class="actions">
            <a href="/new" class="btn btn-primary">+ 新增提報</a>
            <a href="/export" class="btn btn-secondary">匯出 Excel</a>
        </div>
        {% if user.role == 'admin' and projects %}
        <details class="project-lock-panel">
            <!-- 案場管理不動 -->
        </details>
        {% endif %}
    </div>

    <!-- 費用清單（table / mobile cards 不動） -->
    <div class="bento-cell bento-cell--full">
        {% if reports %}
        <table class="desktop-table">...</table>
        <div class="mobile-cards">...</div>
        {% endif %}
    </div>

    <!-- 請款加總（現有 summary-panel 改為 bento-cell） -->
    {% if totals %}
    <div class="bento-cell bento-cell--full">
        <!-- 現有 summary-panel 內容不動 -->
    </div>
    {% endif %}
</div>
```
**注意：** 不改 table/mobile-cards 的內部結構，只加 bento wrapper。
**驗收：** 桌面端 Grid 排列；手機端正確堆疊；資料顯示正確
**狀態：** [ ]

---

### T2-04: `/vendors` 廠商頁 — Bento Grid 結構

**檔案：** `templates/vendors.html`
**做什麼：** 將現有的 actions + section-card + table 結構包入 bento-grid：
```html
<div class="bento-grid">
    <div class="bento-cell bento-cell--full">
        <!-- 匯入/下載按鈕 actions -->
    </div>
    <div class="bento-cell bento-cell--full">
        <!-- 新增廠商表單（現有 vendor-add-panel） -->
    </div>
    <div class="bento-cell bento-cell--full">
        <!-- 廠商列表（現有 desktop-table + mobile-cards） -->
    </div>
</div>
```
**驗收：** 廠商頁三區塊用卡片顯示；手機堆疊正常
**狀態：** [ ]

---

### T2-05: `/users` 帳號管理頁 — Bento Grid 結構

**檔案：** `templates/users.html`
**做什麼：** 現有已有 `.section-card` 結構，加 bento wrapper：
```html
<div class="bento-grid">
    <div class="bento-cell bento-cell--full">
        <h2>新增帳號</h2>
        <form><!-- 不動 --></form>
    </div>
    <div class="bento-cell bento-cell--full">
        <h2>帳號清單</h2>
        <!-- 帳號列表不動 -->
    </div>
</div>
```
**驗收：** 兩張卡片顯示；手機堆疊正常
**狀態：** [ ]

---

### T2-06: `/login` 登入頁 — 微調

**檔案：** `templates/login.html`
**做什麼：** 登入頁已是置中卡片結構（`.login-body` + `.login-card`），不需要 Bento Grid。只需確認：
- `.login-card` 圓角改用 `var(--bento-radius)`
- 登入按鈕 class 維持 `btn btn-primary`（自動吃到森林綠）
**驗收：** 登入頁暖色背景 + 卡片 + 綠色按鈕
**狀態：** [ ]

---

### T2-07: 全域 input font-size ≥ 16px

**檔案：** `static/style.css`（Forms 區段，約 line 286）
**做什麼：** 在 Forms 區段頂部加入：
```css
input, select, textarea {
    font-size: max(16px, 1rem);
}
```
**驗收：** iOS Safari 點擊 input 不觸發自動縮放
**狀態：** [ ]

---

### T2-08: Responsive Bento 斷點調整

**檔案：** `static/style.css` line 985-1060（Responsive 區段）
**做什麼：** 確認現有斷點包含 Bento Grid collapse：
```css
/* 手機 (< 768px) — bento 全部 full-width */
/* 已在 T2-01 base styles 處理（grid-template-columns: 1fr） */

/* 小螢幕 (< 390px) */
@media (max-width: 389px) {
    .bento-cell {
        padding: 16px;  /* 從 20px 縮小 */
    }
    .bento-grid {
        gap: 12px;      /* 從 16px 縮小 */
    }
}
```
**同步：** 確認 safe area padding 仍有效（line 1052-1060）
**驗收：** 390px / 768px / 1200px 三斷點顯示正確
**狀態：** [ ]

---

### T2-09: Phase 2 測試檢查點

**做什麼：**
1. 跑 69/69 測試 → 全數通過
2. 人工抽驗 5 個場景：
   - [ ] 新增提報 → 送出成功（`/new` → `/submit` → redirect `/`）
   - [ ] 管理員 inline 編輯 → 更新成功
   - [ ] 廠商新增 → 出現在列表
   - [ ] 刪除報表 → 從列表消失
   - [ ] 匯出 Excel → 下載成功
3. 截圖確認 `/new` 手機版（390px）無 iOS zoom 問題
**狀態：** [ ]

---

## Phase 3: Component Restyling

### T3-01: Navbar — 移除毛玻璃、改實底

**檔案：** `static/style.css` line 57-78
**做什麼：**
```css
.navbar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--surface);            /* was rgba(255,255,255,0.72) */
    /* 移除 backdrop-filter + -webkit-backdrop-filter */
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
    height: 48px;
}

.nav-brand {
    font-family: var(--font-heading);  /* 新增：Noto Serif TC */
    font-weight: 700;
    font-size: 17px;
    color: var(--text-primary);
    text-decoration: none;
    letter-spacing: -0.02em;
}

.nav-link {
    color: var(--accent);  /* 自動吃到森林綠 */
}
```
**驗收：** Navbar 實底暖色；Dawn 品牌名顯示宋體
**狀態：** [ ]

---

### T3-02: Button — 圓角從膠囊改微圓角

**檔案：** `static/style.css` line 155-271
**做什麼：** 所有 `border-radius: 980px`（膠囊）改為 `border-radius: var(--radius-s)`（6px 微圓角）
涉及的 class：`.btn` (line 160), `.btn-save` (line 216), `.btn-delete` (line 232), `.btn-small` (line 246)

```css
.btn {
    border-radius: var(--radius-s);  /* was 980px */
    min-height: 44px;                /* 新增：觸控區域 */
}
.btn-save { border-radius: var(--radius-s); }
.btn-delete { border-radius: var(--radius-s); }
.btn-small { border-radius: var(--radius-s); }
```
**驗收：** 所有按鈕變微圓角（不再是膠囊形）
**狀態：** [ ]

---

### T3-03: Button — Primary 改 CTA 風格

**檔案：** `static/style.css` line 174-179
**做什麼：** `.btn-primary` 已引用 `--accent`，自動變森林綠。確認 hover 也正確：
```css
.btn-primary {
    background: var(--accent);       /* 自動 = #4A5D4E 森林綠 */
    color: #fff;
}
.btn-primary:hover {
    background: var(--accent-hover); /* 自動 = #3D4F41 */
}
```
**驗收：** 登入按鈕、新增提報送出按鈕 = 森林綠
**狀態：** [ ]

---

### T3-04: Button — Secondary 改地色風格

**檔案：** `static/style.css` line 181-187
**做什麼：** 現有 `.btn-secondary` 是白底 + accent 字 + border。改為可辨識的次要風格：
```css
.btn-secondary {
    background: var(--surface);
    color: var(--accent);
    border: 1px solid var(--border);
}
.btn-secondary:hover {
    background: var(--accent-light);  /* 淡森林綠背景 */
}
```
**驗收：** 匯出 Excel、下載範本按鈕 = 白底綠字
**狀態：** [ ]

---

### T3-05: 焦點環 — 全域改胡桃棕

**檔案：** `static/style.css`（新增在 Forms 區段內或之後）
**做什麼：**
```css
*:focus-visible {
    outline: 2px solid var(--accent-secondary);  /* #7A6652 胡桃棕 */
    outline-offset: 2px;
}
```
**驗收：** Tab 鍵遊走時焦點環為棕色（非藍色）
**狀態：** [ ]

---

### T3-06: 表單 label 紅星 — 維持紅色

**檔案：** 確認 `static/style.css` 中 `.required` class 仍用 `--red`
**做什麼：** 檢查確認，通常不需修改（已引用 token）
**驗收：** 必填欄位的 * 仍為紅色
**狀態：** [ ]

---

### T3-07: Summary Panel — 改 Bento Cell 風格

**檔案：** `static/style.css` line 858-946（Summary Panel 區段）
**做什麼：** 確認 summary-panel 的背景和圓角使用 token：
```css
.summary-panel {
    background: var(--surface);
    border-radius: var(--bento-radius);
    padding: var(--bento-padding);
    box-shadow: var(--shadow-s);
    /* 如果已被 bento-cell 包裹（Phase 2），則這些可以移除避免重複 */
}
```
**驗收：** 請款加總區塊樣式與其他 Bento 卡片一致
**狀態：** [ ]

---

### T3-08: Login 卡片 — 圓角和 brand

**檔案：** `static/style.css` line 136-152
**做什麼：**
```css
.login-card {
    border-radius: var(--bento-radius);  /* was var(--radius-xl) */
    box-shadow: var(--shadow-l);
}

.login-card h1 {
    font-family: var(--font-heading);  /* Noto Serif TC */
}
```
**驗收：** 登入卡片圓角一致；Dawn 文字顯示宋體
**狀態：** [ ]

---

### T3-09: 清除 Apple 風格殘留 — 全域掃描

**檔案：** `static/style.css`
**做什麼：** 搜尋並替換所有硬編碼的 Apple 色值：
- `#f5f5f7` → 應已被 `var(--bg)` 替代
- `#1d1d1f` → 應已被 `var(--text-primary)` 替代
- `#0071e3` → 應已被 `var(--accent)` 替代
- `#6e6e73` → 應已被 `var(--text-secondary)` 替代
- `rgba(0, 113, 227` → 應已被 `var(--accent-light)` 替代
- `-apple-system, BlinkMacSystemFont, "SF Pro Display"` → 已被 T1-04 覆寫

用 grep 搜尋：`grep -n "#f5f5f7\|#1d1d1f\|#0071e3\|#6e6e73\|SF Pro" static/style.css`
**驗收：** grep 結果為空（僅允許在 CSS 註解中出現）
**狀態：** [ ]

---

### T3-10: Phase 3 檢查點

**做什麼：**
1. 逐頁開啟 5 個頁面，確認零冷白/藍色殘留
2. 確認 Navbar 實底 + Dawn 宋體
3. 確認所有按鈕微圓角（非膠囊）
4. Tab 鍵遊走確認焦點環為胡桃棕
5. 跑 69/69 測試 → 全數通過
**狀態：** [ ]

---

## Phase 4: Dark Mode + 微互動（SHOULD — 不阻擋上線）

### T4-01: Dark Mode — 換色值

**檔案：** `static/style.css` line 1062-1106
**做什麼：** 覆寫 dark mode `:root` 色值為大地色暗色版：
```css
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #1E1A17;
        --surface: #2A2520;
        --text-primary: #E8E2D9;
        --text-secondary: #B8A898;
        --text-tertiary: #7A7068;
        --border: rgba(176, 158, 136, 0.2);
        --border-light: rgba(176, 158, 136, 0.1);
        --accent: #6B8F70;
        --accent-hover: #7DA882;
        --accent-light: rgba(107, 143, 112, 0.12);
        --accent-secondary: #A08B75;
        --accent-secondary-hover: #B09E88;
        --btn-default: #E8E2D9;
        --red: #FF6B6B;
        --red-light: rgba(255, 107, 107, 0.15);
        --green: #30d158;
        --green-light: rgba(48, 209, 88, 0.15);
        --shadow-s: 0 1px 3px rgba(20, 12, 4, 0.3);
        --shadow-m: 0 4px 14px rgba(20, 12, 4, 0.4);
        --shadow-l: 0 8px 30px rgba(20, 12, 4, 0.5);
    }

    .navbar {
        background: var(--surface);
    }
}
```
**同步：** 移除現有的 per-component dark overrides（line 1089-1105），因為組件已全部引用 token。
**驗收：** 系統切到 dark mode → 暖棕背景（非黑色/灰色）
**狀態：** [ ]

---

### T4-02: color-scheme meta

**檔案：** `templates/base.html`（`<head>` 內）、`templates/login.html`（`<head>` 內）
**做什麼：** 新增：
```html
<meta name="color-scheme" content="light dark">
```
**驗收：** dark mode 使用者載入時無白色閃爍
**狀態：** [ ]

---

### T4-03: 微互動 — 卡片 hover lift

**檔案：** `static/style.css`
**做什麼：**
```css
.bento-cell {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

@media (hover: hover) {
    .bento-cell:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-m);
    }
}
```
**驗收：** 桌面滑鼠移到卡片上有微升效果；手機無影響
**狀態：** [ ]

---

### T4-04: 微互動 — prefers-reduced-motion guard

**檔案：** `static/style.css`
**做什麼：**
```css
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```
**驗收：** 系統設定「減少動態效果」後所有動畫消失
**狀態：** [ ]

---

### T4-05: Print stylesheet 更新

**檔案：** `static/style.css` line 1108-1120
**做什麼：** 確認 print 強制 light mode 色值：
```css
@media print {
    :root {
        --bg: #fff;
        --surface: #fff;
        --text-primary: #000;
    }
    /* 其餘現有 print rules 不動 */
}
```
**驗收：** 列印預覽顯示白底黑字，無 dark mode 色值
**狀態：** [ ]

---

## Phase 5: QA + UAT

### T5-01: 69/69 功能測試

**做什麼：** `python test_scenario.py`
**驗收：** 69/69 PASS
**狀態：** [ ]

---

### T5-02: WCAG AA 對比度審計

**做什麼：** 用 WebAIM Contrast Checker 驗證 7 組 Light Mode 色彩組合（見 T1-11 的表）
**驗收：** 所有組合 ≥ 4.5:1（正文）/ ≥ 3.0:1（大字）
**狀態：** [ ]

---

### T5-03: iOS Safari 手機測試

**做什麼：**
1. 開 `/new`（最高頻頁面）→ 點每個 input → 確認無自動縮放
2. 確認 safe area padding（iPhone X+ 底部不被裁切）
3. 確認字型正確渲染（Serif 標題 + Sans 內文）
**驗收：** 無 zoom、無裁切、字型正確
**狀態：** [ ]

---

### T5-04: 4G 效能測試

**做什麼：**
1. Chrome DevTools → Network → Throttle: Fast 3G
2. 載入 `/new` 頁面
3. 記錄 FCP 和 TTI
**驗收：** FCP ≤ 2s、TTI ≤ 3s
**狀態：** [ ]

---

### T5-05: 桌面跨瀏覽器

**做什麼：** 開 Chrome + Edge + Firefox，逐頁確認 5 頁面
**驗收：** 無明顯視覺差異
**狀態：** [ ]

---

### T5-06: After 截圖

**做什麼：** `python take_screenshots.py`（修改 OUT_DIR 為 `docs/screenshots/after/`）
**驗收：** 10 張 After 截圖存入 `docs/screenshots/after/`
**狀態：** [ ]

---

### T5-07: Before/After 對比確認

**做什麼：** 逐頁比對 Before vs After 截圖（10 組）
**驗收：** 所有頁面明確改為大地色系；無冷白殘留；排版改為 Bento Grid
**狀態：** [ ]

---

### T5-08: git tag v4-final

**做什麼：** 在 master 分支上：
```bash
git tag v4-final
git push origin v4-final
```
**驗收：** tag 存在且可用（`git log v4-final --oneline -1`）
**狀態：** [ ]

---

### T5-09: UAT — 使用者驗收

**做什麼：**
1. 管理員當面看桌面版 5 頁面
2. 設計師用手機看 `/new` 新增提報頁 + `/` 清單頁
3. 收集回饋，記錄需調整項目
**驗收：** 管理員 + 設計師確認 OK
**狀態：** [ ]

---

### T5-10: 合併上線

**做什麼：**
```bash
git checkout master
git merge v5-ui-redesign
git push origin master
# Vercel 自動部署
```
**後續 1 小時內：** 自己手機開 `/new` 確認線上版正常
**後續 1-3 天：** 觀察期，問題時 `git revert` + 重新部署
**狀態：** [ ]

---

## 任務總覽

| Phase | 任務數 | MUST | SHOULD | 關鍵檔案 |
|-------|--------|------|--------|---------|
| 1: Token + Font | 12 | 12 | 0 | style.css, base.html, login.html, app.py |
| 2: Bento Grid | 9 | 9 | 0 | style.css, 5 templates |
| 3: Components | 10 | 10 | 0 | style.css |
| 4: Dark Mode + 動畫 | 5 | 0 | 5 | style.css, base.html, login.html |
| 5: QA + UAT | 10 | 10 | 0 | test_scenario.py, take_screenshots.py |
| **總計** | **46** | **41** | **5** | — |

**上線最低：41 tasks（Phase 1-3 + Phase 5）**
**完整版：46 tasks（含 Phase 4）**

---

*Task V6 — 2026-04-16*
*對應：prdv6.md V6.1 + sddv6.md*
