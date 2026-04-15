"""
V2 資料庫遷移腳本 — 執行一次
1. 建 users 表
2. 插入初始管理員帳號（Dawn）
3. reports 加 user_id 欄位
4. 既有 reports 全部歸屬 Dawn (user_id = 1)
5. user_id 設為 NOT NULL
"""

from werkzeug.security import generate_password_hash
from app import get_conn


def migrate():
    conn = get_conn()
    cur = conn.cursor()

    # 1. 建 users 表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('designer', 'admin')),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. 插入初始管理員
    pw_hash = generate_password_hash('admin123')
    cur.execute("""
        INSERT INTO users (username, display_name, password_hash, role)
        VALUES ('dawn', 'Dawn', %s, 'admin')
        ON CONFLICT (username) DO NOTHING;
    """, (pw_hash,))

    # 3. reports 加 user_id
    cur.execute("""
        ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);
    """)

    # 4. 既有資料歸屬 Dawn (id=1)
    cur.execute("UPDATE reports SET user_id = 1 WHERE user_id IS NULL;")

    # 5. 設 NOT NULL
    cur.execute("ALTER TABLE reports ALTER COLUMN user_id SET NOT NULL;")

    conn.commit()
    cur.close()
    conn.close()
    print('V2 migration completed!')


if __name__ == '__main__':
    migrate()
