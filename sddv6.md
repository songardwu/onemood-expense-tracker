# SDD V6 — 系統設計文件（System Design Document）

## Dawn 出帳管理系統 V5 UI Redesign

**對應 PRD：** prdv6.md V6.1
**範圍：** `static/style.css` + 6 templates + `app.py` CSP 一行
**分支：** `v5-ui-redesign`

---

## 1. 現況分析

### 現有 CSS 架構（style.css, 1,120 行）

```
Line 1-54     :root tokens + Reset（已有 semantic token 架構）
Line 56-101   Navbar（毛玻璃 backdrop-filter）
Line 102-125  Container + Typography
Line 126-153  Login
Line 154-272  Buttons（.btn 系統）
Line 273-370  Back link + Forms + Radio group
Line 371-509  Messages + Desktop table + Inline edit
Line 510-636  Mobile cards + Badges + Actions
Line 637-704  Locked row + Project lock + Vendor hint + Bank info
Line 705-984  Section card + Vendor page + Summary panel + Dup warning
Line 985-1060 Responsive breakpoints（768px+ / 1200px+ / <390px / safe-area）
Line 1061-1106 Dark mode（@media prefers-color-scheme: dark）
Line 1108-1120 Print
```

### 關鍵發現

1. **已有 semantic token 架構** — `:root` 定義了 `--bg`, `--surface`, `--text-primary`, `--accent` 等 token，組件都引用 token 而非硬編碼色值。這是好消息：Phase 1 主要是換 token 值，不需要重寫組件。
2. **Dark mode 已用 token 覆寫模式** — `@media (prefers-color-scheme: dark)` 只覆寫 `:root` token + 少數組件。V5 可沿用此模式。
3. **無 Bento Grid** — 目前是線性佈局（`.container` → 區塊堆疊），需新增 Grid 層。
4. **Navbar 用毛玻璃** — `backdrop-filter: blur(20px)`，需改為實底。
5. **按鈕用 `--accent`（藍色）** — 需拆分為多個 accent token。

### 現有模板結構

| 模板 | 繼承 | 特殊結構 |
|------|------|---------|
| `base.html` | — | navbar + `.container` wrapper |
| `login.html` | 不繼承 base | 獨立 `.login-body` + `.login-card` |
| `list.html` | extends base | 桌面表格 `.desktop-table` + 手機卡片 `.mobile-cards` + 摘要面板 `.summary-panel` |
| `new.html` | extends base | `.card` 包裹表單 + `.form-group` |
| `vendors.html` | extends base | `.vendor-add-panel` + `.section-card` + 桌面表格/手機卡片 |
| `users.html` | extends base | `.section-card` + `.user-form` |

---

## 2. Token 遷移策略

### 設計決策：擴充現有 token，不重寫

現有 `:root` 有 ~20 個 token。V5 擴充為兩層（primitive + semantic），但保持向後相容：

