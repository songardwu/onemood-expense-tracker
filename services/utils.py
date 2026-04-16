import math
import os
from datetime import date, timedelta
from functools import wraps

import psycopg2
from flask import g, redirect, request, session

# =====================
# 台灣國定假日 + 匯款日期計算
# =====================
TW_HOLIDAYS_2026 = {
    date(2026, 1, 1),   # 元旦
    date(2026, 1, 2),   # 元旦補假
    date(2026, 2, 14),  # 除夕前調整放假
    date(2026, 2, 15),  # 除夕前調整放假
    date(2026, 2, 16),  # 除夕
    date(2026, 2, 17),  # 春節
    date(2026, 2, 18),  # 春節
    date(2026, 2, 19),  # 春節
    date(2026, 2, 20),  # 春節補假
    date(2026, 2, 28),  # 和平紀念日（六）
    date(2026, 3, 2),   # 和平紀念日補假（一）
    date(2026, 4, 3),   # 兒童節（五）
    date(2026, 4, 4),   # 清明節（六）
    date(2026, 4, 6),   # 清明補假（一）
    date(2026, 5, 1),   # 勞動節
    date(2026, 5, 31),  # 端午節（日）
    date(2026, 6, 1),   # 端午補假（一）
    date(2026, 10, 1),  # 中秋節（四）
    date(2026, 10, 2),  # 中秋節補假（五）
    date(2026, 10, 10), # 國慶日（六）
    date(2026, 10, 12), # 國慶補假（一）
}

TW_HOLIDAYS_2027 = {
    date(2027, 1, 1),   # 元旦
    date(2027, 2, 5),   # 除夕前
    date(2027, 2, 6),   # 除夕
    date(2027, 2, 7),   # 春節
    date(2027, 2, 8),   # 春節
    date(2027, 2, 9),   # 春節
    date(2027, 2, 10),  # 春節補假
    date(2027, 2, 28),  # 和平紀念日（日）
    date(2027, 3, 1),   # 和平紀念日補假
    date(2027, 4, 4),   # 清明節（日）
    date(2027, 4, 5),   # 兒童節（一）
    date(2027, 5, 1),   # 勞動節
    date(2027, 6, 19),  # 端午節（六）
    date(2027, 6, 21),  # 端午補假（一）
    date(2027, 9, 25),  # 中秋節（六）
    date(2027, 9, 27),  # 中秋補假（一）
    date(2027, 10, 10), # 國慶日（日）
    date(2027, 10, 11), # 國慶補假（一）
}

TW_HOLIDAYS = TW_HOLIDAYS_2026 | TW_HOLIDAYS_2027


def is_business_day(d):
    """判斷是否為工作日（排除週末 + 台灣國定假日）"""
    if d.weekday() >= 5:  # 六=5, 日=6
        return False
    if d in TW_HOLIDAYS:
        return False
    return True


def next_business_day(d):
    """找到 d 當天或之後的第一個工作日"""
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def default_remit_date(from_date=None):
    """計算預設匯款日期：下個月 5 日，遇假日順延"""
    if from_date is None:
        from_date = date.today()
    # 下個月
    if from_date.month == 12:
        target = date(from_date.year + 1, 1, 5)
    else:
        target = date(from_date.year, from_date.month + 1, 5)
    return next_business_day(target)


# =====================
# DB 連線（Flask g 自動回收，防洩漏）
# =====================
def get_conn():
    """取得 DB 連線，同一 request 內共用，結束時自動關閉"""
    if 'db' not in g:
        url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
        g.db = psycopg2.connect(url)
    return g.db


def close_db(e=None):
    """teardown_appcontext callback — 自動關閉連線"""
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


# =====================
# 認證工具
# =====================
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return {
        'id': user_id,
        'role': session.get('role'),
        'display_name': session.get('display_name'),
    }


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect('/login')
        if user['role'] != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return decorated


# =====================
# Audit Log
# =====================
def write_audit_log(cur, table_name, record_id, field_name,
                    old_value, new_value, user_id, reason=None):
    cur.execute("""
        INSERT INTO audit_logs (table_name, record_id, field_name,
                                old_value, new_value, changed_by, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (table_name, record_id, field_name,
          str(old_value) if old_value is not None else None,
          str(new_value) if new_value is not None else None,
          user_id, reason))


# =====================
# 案場權限檢查
# =====================
def check_project_access(cur, project_id, user, require_editable=True):
    """檢查案場存取權限，回傳 project dict 或 None"""
    cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        return None
    col_names = [desc[0] for desc in cur.description]
    proj = dict(zip(col_names, row))
    # 設計師只能存取自己的案場
    if user['role'] != 'admin' and proj['designer_id'] != user['id']:
        return None
    # 結案後不可編輯（admin 除外）
    if require_editable and proj['status'] == 'closed' and user['role'] != 'admin':
        return None
    return proj


# =====================
# 分頁工具
# =====================
def get_page_info(total, per_page=50):
    """從 request.args 取得分頁資訊，回傳 (page, per_page, offset, total_pages)"""
    page = request.args.get('page', 1, type=int)
    page = max(1, page)
    total_pages = max(1, math.ceil(total / per_page))
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    return page, per_page, offset, total_pages
