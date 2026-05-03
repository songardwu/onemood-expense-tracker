-- Phase 2: 客戶請款單模組
-- 一張請款單可列多個案場（invoice_lines），半自動建議金額沿用案場 remaining_balance

-- =====================
-- 請款單主檔
-- =====================
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(20) UNIQUE NOT NULL,        -- INV-YYYYMM-NNN
    client_name VARCHAR(200) NOT NULL,             -- 客戶名稱
    client_address VARCHAR(300),                   -- 寄送地址
    period_year INTEGER NOT NULL,                  -- 請款月份-年
    period_month INTEGER NOT NULL,                 -- 請款月份-月
    total_amount NUMERIC(12,2) NOT NULL DEFAULT 0, -- 從 lines 加總（後端計算後寫回）
    status VARCHAR(20) NOT NULL DEFAULT 'draft',   -- draft / issued / paid / void
    issued_by INTEGER REFERENCES users(id),        -- 開立者
    issued_at TIMESTAMP,                           -- 開立時間
    notes TEXT,                                    -- 備註
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 請款單明細（一張單列多案場）
-- =====================
CREATE TABLE IF NOT EXISTS invoice_lines (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,  -- 對應案場（可空，允許自訂行）
    description VARCHAR(300) NOT NULL,             -- 說明（預設帶案名）
    suggested_amount NUMERIC(12,2),                -- 系統建議金額（留檔對照）
    amount NUMERIC(12,2) NOT NULL,                 -- 實際開立金額（可手動覆蓋）
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 收款 → 請款單關聯（nullable，舊資料不影響）
-- =====================
ALTER TABLE project_payments
    ADD COLUMN IF NOT EXISTS invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL;

-- =====================
-- 索引
-- =====================
CREATE INDEX IF NOT EXISTS idx_invoices_period ON invoices(period_year, period_month);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice ON invoice_lines(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_project ON invoice_lines(project_id);
CREATE INDEX IF NOT EXISTS idx_project_payments_invoice ON project_payments(invoice_id);