```css
/* === BEFORE (V4) === */
:root {
    --bg: #f5f5f7;
    --accent: #0071e3;
    /* ... */
}

/* === AFTER (V5) === */

/* Layer 1: Primitives（新增，不被組件直接引用） */
:root {
    --color-cream: #F5F2ED;
    --color-charcoal: #333333;
    --color-warm-grey: #666666;
    --color-forest: #4A5D4E;
    --color-walnut: #7A6652;
    --color-white: #FFFFFF;
    --color-red: #D64545;
    --color-red-light: rgba(214, 69, 69, 0.08);
}

/* Layer 2: Semantics（覆寫現有 token 名稱 + 新增） */
:root {
    /* 覆寫現有 token（組件自動吃到新值） */
    --bg: var(--color-cream);
    --surface: var(--color-white);
    --text-primary: var(--color-charcoal);
    --text-secondary: var(--color-warm-grey);
    --border: rgba(51, 51, 51, 0.12);
    --border-light: rgba(51, 51, 51, 0.06);

    /* 拆分 accent 為多個角色（現有 --accent 改為 forest green） */
    --accent: var(--color-forest);          /* 主 CTA — 取代藍色 */
    --accent-hover: #3D4F41;                /* hover 加深 */
    --accent-light: rgba(74, 93, 78, 0.08);
    --accent-secondary: var(--color-walnut); /* 次要按鈕（新增） */
    --accent-secondary-hover: #6B5944;
    --btn-default: var(--color-charcoal);    /* 一般按鈕（新增） */

    /* 保留 status colors */
    --red: var(--color-red);
    --red-light: var(--color-red-light);
    --green: #34c759;                        /* 狀態綠，非品牌綠 */

    /* 覆寫 shadow（暖色調） */
    --shadow-s: 0 1px 3px rgba(74, 93, 78, 0.06);
    --shadow-m: 0 4px 14px rgba(74, 93, 78, 0.08);
    --shadow-l: 0 8px 30px rgba(74, 93, 78, 0.10);

    /* 覆寫 font */
    --font: 'Noto Sans TC', 'Microsoft JhengHei', 'PingFang TC', sans-serif;
    --font-heading: 'Noto Serif TC', 'Noto Serif TC Fallback', 'PMingLiU', serif;

    /* 新增 Bento token */
    --bento-gap: 16px;
    --bento-radius: 12px;
    --bento-padding: 20px;

    /* 覆寫 transition */
    --transition: 0.3s ease;
}
```

### 遷移的好處

因為現有組件全部引用 `--bg`, `--surface`, `--accent` 等 token，**只要替換 `:root` 值，80% 的組件自動變色**。只有以下需要額外處理：

| 需額外處理 | 原因 | 做法 |
|-----------|------|------|
| `.btn` 系統 | 需拆分為 CTA / secondary / default | 新增 `.btn-cta`, `.btn-secondary` class |
| `.navbar` | 毛玻璃 → 實底 | 移除 `backdrop-filter`，改 `background: var(--bg)` |
| `h1`, `h2` | 需改用 Noto Serif TC | 加 `font-family: var(--font-heading)` |
| 焦點環 | 預設藍色 → 胡桃棕 | 全域 `*:focus-visible { outline: 2px solid var(--accent-secondary) }` |
| `.radio-group` pill | 藍色 active → 森林綠 | 已用 `--accent`，自動吃到 |

---

## 3. 字型載入技術方案

### base.html `<head>` 變更

```html
<!-- 新增：Google Fonts preconnect + 載入 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC&family=Noto+Serif+TC:wght@700&display=swap" rel="stylesheet">

<!-- 修改：theme-color 改為大地色 -->
<meta name="theme-color" content="#F5F2ED" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1E1A17" media="(prefers-color-scheme: dark)">
```

### Fallback Font Metric Override（style.css 頂部）

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

目的：讓系統字型的尺寸盡量接近 Noto Serif TC，`font-display: swap` 發生時卡片高度跳動最小化。

### CSP Header 變更（app.py line 165）

```python
# Before
resp.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"

# After
resp.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'"
```

這是唯一的 `app.py` 變更。不改則 Google Fonts 被瀏覽器靜默擋掉。

---

## 4. Bento Grid 實作方案

### 設計決策

- **Bento 用於頁面結構面板**（固定數量的功能區塊）
- **Table/Card list 用於資料列表**（動態數量的資料庫資料）
- **不使用 `grid-auto-flow: dense`**（WCAG 2.4.3 tab order）
- **使用 `grid-template-areas`**（語義化、可讀性高）
- **Mobile-first**：base 是 1 欄，`@media (min-width: 768px)` 擴展

### CSS Grid 基礎 Class

