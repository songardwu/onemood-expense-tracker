# PRD V6 — UI 設計改版完整規格書

## Dawn 出帳管理系統 V5 UI Redesign

**版本：** V6.1（整合需求定義 + 執行路線圖 + 設計規格 + 研究結論 + PM 訪談優化）
**範圍：** 純 CSS/Template 視覺改版（例外：CSP header 一行安全設定調整）
**分支：** `v5-ui-redesign`
**部署策略：** 全部完成後一次上線（不推半成品），附 1-3 天觀察期
**約束：** 69/69 功能測試全程綠燈；4G 行動網路首屏 ≤ 2 秒

---

## 1. 背景與目標

目前系統使用 Apple 極簡風格（冷白背景、SF Pro 字型、毛玻璃 navbar），功能完善但視覺上缺乏室內設計公司的品牌識別。

### 設計目標

- 利用「暖大地色系」營造健康、無壓的居家氛圍
- 強化「設計師」職人形象（人文感字型 + 自然材質色）
- 全頁面 Bento Grid 排版，簡潔、層次分明、具備信任感
- 符合 WCAG AA 無障礙標準（Light Mode 為主）
- 維持手機端（51% 流量）完美操作體驗，效能不劣於現狀
- `/new` 新增提報頁為手機端第一優先優化對象

### 使用者場景

| 角色 | 裝置 | 最高頻操作 | 網路環境 |
|------|------|-----------|---------|
| 設計師 | 手機 (51%) | 新增提報 (`/new`) | 辦公室 WiFi + 外出 4G |
| 管理員 | 桌面 (49%) | 查看清單、審核、匯出 | 辦公室 WiFi |

### 核心價值

設計師和管理員能在任何裝置上快速、無壓力地完成請款提報與審核，UI 視覺傳達「健康、自然、高級感」的室內設計品牌形象。

---

## 2. 色彩計畫 (Color Palette)

### Light Mode

| 角色 | 色碼 | 名稱 | 用途 | 對比度驗證 |
|------|------|------|------|-----------|
| 主背景 | `#F5F2ED` | 暖奶油 Warm Cream | 全站底色 | — |
| 卡片背景 | `#FFFFFF` | 純白 | Bento 卡片表面 | — |
| 主文字 | `#333333` | 深石墨 Charcoal | 標題與主要內文 | vs 背景 11.31 PASS |
| 副文字 | `#666666` | 暖灰 Warm Grey | 副標題、說明文字 | vs 背景 5.14 PASS |
| 主強調 | `#4A5D4E` | 森林深綠 Forest Green | 主要 CTA 按鈕 | 白字 7.08 PASS |
| 次強調 | `#7A6652` | 胡桃木棕 Walnut Brown | 次要按鈕、焦點環 | 白字 5.45 PASS |
| 按鈕底 | `#333333` | 深石墨 | 一般按鈕底色 | 白字 12.63 PASS |

> 胡桃棕已從原始 `#8C7662` 調整為 `#7A6652`，確保 WCAG AA 合規（原色白字對比僅 4.30，未達 4.5 標準）。

### Dark Mode（SHOULD — 獨立設計的暖色暗色版）

> **優先級：SHOULD**（使用者目前主要使用 Light Mode，Dark Mode 不阻擋上線，可於後續版本補齊）

| 角色 | 色碼 | 名稱 | 說明 |
|------|------|------|------|
| 主背景 | `#1E1A17` | 深暖棕 Deep Umber | 溫暖深色底，非中性灰 |
| 卡片背景 | `#2A2520` | 暖深棕 Warm Dark Brown | 比背景稍淺，形成層次 |
| 卡片提升 | `#332D28` | 提升面 Elevated Surface | 浮起卡片用 |
| 主文字 | `#E8E2D9` | 暖奶白 Warm Cream Text | 非純白，減少刺眼 |
| 副文字 | `#B8A898` | 暖中灰 Warm Mid-Grey | 輔助說明 |
| 主強調 | `#6B8F70` | 亮森林綠 Light Forest | 提高亮度 + 飽和度 10-15% |
| 次強調 | `#A08B75` | 亮胡桃棕 Light Walnut | 提高亮度 + 飽和度 |
| 邊框 | `rgba(176,158,136,0.2)` | 暖邊框 | 透明暖色邊框 |

