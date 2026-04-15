import os
from datetime import date, timedelta
from functools import wraps
from io import BytesIO

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv('.env.local')

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.secret_key = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = bool(os.environ.get('VERCEL'))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(days=7)

csrf = CSRFProtect(app)


# =====================
# DB 連線
# =====================
def get_conn():
    url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    return psycopg2.connect(url)


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
# 安全 HTTP headers
# =====================
@app.errorhandler(400)
def handle_csrf_error(e):
    if 'CSRF' in str(e):
        return render_template('login.html', error='操作逾時，請重新操作。'), 400
    return e


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
    return response


# =====================
# 登入 / 登出
# =====================
@app.route('/login', methods=['GET'])
def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, display_name, password_hash, role, is_active
        FROM users WHERE username = %s
    """, (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row or not check_password_hash(row[2], password):
        return render_template('login.html', error='帳號或密碼錯誤')

    if not row[4]:
        return render_template('login.html', error='此帳號已停用，請聯繫管理員')

    session.permanent = True
    session['user_id'] = row[0]
    session['display_name'] = row[1]
    session['role'] = row[3]
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# =====================
# GET / — 清單頁
# =====================
@app.route('/')
@login_required
def index():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    if user['role'] == 'admin':
        cur.execute("""
            SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
                   r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
                   r.stage, r.created_at, u.display_name,
                   r.is_locked, r.updated_by, r.updated_at,
                   u2.display_name as updater_name, r.payment_method
            FROM reports r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN users u2 ON r.updated_by = u2.id
            ORDER BY r.invoice_date DESC, r.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT r.id, r.vendor, r.vendor_type, r.amount, r.category,
                   r.invoice_no, r.invoice_date, r.remit_date, r.project_no,
                   r.stage, r.created_at, NULL as display_name,
                   r.is_locked, NULL as updated_by, NULL as updated_at,
                   NULL as updater_name, r.payment_method
            FROM reports r
            WHERE r.user_id = %s
            ORDER BY r.invoice_date DESC, r.created_at DESC
        """, (user['id'],))

    rows = cur.fetchall()

    # 案場鎖定狀態（管理員用）
    projects = []
    if user['role'] == 'admin':
        cur.execute("""
            SELECT project_no, bool_or(is_locked) as any_locked, COUNT(*) as cnt
            FROM reports
            GROUP BY project_no
            ORDER BY project_no
        """)
        projects = [{'project_no': r[0], 'any_locked': r[1], 'cnt': r[2]}
                    for r in cur.fetchall()]

    # 廠商加總 + 匯款方式分計 + 總計
    from collections import defaultdict
    vendor_totals = defaultdict(float)
    method_totals = defaultdict(float)
    grand_total = 0.0
    for r in rows:
        amt = float(r[3]) if r[3] else 0
        vendor_totals[r[1]] += amt
        method_totals[r[16] or '未設定'] += amt
        grand_total += amt

    # 相似廠商 / 同帳號標記（廠商名稱相同 OR 銀行帳號相同 → 合併群組）
    cur.execute("SELECT name, account_no, bank_name, bank_code, account_name FROM vendors")
    vendor_rows = cur.fetchall()
    vendor_accounts = {row[0]: row[1] for row in vendor_rows}
    vendor_bank_info = {row[0]: {'account_no': row[1], 'bank_name': row[2], 'bank_code': row[3], 'account_name': row[4]} for row in vendor_rows}

    # 建立合併群組：account_no → [vendor_names]
    acct_to_vendors = defaultdict(set)
    for vname, acct in vendor_accounts.items():
        if acct:
            acct_to_vendors[acct].add(vname)

    # 載入相似比對關鍵字
    cur.execute("SELECT keyword FROM vendor_keywords")
    keywords = [row[0] for row in cur.fetchall()]

    def get_core(name):
        c = name
        for kw in keywords:
            c = c.replace(kw, '')
        return c.strip()

    # 偵測重複：名稱相似 OR 帳號相同
    all_vendors = list(vendor_totals.keys())
    dup_flags = {}  # vendor_name → set of similar vendor names
    for i, v1 in enumerate(all_vendors):
        core1 = get_core(v1)
        acct1 = vendor_accounts.get(v1, '')
        for v2 in all_vendors[i+1:]:
            core2 = get_core(v2)
            acct2 = vendor_accounts.get(v2, '')
            is_similar = False
            # 名稱相似
            if core1 and core2 and (core1 == core2 or core1 in core2 or core2 in core1):
                is_similar = True
            # 帳號相同
            if acct1 and acct2 and acct1 == acct2:
                is_similar = True
            if is_similar:
                dup_flags.setdefault(v1, set()).add(v2)
                dup_flags.setdefault(v2, set()).add(v1)

    # 同帳號合併加總
    acct_totals = defaultdict(float)
    for vname, amt in vendor_totals.items():
        acct = vendor_accounts.get(vname, '')
        if acct:
            acct_totals[acct] += amt

    cur.close()
    conn.close()
    return render_template('list.html', reports=rows, user=user, projects=projects,
                           vendor_totals=dict(vendor_totals),
                           method_totals=dict(method_totals),
                           grand_total=grand_total,
                           dup_flags={k: list(v) for k, v in dup_flags.items()},
                           vendor_bank_info=vendor_bank_info)


# =====================
# GET /new — 新增表單頁
# =====================
@app.route('/new')
@login_required
def new_report():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT vendor FROM reports ORDER BY vendor")
    vendors = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT vendor_type FROM reports ORDER BY vendor_type")
    vendor_types = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('new.html', vendors=vendors, vendor_types=vendor_types,
                           today=date.today().isoformat(), user=user,
                           default_remit_date=default_remit_date().isoformat())


# =====================
# POST /submit — 寫入提報
# =====================
@app.route('/submit', methods=['POST'])
@login_required
def submit():
    user = get_current_user()
    vendor = request.form.get('vendor', '').strip()
    vendor_type = request.form.get('vendor_type', '').strip()
    amount_str = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    invoice_no = request.form.get('invoice_no', '').strip() or None
    invoice_date = request.form.get('invoice_date', '').strip()
    remit_date = request.form.get('remit_date', '').strip() or None
    project_no = request.form.get('project_no', '').strip()
    stage = request.form.get('stage', '').strip() or None
    payment_method = request.form.get('payment_method', '').strip()

    # 匯款日期未填 → 預設下月 5 日（遇假日順延）
    if not remit_date:
        remit_date = default_remit_date().isoformat()

    errors = []
    if not vendor:
        errors.append('名稱為必填')
    if not vendor_type:
        errors.append('廠商類型為必填')
    if not amount_str:
        errors.append('請款金額為必填')
    else:
        try:
            amount = float(amount_str)
            if amount <= 0:
                errors.append('請款金額必須為正數')
        except ValueError:
            errors.append('請款金額必須為數字')
    if category not in ('案場成本', '管銷', '獎金'):
        errors.append('款項分類必須為案場成本、管銷或獎金')
    if payment_method not in ('現金', '公司轉帳', '個帳轉帳'):
        errors.append('匯款方式必須為現金、公司轉帳或個帳轉帳')
    if not invoice_date:
        errors.append('發票收據日期為必填')
    if not project_no:
        errors.append('案場名稱為必填')

    # 發票號碼重複防呆
    if not errors and invoice_no:
        conn_chk = get_conn()
        cur_chk = conn_chk.cursor()
        cur_chk.execute("SELECT id FROM reports WHERE invoice_no = %s", (invoice_no,))
        if cur_chk.fetchone():
            errors.append('此發票號碼已存在，請確認是否重複請款')
        cur_chk.close()
        conn_chk.close()

    if errors:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT vendor FROM reports ORDER BY vendor")
        vendors = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT vendor_type FROM reports ORDER BY vendor_type")
        vendor_types = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return render_template('new.html', error='、'.join(errors),
                               vendors=vendors, vendor_types=vendor_types,
                               today=date.today().isoformat(),
                               form=request.form, user=user)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (vendor, vendor_type, amount, category,
                             invoice_no, invoice_date, remit_date, project_no, stage,
                             payment_method, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (vendor, vendor_type, amount_str, category,
          invoice_no, invoice_date, remit_date, project_no, stage,
          payment_method, user['id']))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# POST /delete/<id> — 刪除提報
# =====================
@app.route('/delete/<int:report_id>', methods=['POST'])
@login_required
def delete(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id, is_locked FROM reports WHERE id = %s", (report_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)
    if row[1]:  # is_locked
        cur.close(); conn.close()
        abort(403)
    if user['role'] == 'designer' and row[0] != user['id']:
        cur.close(); conn.close()
        abort(403)

    cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# POST /update-remit-date/<id> — 修改匯款日期
# =====================
@app.route('/update-remit-date/<int:report_id>', methods=['POST'])
@login_required
def update_remit_date(report_id):
    user = get_current_user()
    remit_date = request.form.get('remit_date', '').strip() or None
    conn = get_conn()
    cur = conn.cursor()

    # 檢查存在 + 鎖定
    cur.execute("SELECT user_id, is_locked FROM reports WHERE id = %s", (report_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)
    if row[1]:  # is_locked
        cur.close(); conn.close()
        abort(403)

    if user['role'] == 'designer' and row[0] != user['id']:
        cur.close(); conn.close()
        abort(403)

    cur.execute("UPDATE reports SET remit_date = %s WHERE id = %s",
                (remit_date, report_id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# POST /update-report/<id> — 管理員全欄位更新
# =====================
@app.route('/update-report/<int:report_id>', methods=['POST'])
@admin_required
def update_report(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    # 檢查存在 + 鎖定
    cur.execute("SELECT is_locked FROM reports WHERE id = %s", (report_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)
    if row[0]:
        cur.close(); conn.close()
        abort(403)

    vendor = request.form.get('vendor', '').strip()
    category = request.form.get('category', '').strip()
    amount_str = request.form.get('amount', '').strip()
    invoice_no = request.form.get('invoice_no', '').strip() or None
    invoice_date = request.form.get('invoice_date', '').strip()
    remit_date = request.form.get('remit_date', '').strip() or None
    project_no = request.form.get('project_no', '').strip()
    payment_method = request.form.get('payment_method', '').strip() or None

    # 輸入驗證
    if not vendor or not invoice_date or not project_no:
        cur.close(); conn.close()
        return redirect('/')
    if category not in ('案場成本', '管銷', '獎金'):
        cur.close(); conn.close()
        return redirect('/')
    if payment_method and payment_method not in ('現金', '公司轉帳', '個帳轉帳'):
        cur.close(); conn.close()
        return redirect('/')
    try:
        amount = float(amount_str)
        if amount <= 0:
            cur.close(); conn.close()
            return redirect('/')
    except (ValueError, TypeError):
        cur.close(); conn.close()
        return redirect('/')

    # 發票防呆（排除自己）
    if invoice_no:
        cur.execute(
            "SELECT id FROM reports WHERE invoice_no = %s AND id != %s",
            (invoice_no, report_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return redirect('/?error=invoice_dup')

    cur.execute("""
        UPDATE reports
        SET vendor = %s, category = %s, amount = %s,
            invoice_no = %s, invoice_date = %s, remit_date = %s,
            project_no = %s, payment_method = %s,
            updated_by = %s, updated_at = NOW()
        WHERE id = %s
    """, (vendor, category, amount_str, invoice_no, invoice_date,
          remit_date, project_no, payment_method, user['id'], report_id))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# POST /toggle-lock-project — 案場鎖定切換
# =====================
@app.route('/toggle-lock-project', methods=['POST'])
@admin_required
def toggle_lock_project():
    project_no = request.form.get('project_no', '').strip()
    action = request.form.get('action', '').strip()

    if not project_no or action not in ('lock', 'unlock'):
        return redirect('/')

    lock_value = action == 'lock'
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE reports SET is_locked = %s WHERE project_no = %s",
                (lock_value, project_no))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# GET /api/check-vendor — 廠商相似比對
# =====================
@app.route('/api/check-vendor')
@login_required
def check_vendor():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'similar': []})

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT keyword FROM vendor_keywords")
    keywords = [row[0] for row in cur.fetchall()]

    # 核心名稱：移除關鍵字
    core = q
    for kw in keywords:
        core = core.replace(kw, '')
    core = core.strip()

    if not core:
        cur.close(); conn.close()
        return jsonify({'similar': []})

    cur.execute("SELECT DISTINCT vendor FROM reports WHERE vendor != %s", (q,))
    report_vendors = [row[0] for row in cur.fetchall()]

    # 也查 vendors 表中的廠商
    cur.execute("SELECT name, account_no FROM vendors")
    vendor_accounts = {row[0]: row[1] for row in cur.fetchall()}

    # 查詢輸入廠商的銀行帳號
    q_account = vendor_accounts.get(q, '')

    cur.close()
    conn.close()

    similar = set()
    all_names = set(report_vendors) | set(vendor_accounts.keys())
    all_names.discard(q)

    for v in all_names:
        v_core = v
        for kw in keywords:
            v_core = v_core.replace(kw, '')
        v_core = v_core.strip()
        # 名稱相似
        if v_core and (v_core == core or core in v_core or v_core in core):
            similar.add(v)
        # 銀行帳號相同
        if q_account and vendor_accounts.get(v, '') == q_account:
            similar.add(v)

    return jsonify({'similar': sorted(similar)})


# =====================
# 廠商匯款資料管理
# =====================
@app.route('/vendors')
@login_required
def vendor_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, bank_name, bank_code, account_no, account_name
        FROM vendors ORDER BY name
    """)
    vendors = cur.fetchall()
    cur.close()
    conn.close()

    error = request.args.get('error')
    error_msg = None
    if error == 'missing':
        error_msg = '所有欄位皆為必填'
    elif error == 'duplicate':
        error_msg = '此廠商名稱已存在'
    elif error == 'nofile':
        error_msg = '請選擇檔案'
    elif error == 'badformat':
        error_msg = '僅支援 .xlsx 或 .csv 格式'
    elif error == 'badcolumns':
        error_msg = '檔案欄位不符，請使用範本格式'

    import_result = session.pop('import_result', None)
    return render_template('vendors.html', vendors=vendors, user=user,
                           error=error_msg, import_result=import_result)


