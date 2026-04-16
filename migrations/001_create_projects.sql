-- Phase 1: 案場損益管理 - 核心資料表
-- 執行前請確認 PostgreSQL 已連線至正確的資料庫

-- =====================
-- 案場主檔
-- =====================
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(20) UNIQUE NOT NULL,        -- 系統自動流水號 CASE-YYYYMMDD-NNN
    case_name VARCHAR(200) NOT NULL,            -- 案名（手動輸入）
    owner_name VARCHAR(100),                    -- 業主姓名
    owner_phone VARCHAR(30),                    -- 業主電話
    owner_address VARCHAR(300),                 -- 業主地址
    contract_date DATE,                         -- 簽約日期
    construction_start DATE,                    -- 施工開始日
    construction_end DATE,                      -- 施工結束日
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active / completed / closed
    designer_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 合約收入
-- =====================
ALTER TABLE projects ADD COLUMN IF NOT EXISTS system_furniture_amount NUMERIC(12,2) DEFAULT 0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS non_system_furniture_amount NUMERIC(12,2) DEFAULT 0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(12,2) DEFAULT 0;         -- 5% 營業稅
ALTER TABLE projects ADD COLUMN IF NOT EXISTS deposit_amount NUMERIC(12,2) DEFAULT 0;     -- 裝修押金
ALTER TABLE projects ADD COLUMN IF NOT EXISTS deposit_refund NUMERIC(12,2) DEFAULT 0;     -- 實際退還金額
ALTER TABLE projects ADD COLUMN IF NOT EXISTS deposit_status VARCHAR(20) DEFAULT 'pending'; -- pending / partial / refunded

-- =====================
-- 追加減明細
-- =====================
CREATE TABLE IF NOT EXISTS project_adjustments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    adjust_date DATE,
    description VARCHAR(300),
    amount NUMERIC(12,2) NOT NULL,              -- 正數為追加，負數為減少
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 折讓/扣抵明細
-- =====================
CREATE TABLE IF NOT EXISTS project_discounts (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    item_name VARCHAR(200) NOT NULL,            -- 項目名稱（丈量費、客變費等）
    amount NUMERIC(12,2) NOT NULL,              -- 折讓金額（正數）
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 收款明細
-- =====================
CREATE TABLE IF NOT EXISTS project_payments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    payment_date DATE NOT NULL,
    payment_method VARCHAR(20) NOT NULL,         -- 現金 / 匯款 / 其他
    amount NUMERIC(12,2) NOT NULL,
    is_confirmed BOOLEAN DEFAULT FALSE,          -- 對帳確認
    confirmed_by INTEGER REFERENCES users(id),
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- 支出成本明細
-- =====================
CREATE TABLE IF NOT EXISTS cost_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cost_type VARCHAR(20) NOT NULL,              -- system / non_system
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);

-- 預設系統工程成本科目
INSERT INTO cost_categories (name, cost_type, sort_order) VALUES
    ('系統板材', 'system', 1),
    ('運費', 'system', 2),
    ('組裝工資', 'system', 3),
    ('五金(博士家)', 'system', 4),
    ('3D製圖費', 'system', 5),
    ('其他系統費用', 'system', 6)
ON CONFLICT DO NOTHING;

-- 預設非系統工程成本科目
INSERT INTO cost_categories (name, cost_type, sort_order) VALUES
    ('室內裝修審查費', 'non_system', 1),
    ('保護', 'non_system', 2),
    ('木工', 'non_system', 3),
    ('油漆', 'non_system', 4),
    ('水電', 'non_system', 5),
    ('木地板', 'non_system', 6),
    ('泥作', 'non_system', 7),
    ('拆除', 'non_system', 8),
    ('其他非系統費用', 'non_system', 9)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS project_costs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES cost_categories(id),
    amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    UNIQUE(project_id, category_id)
);

-- =====================
-- 分潤結算
-- =====================
ALTER TABLE projects ADD COLUMN IF NOT EXISTS profit_share_pct NUMERIC(5,2) DEFAULT 0;  -- 設計師分潤比
ALTER TABLE projects ADD COLUMN IF NOT EXISTS bonus_checked BOOLEAN DEFAULT FALSE;       -- 管理者核對
ALTER TABLE projects ADD COLUMN IF NOT EXISTS bonus_disbursed BOOLEAN DEFAULT FALSE;     -- 已出帳
ALTER TABLE projects ADD COLUMN IF NOT EXISTS bonus_report_id INTEGER REFERENCES reports(id); -- 關聯的報帳紀錄

-- =====================
-- 審計日誌
-- =====================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT NOW(),
    reason TEXT                                   -- 解鎖原因等
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record ON audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_projects_designer ON projects(designer_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