**Dark Mode 設計原則：**
- 獨立設計色板，不做 Light Mode 的數學反轉（反轉會讓暖色變灰）
- 強調色飽和度 +10-15%（暗背景上暖色會失去溫度）
- 暗色背景保持暖色調：`hsl(30, 8%, 12%)` 而非 `hsl(0, 0%, 12%)`
- 陰影用暖色調：`rgba(20, 12, 4, 0.6)` 而非純黑

### WCAG AA 對比度驗證表

**Light Mode:**

| 組合 | 對比度 | AA 正文 | AA 大字 |
|------|--------|---------|---------|
| 主文字 `#333` vs 背景 `#F5F2ED` | 11.31 | PASS | PASS |
| 副文字 `#666` vs 背景 | 5.14 | PASS | PASS |
| 白字 vs 森林綠按鈕 `#4A5D4E` | 7.08 | PASS | PASS |
| 白字 vs 胡桃棕按鈕 `#7A6652` | 5.45 | PASS | PASS |
| 白字 vs 深石墨按鈕 `#333` | 12.63 | PASS | PASS |
| 森林綠文字 vs 背景 | 6.34 | PASS | PASS |
| 胡桃棕文字 vs 背景 | 4.88 | PASS | PASS |

**Dark Mode:**（Phase 4 視覺驗證後確認）

| 組合 | 預估對比度 | 需驗證 |
|------|-----------|--------|
| 暖奶白 `#E8E2D9` vs 背景 `#1E1A17` | ~11.2 | Phase 4 |
| 副文字 `#B8A898` vs 背景 | ~5.8 | Phase 4 |
| 暖奶白 vs 亮森林綠按鈕 `#6B8F70` | ~4.8 | Phase 4 |
| 暖奶白 vs 亮胡桃棕按鈕 `#A08B75` | ~4.6 | Phase 4 |

---

## 3. 字體規範 (Typography)

### 字型選擇

| 角色 | 字型 | 字重 | 最小字級 | 用途 |
|------|------|------|---------|------|
| 大標題 | Noto Serif TC（思源宋體） | Bold 700 | 20px | 頁面大標、品牌名稱 |
| 內文 | Noto Sans TC（思源黑體） | Regular 400 | 16px | 表單文字、表格內容 |

### 排版參數

| 元素 | 字型 | 字級 | 行高 | 字距 |
|------|------|------|------|------|
| h1 (頁面標題) | Noto Serif TC 700 | 32-40px | 1.3 | -0.02em |
| h2 (區塊標題) | Noto Serif TC 700 | 24-28px | 1.4 | -0.01em |
| h3 (卡片標題) | Noto Serif TC 700 | 18-20px | 1.5 | 0 |
| body | Noto Sans TC 400 | 15-16px | 1.7 | 0 |
| caption | Noto Sans TC 400 | 13-14px | 1.6 | 0 |

### 字型載入策略

```html
<!-- base.html <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC&family=Noto+Serif+TC:wght@700&display=swap" rel="stylesheet">
```

**Fallback Font Metric Override（防止 CLS）：**

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

**Fallback Stack：**
- 標題：`'Noto Serif TC', 'Noto Serif TC Fallback', 'PMingLiU', serif`
- 內文：`'Noto Sans TC', 'Microsoft JhengHei', 'PingFang TC', sans-serif`

---

## 4. CSS 架構

### Two-Layer Token System

