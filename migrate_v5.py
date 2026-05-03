"""V5 Migration: 客戶請款單模組（invoices + invoice_lines + project_payments.invoice_id）"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env.local')

url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
conn = psycopg2.connect(url)
cur = conn.cursor()

# 1. 請款單主檔
cur.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id SERIAL PRIMARY KEY,
        invoice_no VARCHAR(20) UNIQUE NOT NULL,
        client_name VARCHAR(200) NOT NULL,
        client_address VARCHAR(300),
        period_year INTEGER NOT NULL,
        period_month INTEGER NOT NULL,
        total_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'draft',
        issued_by INTEGER REFERENCES users(id),
        issued_at TIMESTAMP,
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
""")
print("[OK] invoices table created")

# 2. 請款單明細
cur.execute("""
    CREATE TABLE IF NOT EXISTS invoice_lines (
        id SERIAL PRIMARY KEY,
        invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
        project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
        description VARCHAR(300) NOT NULL,
        suggested_amount NUMERIC(12,2),
        amount NUMERIC(12,2) NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW()
    )
""")
print("[OK] invoice_lines table created")

# 3. project_payments 加上 invoice_id（nullable）
cur.execute("""
    ALTER TABLE project_payments
        ADD COLUMN IF NOT EXISTS invoice_id INTEGER REFERENCES invoices(id) ON DELETE SET NULL
""")
print("[OK] project_payments.invoice_id added")

# 4. 索引
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_period ON invoices(period_year, period_month)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice ON invoice_lines(invoice_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_invoice_lines_project ON invoice_lines(project_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_project_payments_invoice ON project_payments(invoice_id)")
print("[OK] indexes created")

conn.commit()
cur.close()
conn.close()
print("Migration v5 done.")
