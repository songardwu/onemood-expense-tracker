# TODO 20260416 Night — 下一步優先順序（更新版）

## 已完成項目（本輪）

| 原優先 | 項目 | 狀態 |
|--------|------|------|
| P0-1 | Vercel 部署驗證（flask-limiter 已加入 requirements.txt） | ✅ 待部署驗證 |
| P1-3 | users.html / cost_categories.html 手機卡片 | ✅ 已加 mobile-cards |
| P1-4 | list.html / new.html title + scope | ✅ 已加 block title + scope="col" |
| P1-5 | DB 連線池 | ✅ 不需要：Neon pooler 已在 server-side 處理 |
| P2-6 | CSP unsafe-inline | ✅ 評估後維持：僅 style-src，54 處 inline style 重構成本高，無 script-src 風險 |
| P2-7 | 分頁機制 | ✅ 已加分頁（reports / projects / audit logs，每頁 50 筆） |
| P2-8 | CSRF error handler | ✅ 改用 CSRFError exception class |

## 剩餘優先順序

### P3 — 未來考慮
1. **連線池改用 ThreadedConnectionPool** — 僅在脫離 Vercel serverless 改用 gunicorn 時需要
2. **vendor_create 權限** — 目前 login_required，考慮是否改 admin_required
3. **Excel export 串流化** — 大量資料時 pd.read_sql 全部載入記憶體，改用 streaming
4. **CSP style-src 移除 unsafe-inline** — 需重構 54 處 inline style 為 CSS class，工作量大
5. **Dark mode 漢堡選單配色驗證** — 需實機測試 prefers-color-scheme: dark 下的選單樣式

## 技術決策記錄

### DB 連線池（P1-5）
- Neon 連線字串使用 `-pooler.` endpoint → server-side PgBouncer 已生效
- Vercel serverless 每次 invocation 短暫存活，app-level pool 無法跨 request 重用
- 結論：現行 Flask `g` + `teardown_appcontext` 是最適配置，不需加 app-level pool

### CSP unsafe-inline（P2-6）
- 現行 CSP：`style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`
- `script-src 'self'` 已是最嚴格配置，XSS 主要風險已阻擋
- `style-src unsafe-inline` 對應 54 處 inline style attribute，非 `<style>` block
- inline style attribute 無法執行 JavaScript，安全風險極低
- 結論：接受現狀，列為 P3 長期優化項目
