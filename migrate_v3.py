"""V3 資料庫遷移：reports 加 is_locked/updated_by/updated_at + vendor_keywords 表"""
from app import get_conn


def migrate():
    conn = get_conn()
    cur = conn.cursor()

    # reports 加欄位
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            is_locked BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            updated_by INTEGER REFERENCES users(id);
    """)
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS
            updated_at TIMESTAMP;
    """)

    # vendor_keywords 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendor_keywords (
            id SERIAL PRIMARY KEY,
            keyword VARCHAR(50) NOT NULL UNIQUE
        );
    """)
    for kw in ['公司', '行', '工作室', '企業', '設計', '工程',
               '有限', '股份', '實業', '工坊']:
        cur.execute("""
            INSERT INTO vendor_keywords (keyword) VALUES (%s)
            ON CONFLICT (keyword) DO NOTHING;
        """, (kw,))

    conn.commit()
    cur.close()
    conn.close()
    print('V3 migration done')


if __name__ == '__main__':
    migrate()