```css
/* Layer 1: Primitive Tokens (raw values) */
:root {
  --color-cream: #F5F2ED;
  --color-charcoal: #333333;
  --color-warm-grey: #666666;
  --color-forest: #4A5D4E;
  --color-walnut: #7A6652;
  --color-white: #FFFFFF;
  /* ... */
}

/* Layer 2: Semantic Tokens (role assignments) */
:root {
  --bg-page: var(--color-cream);
  --bg-surface: var(--color-white);
  --text-primary: var(--color-charcoal);
  --text-secondary: var(--color-warm-grey);
  --accent-primary: var(--color-forest);
  --accent-secondary: var(--color-walnut);
  /* ... */
}

/* Dark Mode: reassign semantic tokens ONLY */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-page: #1E1A17;
    --bg-surface: #2A2520;
    --text-primary: #E8E2D9;
    --text-secondary: #B8A898;
    --accent-primary: #6B8F70;
    --accent-secondary: #A08B75;
    /* ... */
  }
}
```

### @layer 宣告順序（建議）

```css
@layer reset, tokens, base, components, utilities, overrides;
```

### CSS 檔案結構（單一 style.css，約 1,200-1,350 行）

| Section | 內容 |
|---------|------|
| 1. @layer 宣告 | Cascade 順序 |
| 2. @font-face fallback | Metric overrides |
| 3. Primitive tokens | 原始色碼值 |
| 4. Semantic tokens (light) | 角色映射 |
| 5. Semantic tokens (dark) | Dark mode 覆寫 |
| 6. Base/reset | HTML 基礎樣式 |
| 7. Bento Grid shells | 頁面級 Grid 佈局 |
| 8. Bento cells | 卡片基礎樣式 |
| 9. Components | 按鈕、表單、表格、導覽列... |
| 10. Utilities + overrides | 工具類 + 特殊覆寫 |

---

## 5. Bento Grid 佈局

### 設計原則

- **Bento 用於頁面結構**：summary 面板、操作區、表單區段 → 用 Bento Grid
- **表格用於資料列表**：費用清單、廠商列表 → 維持 table/card list（不用 Bento）
- **不使用 `grid-auto-flow: dense`**：避免 tab order 與視覺順序不一致（WCAG 2.4.3）
- **使用 `grid-template-areas`**：每頁有名稱化的區域定義

### 三層卡片階層

| 層級 | CSS 尺寸 | 用途 |
|------|---------|------|
| Hero | `grid-column: span 2` + `grid-row: span 2` | 請款加總、重要 KPI |
| Standard | `grid-column: span 2` 或 `span 1` | 操作面板、表單區段 |
| Compact | `grid-column: span 1` | 快捷資訊、狀態指示 |

### 各頁面 Grid 規劃

**登入頁 (`login.html`)：**
- 置中單卡片佈局，品牌名 Noto Serif TC Bold
- 登入按鈕用森林深綠 CTA

**清單頁 (`list.html`)：**
```
桌面：
┌─────────────────┬────────────┐
│  請款加總 (Hero) │  操作面板   │
│                 │            │
├─────────────────┴────────────┤
│         費用清單 (Table)       │
└──────────────────────────────┘

手機：
┌──────────────────────────────┐
│  請款加總                     │
├──────────────────────────────┤
│  操作面板                     │
├──────────────────────────────┤
│  費用清單 (Cards)             │
└──────────────────────────────┘
```

**新增提報頁 (`new.html`)：**
- 表單區段用 Bento 卡片包裹（基本資訊、金額、發票）
- 內部保持線性流程，送出按鈕用森林深綠 CTA

**廠商資料頁 (`vendors.html`)：**
- Bento Grid 排列：新增表單卡片 + 匯入卡片 + 廠商列表

**帳號管理頁 (`users.html`)：**
- Bento 卡片排列帳號清單，狀態 badge 用大地色系

---

## 6. 組件設計

### 按鈕系統

| 類型 | 背景色 | 文字色 | 用途 |
|------|--------|--------|------|
| 主 CTA | `var(--accent-primary)` #4A5D4E | 白 | 送出、確認、登入 |
| 次要 | `var(--accent-secondary)` #7A6652 | 白 | 編輯、次要操作 |
| 預設 | `var(--text-primary)` #333 | 白 | 一般按鈕 |
| 危險 | 紅色系（維持不變） | 白 | 刪除、破壞性操作 |

