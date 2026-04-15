import os
from datetime import date, timedelta
from functools import wraps
from io import BytesIO

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv('.env.local')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.permanent_session_lifetime = timedelta(days=7)


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
                   u2.display_name as updater_name
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
                   NULL as updater_name
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

    cur.close()
    conn.close()
    return render_template('list.html', reports=rows, user=user, projects=projects)


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
                           today=date.today().isoformat(), user=user)


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
                             invoice_no, invoice_date, remit_date, project_no, stage, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (vendor, vendor_type, amount_str, category,
          invoice_no, invoice_date, remit_date, project_no, stage, user['id']))
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

    if user['role'] == 'designer':
        cur.execute("SELECT user_id FROM reports WHERE id = %s", (report_id,))
        row = cur.fetchone()
        if not row or row[0] != user['id']:
            cur.close()
            conn.close()
            abort(403)
        cur.execute("UPDATE reports SET remit_date = %s WHERE id = %s",
                    (remit_date, report_id))
    else:
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
    amount = request.form.get('amount', '').strip()
    invoice_no = request.form.get('invoice_no', '').strip() or None
    invoice_date = request.form.get('invoice_date', '').strip()
    remit_date = request.form.get('remit_date', '').strip() or None
    project_no = request.form.get('project_no', '').strip()

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
            project_no = %s, updated_by = %s, updated_at = NOW()
        WHERE id = %s
    """, (vendor, category, amount, invoice_no, invoice_date,
          remit_date, project_no, user['id'], report_id))
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
    vendors = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    similar = []
    for v in vendors:
        v_core = v
        for kw in keywords:
            v_core = v_core.replace(kw, '')
        v_core = v_core.strip()
        if v_core and (v_core == core or core in v_core or v_core in core):
            similar.append(v)

    return jsonify({'similar': similar})


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
                   r.invoice_no, r.remit_date
            FROM reports r
            JOIN users u ON r.user_id = u.id
            ORDER BY r.vendor_type, r.vendor, r.invoice_date
        """, conn)
    else:
        df = pd.read_sql("""
            SELECT invoice_date, vendor_type, vendor, project_no, stage,
                   category, amount, invoice_no, remit_date
            FROM reports
            WHERE user_id = %s
            ORDER BY vendor_type, vendor, invoice_date
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
            'remit_date': '匯款日期',
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
            'remit_date': '匯款日期',
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