@app.route('/vendors/create', methods=['POST'])
@login_required
def vendor_create():
    user = get_current_user()
    name = request.form.get('name', '').strip()
    bank_name = request.form.get('bank_name', '').strip()
    bank_code = request.form.get('bank_code', '').strip()
    account_no = request.form.get('account_no', '').strip()
    account_name = request.form.get('account_name', '').strip()

    if not all([name, bank_name, bank_code, account_no, account_name]):
        return redirect('/vendors?error=missing')

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO vendors (name, bank_name, bank_code, account_no,
                                 account_name, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, bank_name, bank_code, account_no, account_name, user['id']))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close(); conn.close()
        return redirect('/vendors?error=duplicate')
    cur.close()
    conn.close()
    return redirect('/vendors')


@app.route('/vendors/update/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_update(vendor_id):
    user = get_current_user()
    name = request.form.get('name', '').strip()
    bank_name = request.form.get('bank_name', '').strip()
    bank_code = request.form.get('bank_code', '').strip()
    account_no = request.form.get('account_no', '').strip()
    account_name = request.form.get('account_name', '').strip()

    if not all([name, bank_name, bank_code, account_no, account_name]):
        return redirect('/vendors?error=missing')

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE vendors
            SET name = %s, bank_name = %s, bank_code = %s,
                account_no = %s, account_name = %s,
                updated_by = %s, updated_at = NOW()
            WHERE id = %s
        """, (name, bank_name, bank_code, account_no, account_name,
              user['id'], vendor_id))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close(); conn.close()
        return redirect('/vendors?error=duplicate')
    cur.close()
    conn.close()
    return redirect('/vendors')


@app.route('/vendors/delete/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_delete(vendor_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/vendors')


@app.route('/vendors/template')
@login_required
def vendor_template():
    df = pd.DataFrame(columns=['名稱', '銀行分行名稱', '銀行代碼', '帳號', '戶名'])
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='廠商匯款資料範本.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/vendors/import', methods=['POST'])
@login_required
def vendor_import():
    user = get_current_user()
    file = request.files.get('file')
    if not file or not file.filename:
        return redirect('/vendors?error=nofile')

    filename = file.filename.lower()
    try:
        if filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file, dtype=str)
        else:
            return redirect('/vendors?error=badformat')
    except Exception:
        return redirect('/vendors?error=badformat')

    col_map = {
        '名稱': 'name', '廠商名稱': 'name',
        '銀行分行名稱': 'bank_name', '銀行分行': 'bank_name',
        '銀行代碼': 'bank_code',
        '帳號': 'account_no', '銀行帳號': 'account_no',
        '戶名': 'account_name',
    }
    df.rename(columns=col_map, inplace=True)

    required = ['name', 'bank_name', 'bank_code', 'account_no', 'account_name']
    if not all(c in df.columns for c in required):
        return redirect('/vendors?error=badcolumns')

    added = 0; updated = 0; skipped = 0; errors = []

    conn = get_conn()
    cur = conn.cursor()
    for idx, row in df.iterrows():
        name = str(row.get('name', '')).strip()
        bank_name = str(row.get('bank_name', '')).strip()
        bank_code = str(row.get('bank_code', '')).strip()
        account_no = str(row.get('account_no', '')).strip()
        account_name = str(row.get('account_name', '')).strip()

        if not all([name, bank_name, bank_code, account_no, account_name]):
            errors.append(f'第 {idx+2} 列：欄位不完整')
            continue

        cur.execute("SELECT id FROM vendors WHERE name = %s", (name,))
        existing = cur.fetchone()

        if existing:
            if user['role'] == 'admin':
                cur.execute("""
                    UPDATE vendors
                    SET bank_name = %s, bank_code = %s, account_no = %s,
                        account_name = %s, updated_by = %s, updated_at = NOW()
                    WHERE id = %s
                """, (bank_name, bank_code, account_no, account_name,
                      user['id'], existing[0]))
                updated += 1
            else:
                skipped += 1
        else:
            cur.execute("""
                INSERT INTO vendors (name, bank_name, bank_code, account_no,
                                     account_name, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, bank_name, bank_code, account_no, account_name, user['id']))
            added += 1

    conn.commit()
    cur.close()
    conn.close()

    session['import_result'] = {
        'added': added, 'updated': updated,
        'skipped': skipped, 'errors': errors
    }
    return redirect('/vendors')


