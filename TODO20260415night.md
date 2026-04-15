# TODO — 2026-04-15 Night（CSRF 完成後）

> 截止時間點：CSRF 防護全面完成，69/69 測試通過，準備推版。

---

## 🔴 P0 — 立即處理（阻塞正式使用）

### 1. ~~CSRF 防護~~ ✅ 已完成
- flask-wtf CSRFProtect 初始化完畢
- 全系統 19 個表單皆已加入 `csrf_token()`
- 測試腳本已更新支援 CSRF token 自動注入
- 69/69 scenario test 全通過

### 2. Dawn 管理員密碼更換
- 目前密碼仍為開發階段設定（dawn1234），任何知道 repo 的人都能登入
- 到帳號管理頁 `/users` 直接重設
- **負責人：Dawn 本人**

### 3. CSRF 錯誤處理精準化
- **現狀**：用 `@app.errorhandler(400)` 攔截，以 `'CSRF' in str(e)` 判斷
- **風險**：其他 400 錯誤可能被誤攔截，且一律導向 login.html
- **建議**：改用 Flask-WTF 的 `CSRFError` 專用例外：
  ```python
  from flask_wtf.csrf import CSRFError
  @app.errorhandler(CSRFError)
  def handle_csrf_error(e):
      return render_template('error.html', error='操作逾時，請重新操作。'), 400
  ```

---

## 🟡 P1 — 本週內完成

### 4. Session Cookie 安全強化
- **現狀**：缺少 `HttpOnly` 和 `SameSite` 設定
- **修法**（一行搞定）：
  ```python
  app.config['SESSION_COOKIE_HTTPONLY'] = True
  app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
  ```

### 5. Rate Limiting（登入暴力破解防護）
- **現狀**：登入無任何頻率限制，可無限嘗試密碼
- **建議**：`flask-limiter` 對 `/login` POST 設 5 次/分鐘
- **注意**：Vercel Serverless 無共享記憶體，需用 Neon DB 做計數器或 Upstash Redis

### 6. DB Index 補建
- **現狀**：`reports` 表除 PK 外無索引，隨資料量增長查詢變慢
- **建議**：
  ```sql
  CREATE INDEX idx_reports_user_id ON reports(user_id);
  CREATE INDEX idx_reports_project_no ON reports(project_no);
  CREATE INDEX idx_reports_invoice_no ON reports(invoice_no);
  CREATE INDEX idx_reports_invoice_date ON reports(invoice_date DESC);
  CREATE INDEX idx_vendors_name ON vendors(name);
  ```

### 7. 分頁機制
- **現狀**：清單頁一次撈全部 reports，無分頁
- **臨界點**：300 筆起明顯變慢，500+ 筆 DOM 過大影響手機體驗
- **建議**：`?page=1&per_page=50`，SQL `LIMIT/OFFSET`，加總改為獨立 `SUM()` SQL

### 8. 篩選 / 搜尋功能
- 與分頁一起做最划算（同一段 SQL WHERE）
- MVP：日期區間 + 廠商名稱 + 案場名稱

---

## 🟢 P2 — 近期改善

### 9. 設計師自行修改密碼
- 降低管理員日常支援成本
- `/change-password` 頁，驗舊密碮 → 設新密碼，要求 8 字元 + 英數混合

### 10. 密碼安全政策
- 現無最小長度、複雜度要求
- 管理員重設密碼後可加「首次登入強制改密碼」flag

### 11. 廠商匯入檔案驗證強化
- 限制上傳大小（如 2MB）、驗證 MIME type、限制匯入行數上限（如 500 筆）

### 12. 完整審計日誌
- 目前只記 `updated_by/updated_at`（最後一次），刪除無記錄
- 建議新增 `audit_log` 表記錄所有 INSERT/UPDATE/DELETE

### 13. DB 連線池
- **現狀**：每次 request 都 `psycopg2.connect()` → `close()`
- **風險**：Neon 免費版有連線數上限，多人操作可能 500
- **建議**：啟用 Neon 的 connection pooler (PgBouncer) 或改連 pooler endpoint

---

## 🔵 P3 — 未來規劃

### 14. 台灣假日 2028 年更新
- `TW_HOLIDAYS` 只到 2027 年底，2027 Q4 前需更新
- 長期：改為 DB 表或外部 JSON，提供管理介面維護

### 15. 報表篩選後匯出
- 匯出帶入當前篩選條件，而非全量

### 16. Dashboard / 統計圖表
- Chart.js，月度趨勢 + 廠商佔比 + 案場花費

### 17. 測試自動化 CI
- GitHub Actions：push 時自動跑 test_scenario.py

### 18. Error Tracking
- Sentry Free Plan + UptimeRobot 監控

---

## 阻塞點總覽

| 項目 | 阻塞原因 | 解法 |
|------|----------|------|
| ~~CSRF~~ | ~~已完成~~ | ✅ |
| Rate Limiting | Vercel 無共享記憶體 | Neon DB 計數器或 Upstash Redis |
| DB Migration | 無 migration 工具 | 手動 Neon Console 或引入 Alembic |
| Connection Pool | Serverless cold start | Neon PgBouncer pooler endpoint |

---

## 已解除的阻塞

- ~~無 CSRF 防護~~ → flask-wtf CSRFProtect，19 個表單全覆蓋
- ~~DELETE/UPDATE 路由未回 403~~ → V3 已修復
- ~~SESSION_COOKIE_SECURE 破壞本地測試~~ → VERCEL 環境變數偵測
- ~~驗收流程未跑通~~ → 69/69 scenario test 全通過
- ~~UI 不夠精緻~~ → Apple 極簡風格，含 Dark Mode + 全裝置自適應

---

## PM 建議：下一步先做哪一件？

**第一步：Session Cookie 安全強化（P1 #4）。** 兩行設定，零風險，5 分鐘搞定。和 CSRF 合在一起構成完整的 session 安全防護。

**第二步：DB Index（P1 #6）。** 五條 CREATE INDEX，預防性維護，愈早做愈好。等資料量上來再加會有 lock table 風險。

**第三步：分頁 + 篩選（P1 #7-8 一起做）。** 這是使用體驗的拐點——現在不痛，3 個月後會非常痛。兩個功能共用同一段 SQL 改動，分開做反而浪費。