```css
/* Bento Grid Shell — 加在 .container 內 */
.bento-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--bento-gap);
}

@media (min-width: 768px) {
    .bento-grid {
        grid-template-columns: repeat(12, 1fr);
    }
}

/* Bento Cell — 自包含卡片 */
.bento-cell {
    background: var(--surface);
    border-radius: var(--bento-radius);
    padding: var(--bento-padding);
    box-shadow: var(--shadow-s);
}

/* 卡片階層 */
.bento-cell--hero    { grid-column: span 12; }  /* 手機自動 1fr */
.bento-cell--wide    { grid-column: span 8; }
.bento-cell--side    { grid-column: span 4; }
.bento-cell--half    { grid-column: span 6; }
.bento-cell--full    { grid-column: span 12; }

/* 手機全部 full-width */
@media (max-width: 767px) {
    .bento-cell--hero,
    .bento-cell--wide,
    .bento-cell--side,
    .bento-cell--half {
        grid-column: span 1;
    }
}
```

### 各頁面 Grid Template

**清單頁 (`list.html`)：**

```css
@media (min-width: 768px) {
    .bento-grid--list {
        grid-template-areas:
            "summary summary summary summary  summary summary summary summary  actions actions actions actions"
            "table   table   table   table    table   table   table   table   table   table   table   table";
    }
}
```

模板變更：
```html
<!-- Before -->
<div class="container">
    <h1>出帳管理</h1>
    <!-- buttons, table, summary 全部線性排列 -->
</div>

<!-- After -->
<div class="container">
    <h1>出帳管理</h1>
    <div class="bento-grid bento-grid--list">
        <div class="bento-cell bento-cell--wide" style="grid-area: summary">
            <!-- 請款加總 summary panel -->
        </div>
        <div class="bento-cell bento-cell--side" style="grid-area: actions">
            <!-- 新增提報 / 匯出 buttons / 案場管理 -->
        </div>
        <div class="bento-cell bento-cell--full" style="grid-area: table">
            <!-- 費用清單 table（保持原有 desktop-table + mobile-cards） -->
        </div>
    </div>
</div>
```

**新增提報頁 (`new.html`)：** 最優先頁面

```html
<!-- After: 表單區段用 bento-cell 包裹，但內部保持線性 -->
<div class="bento-grid">
    <div class="bento-cell bento-cell--full">
        <!-- 整個表單作為一張卡片，內部 form-group 線性排列 -->
        <!-- 不拆成多張卡片，避免手機端操作碎片化 -->
    </div>
</div>
```

> `/new` 頁面的 Bento 改動最小——現有 `.card` 已經包裹表單，只需改 class 名為 `.bento-cell`。重點是確保 input font-size ≥ 16px。

**其他頁面：** vendors 和 users 類似 list 的 summary+table 結構，login 維持置中卡片。

---

## 5. 組件遷移方案

### Navbar

```css
/* Before */
.navbar {
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: saturate(180%) blur(20px);
}

/* After */
.navbar {
    background: var(--surface);  /* 暖奶油白實底 */
    backdrop-filter: none;
    border-bottom: 1px solid var(--border);
}

.nav-brand {
    font-family: var(--font-heading);  /* Noto Serif TC */
    font-weight: 700;
}
```

### 按鈕系統

```css
/* 現有 .btn 改為 default style */
.btn {
    background: var(--btn-default);  /* #333 深石墨 */
    color: #fff;
    border-radius: 6px;              /* 微圓角（原 var(--radius-l) 太圓） */
    transition: all var(--transition);
    min-height: 44px;                /* 觸控區域 */
}

/* 新增 CTA variant */
.btn-cta {
    background: var(--accent);       /* #4A5D4E 森林綠 */
    color: #fff;
}

/* 新增 secondary variant */
.btn-secondary {
    background: var(--accent-secondary);  /* #7A6652 胡桃棕 */
    color: #fff;
}

/* Danger 保持紅色 */
.btn-danger {
    background: var(--red);
    color: #fff;
}
```

模板影響：送出按鈕加 `class="btn btn-cta"`，編輯按鈕加 `class="btn btn-secondary"`。

### 表單焦點環

```css
/* 全域覆寫 */
*:focus-visible {
    outline: 2px solid var(--accent-secondary);  /* 胡桃棕 */
    outline-offset: 2px;
}

/* 表單 input 防 iOS zoom */
input, select, textarea {
    font-size: max(16px, 1rem);
}
```