@app.route('/api/vendor-bank')
@login_required
def vendor_bank():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({})
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT bank_name, bank_code, account_no, account_name
        FROM vendors WHERE name = %s
    """, (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return jsonify({
            'bank_name': row[0], 'bank_code': row[1],
            'account_no': row[2], 'account_name': row[3]
        })
    return jsonify({})


# =====================
# GET /export — 匯出 Excel
# =====================
@app.route('/export')
@login_required
def export():
    user = get_current_user()
    conn = get_conn()
    is_admin = user['role'] == 'admin'

    if is_admin:
        df = pd.read_sql("""
            SELECT u.display_name as reporter, r.invoice_date, r.vendor_type,
                   r.vendor, r.project_no, r.stage, r.category, r.amount,
                   r.invoice_no, r.remit_date, r.payment_method,
                   v.bank_name, v.bank_code, v.account_no, v.account_name
            FROM reports r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN vendors v ON r.vendor = v.name
            ORDER BY r.vendor_type, r.vendor, r.invoice_date
        """, conn)
    else:
        df = pd.read_sql("""
            SELECT r.invoice_date, r.vendor_type, r.vendor, r.project_no, r.stage,
                   r.category, r.amount, r.invoice_no, r.remit_date, r.payment_method,
                   v.bank_name, v.bank_code, v.account_no, v.account_name
            FROM reports r
            LEFT JOIN vendors v ON r.vendor = v.name
            WHERE r.user_id = %s
            ORDER BY r.vendor_type, r.vendor, r.invoice_date
        """, conn, params=(user['id'],))

    conn.close()

    if df.empty:
        return redirect('/')

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        write_detail_sheet(df, writer, is_admin=is_admin)
        write_summary_sheet(df, writer, is_admin=is_admin)
    output.seek(0)

    today_str = date.today().strftime('%Y%m%d')
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'出帳報表_{today_str}.xlsx'
    )


def write_detail_sheet(df, writer, is_admin=False):
    if is_admin:
        col_map = {
            'reporter': '提報人',
            'invoice_date': '發票收據日期',
            'vendor_type': '廠商類型',
            'vendor': '名稱',
            'project_no': '案場名稱',
            'stage': '階段',
            'category': '款項分類',
            'amount': '請款金額',
            'invoice_no': '發票收據編號',
            'payment_method': '匯款方式',
            'remit_date': '匯款日期',
            'bank_name': '銀行分行名稱',
            'bank_code': '銀行代碼',
            'account_no': '銀行帳號',
            'account_name': '戶名',
        }
    else:
        col_map = {
            'invoice_date': '發票收據日期',
            'vendor_type': '廠商類型',
            'vendor': '名稱',
            'project_no': '案場名稱',
            'stage': '階段',
            'category': '款項分類',
            'amount': '請款金額',
            'invoice_no': '發票收據編號',
            'payment_method': '匯款方式',
            'remit_date': '匯款日期',
            'bank_name': '銀行分行名稱',
            'bank_code': '銀行代碼',
            'account_no': '銀行帳號',
            'account_name': '戶名',
        }

    rows = []

    for vendor, group in df.groupby('vendor', sort=False):
        for _, row in group.iterrows():
            rows.append(row.to_dict())
        subtotal = {'vendor': f'【{vendor} 小計】', 'amount': group['amount'].sum()}
        rows.append(subtotal)

    for cat, group in df.groupby('category'):
        rows.append({
            'category': f'【{cat} 分計】',
            'amount': group['amount'].sum(),
        })

    rows.append({
        'vendor': '【總計】',
        'amount': df['amount'].sum(),
    })

    result = pd.DataFrame(rows)
    ordered_cols = [c for c in col_map.keys() if c in result.columns]
    result = result[ordered_cols]
    result.rename(columns=col_map, inplace=True)
    result.to_excel(writer, sheet_name='明細', index=False)


def write_summary_sheet(df, writer, is_admin=False):
    today = date.today()
    current_year = today.year
    current_month = today.month

    df['invoice_date'] = pd.to_datetime(df['invoice_date'])

    year_df = df[df['invoice_date'].dt.year == current_year]
    month_df = year_df[year_df['invoice_date'].dt.month == current_month]

    categories = ['案場成本', '管銷', '獎金']
    summary_rows = []
    year_total = year_df['amount'].sum()

    for cat in categories:
        month_amount = month_df[month_df['category'] == cat]['amount'].sum()
        year_amount = year_df[year_df['category'] == cat]['amount'].sum()
        pct = (year_amount / year_total * 100) if year_total > 0 else 0
        summary_rows.append({
            '款項分類': cat,
            '本月請款金額': month_amount,
            '當年累計': year_amount,
            '佔比(%)': round(pct, 1),
        })

    summary_rows.append({
        '款項分類': '合計',
        '本月請款金額': month_df['amount'].sum(),
        '當年累計': year_total,
        '佔比(%)': 100.0 if year_total > 0 else 0,
    })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_excel(writer, sheet_name='總覽', index=False)

    # 管理員版：按提報人彙總
    if is_admin and 'reporter' in df.columns:
        reporter_cats = df.groupby(['reporter', 'category'])['amount'].sum().unstack(fill_value=0)
        for cat in categories:
            if cat not in reporter_cats.columns:
                reporter_cats[cat] = 0
        reporter_cats = reporter_cats[categories]
        reporter_cats['小計'] = reporter_cats.sum(axis=1)

        startrow = len(summary_df) + 3
        ws = writer.sheets['總覽']
        ws.cell(row=startrow, column=1, value='按提報人彙總')
        reporter_cats.to_excel(writer, sheet_name='總覽', startrow=startrow)


# =====================
# 帳號管理（admin 專用）
# =====================
@app.route('/users')
@admin_required
def user_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, display_name, role, is_active, created_at
        FROM users ORDER BY role, display_name
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('users.html', users=users, user=user)


@app.route('/users/create', methods=['POST'])
@admin_required
def user_create():
    username = request.form.get('username', '').strip()
    display_name = request.form.get('display_name', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'designer')

    if not username or not display_name or not password:
        return redirect('/users')
    if role not in ('designer', 'admin'):
        role = 'designer'

    pw_hash = generate_password_hash(password)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, display_name, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (username, display_name, pw_hash, role))
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
    cur.close()
    conn.close()
    return redirect('/users')


@app.route('/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def user_toggle(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/users')


@app.route('/users/<int:uid>/reset-password', methods=['POST'])
@admin_required
def user_reset_password(uid):
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        return redirect('/users')
    pw_hash = generate_password_hash(new_password)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, uid))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/users')


if __name__ == '__main__':
    app.run(debug=True)