| 屬性 | 規格 |
|------|------|
| 圓角 | `border-radius: 4px ~ 6px` |
| 過渡 | `transition: all 0.3s ease` |
| 觸控區域 | 最小高度 44px |
| Hover | 背景亮度 +8%, `translateY(-1px)` |
| Active | `scale(0.97)`, 100ms |

### 卡片設計 (Bento Cell)

| 屬性 | 規格 |
|------|------|
| 背景 | `var(--bg-surface)` (Light: #FFF, Dark: #2A2520) |
| 圓角 | `8px ~ 12px`（單一 token `--bento-radius`） |
| 內距 | `16px ~ 24px` |
| 陰影 | `box-shadow: 0 2px 8px rgba(74,93,78,0.08)` |
| Hover | `translateY(-2px)` + shadow 加深, 150-200ms |

### Navbar

- 固定頂部，毛玻璃改為大地色系實底
- 品牌名 "Dawn" 使用 Noto Serif TC
- Light: 暖奶油底 or 深石墨底 + 白字
- Dark: 暖深棕底 + 暖奶白字

### 表單元素

| 屬性 | 規格 |
|------|------|
| 邊框 | `1px solid var(--border)` |
| 焦點環 | `outline: 2px solid #7A6652` (胡桃棕) |
| 字級 | `font-size: max(16px, 1rem)` (全域強制，防 iOS zoom) |
| 背景 | `var(--bg-surface)` |

---

## 7. 響應式設計

### 斷點

| 斷點 | 裝置 | Grid 行為 |
|------|------|----------|
| < 390px | 小螢幕手機 | 單欄、更緊湊間距 |
| < 768px | 手機 | Bento Grid 堆疊為單欄 |
| 768px+ | 平板/桌面 | Bento Grid 多欄 |
| 1200px+ | 大螢幕 | 更寬鬆間距、更多欄 |

### 手機優化重點

- 觸控區域最小 44px
- 表單 input `font-size: max(16px, 1rem)`（防止 iOS Safari 自動縮放）
- iPhone safe area：`padding-bottom: env(safe-area-inset-bottom)`
- Noto Serif TC 標題不低於 20px
- Mobile 明確設計（非 desktop fallback）：重要卡片用 `order` 優先顯示

---

## 8. Dark Mode 實作（SHOULD — 不阻擋上線）

> **優先級：SHOULD** — Dark Mode token 在 Phase 1 預留架構（semantic token 層），但視覺驗證與打磨延後至 Phase 4（optional）。上線最低要求為 Light Mode 完整可用。

### 觸發方式

```css
@media (prefers-color-scheme: dark) {
  :root {
    /* 只重新指派 semantic tokens */
  }
}
```

- 無 JS toggle（內部工具跟隨系統即可）
- `<meta name="color-scheme" content="light dark">` 防 FODT 白閃

### 暗色版設計要點

- 背景必須是暖色調（深棕 `#1E1A17`），不用中性灰
- 強調色飽和度 +10-15%，補償暗背景的色彩衰減
- 文字用暖奶白 `#E8E2D9`，不用純白 `#FFFFFF`
- 陰影用暖色調 `rgba(20, 12, 4, 0.6)`
- 層次用亮度區分（較亮 = 較高），不用陰影

---

## 9. 微互動與動畫（SHOULD — 不阻擋上線）

> **優先級：SHOULD** — 手機端無 hover 效果，實際受益有限。有則加分，無不影響上線。

| 互動 | 動畫 | 時長 | 備註 |
|------|------|------|------|
| 卡片 Hover | `translateY(-2px)` + shadow 加深 | 150-200ms | ease-out（桌面才有效） |
| 按鈕 Press | `scale(0.97)` | 100ms down, 150ms up | — |
| 頁面載入 | 卡片交錯入場 | 40ms/card stagger | 僅首次 |
| 成功回饋 | 森林綠 checkmark + "已儲存" | 250ms | scale 0→1.1→1 |
| Loading | 大地色 shimmer `#E8E2D9` ↔ `#F5F2ED` | 1.5s loop | 非灰色 |

**動畫預算：** 每頁同時最多 3 種動畫類型
**無障礙：** `prefers-reduced-motion: reduce` 時停用所有動畫

---

## 10. 效能考量

### 效能預算（MUST）

| 指標 | 目標 | 基準（現狀） | 測試環境 |
|------|------|------------|---------|
| 首屏可見 (FCP) | ≤ 2 秒 | ~1-2 秒 | 4G 行動網路 |
| 可互動 (TTI) | ≤ 3 秒 | ~1-2 秒 | 4G 行動網路 |
| 字型換體跳動 (CLS) | < 0.1 | 0（無自訂字型） | 所有環境 |
| 優先頁面 | `/new` 新增提報頁 | — | 手機 4G |

> 改版後效能不得劣於現狀。設計師在工地用 4G 新增提報是最高頻場景。

### 策略

| 項目 | 策略 |
|------|------|
| CJK 字型載入 | Google Fonts + `font-display: swap`；preconnect + 合併 URL + 限制字重（Serif 700 + Sans 400）|
| Font Swap CLS | `@font-face` fallback metric override（size-adjust: 97%, ascent-override: 88%）降低跳動幅度 |
| CSP Header 調整 | `app.py` 加入 `fonts.googleapis.com` + `fonts.gstatic.com` 白名單（唯一 app.py 變更，見 §11） |
| CSS 改動範圍 | 僅修改 style.css + templates；不新增 JS |
| 69 項功能測試 | 純 CSS/Template 改動，功能邏輯零修改 |
| `<html lang="zh-Hant">` | 正確 CJK 渲染 + 螢幕閱讀器語言辨識 |
| Print | `@media print` 強制 light mode、隱藏導覽列（SHOULD） |

---

## 11. 已知風險與防護

### CSP Header 例外（唯一 app.py 變更）

本案原則為「不碰 app.py」，但 Google Fonts 需要 CSP 白名單才能載入。此為唯一例外，僅修改安全設定一行，不涉及商業邏輯：

```python
# app.py line 165 — 修改前
"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"

# 修改後
"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'"
```

### 風險登錄

| 風險 | 嚴重度 | 影響 | 防護措施 | 階段 |
|------|--------|------|---------|------|
| **CSP 擋 Google Fonts** | **Critical** | 字型完全不載入，瀏覽器靜默失敗 | 修改 CSP header 加白名單（見上方） | Phase 1 |
| CJK 字型 40+ HTTP 請求 | High | 手機 FCP 慢 2-4s | preconnect + 合併 URL + 限制字重 | Phase 1 |
| font-display: swap CLS | High | Bento 卡片跳動 | fallback font metric overrides | Phase 1 |
| **模板重構讓測試靜默失效** | **Medium** | 69 測試 pass 但驗到錯的東西 | Phase 2 後人工抽驗 5 個關鍵場景（見下方） | Phase 2 |
| iOS Safari 16px 自動縮放 | High | 表單佈局炸裂 | 全域 `font-size: max(16px, 1rem)` | Phase 2 |
| Bento + 動態資料列 = 孤兒格 | Medium | 佈局破碎 | Bento 只用於結構；表格用於資料 | Phase 2 |
| dense flow 破壞 tab order | Medium | WCAG 2.4.3 不合規 | 明確 grid placement，禁用 dense | Phase 2 |
| 暗色模式暖色變灰 | Low | 品牌感消失 | 獨立設計暗色板 + 視覺驗證（SHOULD） | Phase 4 |
| Serif 字型 <20px 難辨 | Medium | 手機端可讀性差 | Serif 僅用於標題 >=20px | Phase 1 |
| **上線後無法回滾** | **Medium** | 出問題時無退路 | git tag + revert 計畫（見下方） | Phase 5 |

### Phase 2 測試健全性抽驗清單

模板加入 Bento Grid 包裹 div 後，除了跑 69/69 自動測試，需人工抽驗以下 5 個場景確認測試仍在驗對的東西：

1. 新增提報 → 送出成功（`/new` → `/submit`）
2. 管理員 inline 編輯 → 更新成功
3. 廠商新增 → 出現在列表
4. 刪除報表 → 從列表消失
5. 匯出 Excel → 下載成功

### 回滾計畫

| 層級 | 時機 | 做法 | 耗時 |
|------|------|------|------|
| 預防 | 上線前 | `git tag v4-final` 標記舊版 | 10 秒 |
| 快速回滾 | 上線後發現重大問題 | `git revert` merge commit → 重新部署 | 5 分鐘 |
| 觀察期 | 上線後 1-3 天 | 管理員 + 設計師實機試用，收集回饋 | 1-3 天 |

```
上線前：git tag v4-final
   ↓
合併 v5-ui-redesign → master → Vercel 自動部署
   ↓
上線後 1 小時：自己手機打開 /new 確認
   ↓
上線後 1-3 天：管理員 + 設計師試用
   ↓
OK → V5 正式定案 ｜ 不 OK → git revert（5 分鐘退回 V4）
```

---

## 12. 執行路線圖

### Phase 1: Design Token System + Font Setup（MUST）

**目標：** 建立完整的色彩和字型基礎，後續所有階段的依賴根基。

| # | 任務 | 檔案 |
|---|------|------|
| 1.1 | 定義 primitive color tokens | `static/style.css` |
| 1.2 | 定義 semantic color tokens (light) | `static/style.css` |
| 1.3 | 預留 dark mode semantic token 架構（值可暫用 light） | `static/style.css` |
| 1.4 | WCAG 對比度驗證表（CSS 註解，Light Mode） | `static/style.css` |
| 1.5 | Google Fonts link + preconnect | `templates/base.html` |
| 1.6 | **修改 CSP header 加 Google Fonts 白名單** | `app.py` line 165 |
| 1.7 | @font-face fallback metric overrides | `static/style.css` |
| 1.8 | Typography tokens (字型、字級、行高) | `static/style.css` |
| 1.9 | `lang="zh-Hant"` | `templates/base.html` |
| 1.10 | @layer 宣告 | `static/style.css` |
| 1.11 | 替換現有 Apple 風格色值為 semantic tokens | `static/style.css` |

**驗收：** 全站切換為大地色系；字型載入無白屏；CSP 不擋字型；69/69 測試通過

### Phase 2: Bento Grid + Template 重構（MUST）

**目標：** 頁面級結構從線性流轉換為 Bento Grid，mobile-first 響應式。
**優先頁面：** `/new` 新增提報頁第一優先（手機最高頻操作）

| # | 任務 | 檔案 |
|---|------|------|
| 2.1 | `.bento-grid` 基礎 class (mobile-first 1-col) | `static/style.css` |
| 2.2 | **`/new` 新增提報頁 grid（第一優先）** | CSS + `templates/new.html` |
| 2.3-2.6 | 其餘 4 頁 grid-template-areas（list/vendors/users/login） | CSS + templates |
| 2.7 | `.bento-cell` 卡片基礎樣式 | `static/style.css` |
| 2.8 | 三層卡片階層 (Hero/Standard/Compact) | `static/style.css` |
| 2.9 | 響應式斷點（390/768/1200px） | `static/style.css` |
| 2.10 | 全域 input font-size >= 16px | `static/style.css` |
| 2.11 | iPhone safe area padding | `static/style.css` |
| 2.12 | Templates 加入 `.bento-grid` + `.bento-cell` 標記 | 6 templates |
| 2.13 | **測試健全性抽驗**（5 個關鍵場景人工比對，見 §11） | — |

**驗收：** 桌面多欄 Grid；手機單欄堆疊；無 iOS zoom；69/69 測試通過；抽驗 5 場景正確

### Phase 3: Component Restyling（MUST）

**目標：** 所有 UI 組件改用 semantic tokens，消除 Apple 風格殘留。

| # | 任務 | 檔案 |
|---|------|------|
| 3.1 | 按鈕系統 (CTA/次要/預設/危險) | `static/style.css` |
| 3.2 | 表單元素（邊框、焦點環、背景） | `static/style.css` |
| 3.3 | 桌面表格 + 手機卡片 | `static/style.css` |
| 3.4 | Navbar（實底 + serif 品牌名） | CSS + `base.html` |
| 3.5 | 狀態 badge + 訊息 | `static/style.css` |
| 3.6 | 請款加總 summary 面板（Hero 卡片） | CSS + `list.html` |
| 3.9 | 清除所有 Apple 風格 CSS 殘留 | `static/style.css` |

**驗收：** 零冷白殘留；胡桃棕焦點環；大地色 navbar；69/69 測試通過

### Phase 4: Dark Mode + 微互動 + 打磨（SHOULD — 不阻擋上線）

**目標：** 視覺驗證暗色模式品質，加入微互動打磨。此階段為加分項，Phase 1-3 + Phase 5 完成即可上線。

| # | 任務 | 優先級 | 檔案 |
|---|------|--------|------|
| 4.1 | 5 頁 dark mode 視覺檢查 | SHOULD | （檢查） |
| 4.2 | 調整 dark mode token 飽和度/亮度 | SHOULD | `static/style.css` |
| 4.3 | `color-scheme` meta tag | SHOULD | `base.html` |
| 4.4 | Print stylesheet | SHOULD | `static/style.css` |
| 4.5-4.7 | 微互動（hover lift / press / entrance stagger） | SHOULD | `static/style.css` |
| 4.8 | `prefers-reduced-motion` guard | SHOULD | `static/style.css` |

**驗收：** Dark mode 溫暖不灰；無 FODT 白閃；動畫流暢；69/69 測試通過

### Phase 5: Cross-Browser QA + 使用者驗收（MUST）

**目標：** 全面品質驗證 + 使用者實機確認。

| # | 任務 | 優先級 |
|---|------|--------|
| 5.1 | 69/69 功能測試全數通過 | MUST |
| 5.2 | WCAG AA 對比度審計（Light Mode） | MUST |
| 5.3 | iOS Safari 實機/模擬器測試（`/new` 頁面優先） | MUST |
| 5.4 | Chrome / Firefox / Edge / Safari 桌面驗證 | SHOULD |
| 5.5 | 手機 Chrome + Safari 驗證 | MUST |
| 5.6 | 4G 環境效能驗證（FCP ≤ 2s, TTI ≤ 3s） | MUST |
| 5.7 | 修復發現的問題 | MUST |
| 5.8 | **`git tag v4-final` 標記舊版** | MUST |
| 5.9 | **使用者驗收（UAT）：管理員 + 設計師當面看/截圖** | MUST |

**驗收：** 69/69 綠燈；WCAG AA 通過；4G 效能達標；使用者確認 OK

### 階段依賴圖

```
Phase 1 (Token + 字型) ─MUST─→ Phase 2 (Bento Grid) ─MUST─→ Phase 3 (組件) ─MUST─→ Phase 5 (QA + UAT)
                                                                    ↓
                                                              Phase 4 (Dark Mode + 動畫) ──SHOULD──↗
```

**上線最低路徑：** Phase 1 → 2 → 3 → 5（跳過 Phase 4 即可上線）
**完整路徑：** Phase 1 → 2 → 3 → 4 → 5

---

## 13. 需求總覽

| Phase | MUST | SHOULD | Total | 阻擋上線 |
|-------|------|--------|-------|---------|
| 1: Token + 字型 + CSP | 5 | 1 | 6 | 是 |
| 2: Bento Grid | 4 | 0 | 4 | 是 |
| 3: 組件 | 6 | 0 | 6 | 是 |
| 4: Dark Mode + 動畫 | 0 | 6 | 6 | **否** |
| 5: QA + UAT | 7 | 1 | 8 | 是 |
| **總計** | **22** | **8** | **30** | — |

**上線最低要求：22 個 MUST（Phase 1-3 + Phase 5）**
**完整版：30 個（含 Phase 4 的 SHOULD）**

---

## 14. 不在此版範圍

| 項目 | 原因 | 時機 |
|------|------|------|
| JS dark mode toggle | 跟隨系統即可 | 有需求時 |
| 卡片密度切換 | 需使用模式驗證 | V5.1+ |
| 方向性頁面轉場 | 需路由架構配合 | V5.1+ |
| 拉丁數字等寬字型 | 額外字型載入成本 | V5.1+ |
| FLIP 卡片動畫 | 高複雜度，低投資報酬 | V5.1+ |
| app.py 邏輯修改 | 純 UI 改版（CSP header 除外） | 另案 |
| 新功能（分頁、篩選） | 另案處理 | 另案 |
| DB 結構變更 | 無需 | — |
| Rate Limiting / 密碼複雜度 | 安全加固項 | 另案 |

---

## 15. 最終驗收標準

### MUST（上線門檻）

- [ ] 全站色彩使用暖大地色系，無冷白殘留
- [ ] 標題使用 Noto Serif TC，內文使用 Noto Sans TC
- [ ] 全頁面 Bento Grid 排版（清單、新增、廠商、帳號管理）
- [ ] 按鈕微圓角 4-6px + 0.3s transition
- [ ] Light Mode 所有色彩組合通過 WCAG AA 對比度
- [ ] 手機端（< 768px）完美自適應
- [ ] iPhone safe area 正常
- [ ] 字型 `font-display: swap` 無白屏
- [ ] iOS Safari 表單無自動縮放
- [ ] 4G 行動網路 FCP ≤ 2s、TTI ≤ 3s
- [ ] CSP header 允許 Google Fonts 載入
- [ ] 69/69 功能測試全數通過（純 UI 不影響功能）
- [ ] `git tag v4-final` 已標記（回滾保護）
- [ ] 管理員 + 設計師實機驗收通過（UAT）
- [ ] 改版前後對比截圖已產生（5 頁 × 桌面/手機 = 10 組）

### SHOULD（加分項，不阻擋上線）

- [ ] Dark Mode 大地色暗色版正常運作（溫暖，非灰色）
- [ ] Dark Mode 所有色彩組合通過 WCAG AA 對比度
- [ ] `prefers-reduced-motion` 時無動畫
- [ ] 微互動（hover lift / press feedback / entrance stagger）
- [ ] 列印樣式正常（強制 light mode）

---

## 16. 改版前後對比截圖計畫

在 Phase 5 上線前，產生改版前後對比截圖：

### 截圖範圍

| 頁面 | 桌面 (1280px) | 手機 (390px) |
|------|--------------|-------------|
| 登入頁 `/login` | Before / After | Before / After |
| 清單頁 `/` | Before / After | Before / After |
| 新增提報 `/new` | Before / After | Before / After |
| 廠商頁 `/vendors` | Before / After | Before / After |
| 帳號管理 `/users` | Before / After | Before / After |

### 執行方式

1. **Before 截圖：** 在開始 Phase 1 之前，從 `master` 分支截取 5 頁 × 2 尺寸 = 10 張截圖，存入 `docs/screenshots/before/`
2. **After 截圖：** Phase 5 QA 完成後，從 `v5-ui-redesign` 分支截取同樣 10 張，存入 `docs/screenshots/after/`
3. **對比圖：** 左右並排或上下疊放，用於 UAT 展示和內部記錄

### 用途

- UAT 驗收時展示給管理員和設計師
- 內部記錄改版成果
- 如需回滾時確認「回到哪個版本」

---

*PRD V6.1 — PM 訪談優化版：2026-04-16*
*基於：prdv5.md + GSD Research + REQUIREMENTS.md + ROADMAP.md + PM 訪談結論*
*訪談變更：Dark Mode/微互動降為 SHOULD、效能預算 4G ≤ 2s、CSP 例外、回滾計畫、UAT 環節、/new 優先、對比截圖*