### Typography

```css
h1, h2, h3 {
    font-family: var(--font-heading);  /* Noto Serif TC */
}

h1 {
    font-size: 32px;    /* 從 28px 加大 */
    line-height: 1.3;
    letter-spacing: -0.02em;
}

h3 {
    font-size: 20px;    /* Serif 最小 20px */
    line-height: 1.5;
}

body {
    font-family: var(--font);  /* Noto Sans TC */
    font-size: 16px;           /* 從 15px 調到 16px（防 iOS zoom） */
    line-height: 1.7;          /* 從 1.5 加大（CJK 需要更多行高） */
}
```

---

## 6. Dark Mode 方案（SHOULD）

### 設計決策：保留現有架構，換值

現有 dark mode 已經是「覆寫 `:root` token」模式（line 1061-1106），V5 只需換色值：

```css
@media (prefers-color-scheme: dark) {
    :root {
        /* Before: Apple dark (#000000 背景)
           After: Earth-tone dark（暖棕背景） */
        --bg: #1E1A17;
        --surface: #2A2520;
        --text-primary: #E8E2D9;
        --text-secondary: #B8A898;
        --border: rgba(176, 158, 136, 0.2);
        --accent: #6B8F70;
        --accent-secondary: #A08B75;
        --shadow-s: 0 1px 3px rgba(20, 12, 4, 0.3);
        --shadow-m: 0 4px 14px rgba(20, 12, 4, 0.4);
        --shadow-l: 0 8px 30px rgba(20, 12, 4, 0.5);
    }

    /* Navbar 實底暗色 */
    .navbar {
        background: var(--surface);
    }

    /* 移除現有的 per-component dark overrides（line 1089-1105）*/
    /* 因為組件全部引用 token，不需要個別覆寫 */
}
```

現有 dark mode 有 4 個 per-component 覆寫（inline-edit, form inputs），新架構因為所有組件都引用 semantic token，這些覆寫可以移除。

---

## 7. 檔案變更清單

### 總覽

| 檔案 | 變更類型 | Phase |
|------|---------|-------|
| `static/style.css` | 重寫 `:root` token + 新增 Bento Grid + 組件調整 | 1, 2, 3 |
| `templates/base.html` | 加 Google Fonts link + preconnect + theme-color | 1 |
| `templates/list.html` | 加 `.bento-grid` + `.bento-cell` wrapper | 2 |
| `templates/new.html` | `.card` → `.bento-cell` + 按鈕 class 調整 | 2, 3 |
| `templates/vendors.html` | 加 `.bento-grid` wrapper | 2 |
| `templates/users.html` | 加 `.bento-grid` wrapper | 2 |
| `templates/login.html` | theme-color 已在 base.html 處理 | 1 |
| `app.py` line 165 | CSP header 加 Google Fonts 白名單 | 1 |

### 不改的檔案

| 檔案 | 為什麼不改 |
|------|-----------|
| `app.py`（除 CSP） | 純 UI 改版，不碰路由/商業邏輯 |
| `static/app.js` | 不影響 vendor check / bank info API |
| `test_scenario.py` | 測試對 CSS class 不敏感（驗 HTTP response + form submit） |
| `migrate_*.py` | 無 DB 變更 |

### style.css 新結構（預估 ~1,250 行）

```
Line 1-5       @layer 宣告（新增）
Line 6-15      @font-face fallback metric overrides（新增）
Line 16-80     :root — Primitive tokens + Semantic tokens（重寫）
Line 81-100    Reset & Foundation（保留，微調 body font-size/line-height）
Line 101-130   Navbar（移除毛玻璃，加 serif brand）
Line 131-160   Container + Typography（加 serif headings）
Line 161-190   Login（微調色值，已自動吃 token）
Line 191-310   Buttons（拆分 CTA/secondary/default）
Line 311-550   Forms + Radio + Messages + Desktop table + Inline edit（mostly 自動吃 token）
Line 551-700   Mobile cards + Badges + Actions + Locked（mostly 自動吃 token）
Line 701-800   Section card + Vendor page（微調）
Line 801-900   Summary panel + Dup warning（改為 hero bento cell 樣式）
Line 901-950   Bento Grid system（新增）
Line 951-1050  Responsive breakpoints（調整 + Bento responsive）
Line 1051-1100 Dark mode（SHOULD — 換值）
Line 1101-1130 Utility: focus-visible, input font-size（新增）
Line 1131-1150 Print（保留）
```

