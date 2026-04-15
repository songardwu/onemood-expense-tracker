"""V4 Migration: vendors table + reports.payment_method"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env.local')

url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
conn = psycopg2.connect(url)
cur = conn.cursor()

# 1. 建立 vendors 表
cur.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id SERIAL PRIMARY KEY,
        name VARCHAR(200) UNIQUE NOT NULL,
        bank_name VARCHAR(200) NOT NULL,
        bank_code VARCHAR(50) NOT NULL,
        account_no VARCHAR(50) NOT NULL,
        account_name VARCHAR(200) NOT NULL,
        created_by INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT NOW(),
        updated_by INTEGER REFERENCES users(id),
        updated_at TIMESTAMP
    )
""")
print("[OK] vendors table created")

# 2. reports 新增 payment_method 欄位
cur.execute("""
    ALTER TABLE reports ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20)
""")
print("[OK] reports.payment_method added")

conn.commit()
cur.close()
conn.close()
print("Migration v4 done.")
