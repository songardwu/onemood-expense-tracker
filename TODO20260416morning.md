# TODO — 2026-04-16 Morning (Updated)

## Completed This Session

- [x] ~~69/69 測試~~ → 已修復（`S\_%` → `S_%`），69/69 全綠，commit `90b8c8b`
- [x] ~~git tag v4-final~~ → 已建立，指向 `32e988b`，已推至 remote
- [x] ~~Bento Grid 雙重卡片修正~~ → 已加 `bento-cell--transparent`，commit `2b08351`

---

## Priority 1: HIGH (UAT 前完成)

- [x] ~~線上版面目視確認~~ → `90b8c8b` 已部署至 Vercel production（2026-04-16），需 `Ctrl+Shift+R` 逐頁確認
- [ ] **UAT 驗收** — 管理員當面看桌面版 5 頁 + 設計師手機看 `/new` 和 `/`，收集回饋（taskv6.md T5-09）
- [x] ~~Before/After 對比圖~~ → UAT 驗收文件 `UAT20260416.md` 已建立，含 10 組截圖對照表 + 變更摘要
- [ ] **iOS Safari 實測** — `/new` 頁面點 input 確認無自動縮放、safe area 正常、字型正確（taskv6.md T5-03）
- [ ] **4G 效能測試** — Chrome DevTools → Network → Throttle: Fast 3G，載入 `/new`，確認 FCP ≤ 2s（taskv6.md T5-04）

## Priority 2: MEDIUM (觀察期 1-3 天內)

- [ ] **跨瀏覽器驗證** — Chrome + Edge + Firefox 桌面版逐頁確認（taskv6.md T5-05）
- [ ] **Dark Mode 視覺驗證** — 系統切 dark mode 確認暖棕背景、文字可讀、無灰色調（Phase 4 SHOULD，已實作但未實機驗證）
- [ ] **Vercel Git 自動部署修復** — git push 未觸發 Vercel 自動部署，目前靠 `npx vercel --prod` 手動。需檢查 Vercel Dashboard → Settings → Git → Production Branch 是否為 `master`
- [ ] **users.html 版面確認** — 目前 users 頁的兩個 bento-cell 未加 `--transparent`，需目視確認是否有雙重卡片效果，有則加上

## Priority 3: LOW (後續迭代)

- [ ] **taskv6.md 狀態更新** — 46 項任務的 checkbox 全部還是 `[ ]`，需標記為 `[x]`
- [ ] **prdv6.md 驗收清單勾選** — Section 15 的 MUST / SHOULD checklist 需逐項確認勾選

## Blockers

| Blocker | 影響 | 解法 |
|---------|------|------|
| Vercel 未自動部署 | 每次改動需手動 `npx vercel --prod` | 檢查 Vercel Git Settings，確認 Production Branch = `master` |
| ~~最新 commit 未部署~~ | ~~已解決~~ | `90b8c8b` 已部署（2026-04-16） |