---

## 8. 風險防護實作

### CSP 靜默失敗偵測

Phase 1 完成後，開 DevTools Console 確認無 CSP 錯誤：
```
Refused to load the stylesheet 'https://fonts.googleapis.com/...'
because it violates the following Content Security Policy directive
```
如果出現此訊息 = CSP 沒改到。

### 69 測試不受影響的原因

測試使用 `urllib` 對 HTTP response 做驗證：
- POST form submit → 驗 redirect / status code
- GET page → 驗 response 包含特定文字（如廠商名稱、金額）

測試**不依賴** CSS class 名稱或 DOM 結構。新增 `.bento-grid` wrapper div 不影響 form 的 `name` attribute 和 `action` URL。

唯一風險：如果模板重構不小心刪除或搬移了 `<form>` 或 `<input name="...">`。Phase 2 抽驗清單覆蓋這個風險。

### 效能不劣化的原因

| 面向 | 現狀 | V5 後 | 差異 |
|------|------|-------|------|
| CSS 檔案大小 | 1,120 行 ~35KB | ~1,250 行 ~40KB | +5KB（可忽略） |
| JS 檔案 | app.js 61 行 | 不變 | 0 |
| HTTP 請求 | 2（CSS + JS） | 3-5（+Google Fonts CSS + font chunks） | +2-3（preconnect 優化） |
| DOM 層級 | 平均 8 層 | 平均 9 層（+bento wrapper） | +1（可忽略） |
| 渲染 | 無 Grid | CSS Grid | 瀏覽器原生，無效能影響 |

---

## 9. 開發順序與檢查點

```
Phase 1: Token + Font
├── 1. 寫 primitive + semantic tokens（:root 區塊重寫）
├── 2. 改 app.py CSP header
├── 3. 加 Google Fonts link 到 base.html
├── 4. 加 @font-face fallback metric override
├── 5. 改 body/heading font-family + font-size
├── 🔍 檢查點：開 /login 確認字型載入 + 大地色背景 + 無 CSP 錯誤
└── 🧪 跑 69/69 測試

Phase 2: Bento Grid
├── 1. 寫 .bento-grid + .bento-cell CSS
├── 2. /new 頁面加 bento wrapper（最優先）
├── 3. /list 頁面加 bento grid-template-areas
├── 4. /vendors + /users 加 bento wrapper
├── 5. 調整響應式斷點
├── 🔍 檢查點：手機 390px + 桌面 1280px 各頁截圖確認
├── 🧪 跑 69/69 測試
└── 🧪 人工抽驗 5 個場景

Phase 3: Components
├── 1. Navbar 實底 + serif brand
├── 2. Button 拆分 CTA/secondary/default
├── 3. 焦點環 → 胡桃棕
├── 4. Summary panel → hero bento cell
├── 5. 清除殘留 Apple 風格 CSS
├── 🔍 檢查點：逐頁確認零冷白殘留
└── 🧪 跑 69/69 測試

Phase 5: QA + UAT（跳過 Phase 4）
├── 1. 69/69 測試
├── 2. WCAG AA 對比度確認（Light Mode）
├── 3. iOS Safari 手機測試（/new 優先）
├── 4. 4G 效能測試（FCP ≤ 2s）
├── 5. After 截圖（10 張）
├── 6. Before/After 對比圖
├── 7. git tag v4-final
└── 8. UAT：管理員 + 設計師當面確認
```

---

*SDD V6 — 2026-04-16*
*對應：prdv6.md V6.1 + style.css 現況分析*
