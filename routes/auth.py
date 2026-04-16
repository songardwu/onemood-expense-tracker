from flask import Blueprint, redirect, render_template, request, session
from flask_limiter import Limiter
from werkzeug.security import check_password_hash, generate_password_hash

from services.utils import admin_required, get_conn, get_current_user, get_page_info, login_required

bp = Blueprint('auth', __name__)


def _log_login(conn, user_id, username, success):
    """記錄登入嘗試"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO login_logs (user_id, username, success, ip_address)
        VALUES (%s, %s, %s, %s)
    """, (user_id, username, success, ip))
    conn.commit()
    cur.close()


@bp.route('/login', methods=['GET'])
def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')


@bp.route('/login', methods=['POST'])
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

    if not row or not check_password_hash(row[2], password):
        _log_login(conn, row[0] if row else None, username, False)
        return render_template('login.html', error='帳號或密碼錯誤')

    if not row[4]:
        _log_login(conn, row[0], username, False)
        return render_template('login.html', error='此帳號已停用，請聯繫管理員')

    _log_login(conn, row[0], username, True)

    # 防止 session fixation：登入前清除舊 session
    session.clear()
    session.permanent = True
    session['user_id'] = row[0]
    session['display_name'] = row[1]
    session['role'] = row[3]
    return redirect('/')


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = get_current_user()
    if request.method == 'GET':
        return render_template('change_password.html', user=user)

    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not old_password or not new_password:
        return render_template('change_password.html', user=user, error='請填寫所有欄位')

    if len(new_password) < 6:
        return render_template('change_password.html', user=user, error='新密碼至少需 6 字元')

    if new_password != confirm_password:
        return render_template('change_password.html', user=user, error='兩次輸入的新密碼不一致')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user['id'],))
    row = cur.fetchone()

    if not row or not check_password_hash(row[0], old_password):
        cur.close()
        return render_template('change_password.html', user=user, error='目前密碼不正確')

    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                (generate_password_hash(new_password), user['id']))
    conn.commit()
    cur.close()
    return render_template('change_password.html', user=user, success='密碼已更新成功')


@bp.route('/login-logs')
@admin_required
def login_logs():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM login_logs")
    total = cur.fetchone()[0]
    page, per_page, offset, total_pages = get_page_info(total, per_page=50)
    cur.execute("""
        SELECT ll.created_at, ll.username, ll.success, ll.ip_address,
               u.display_name
        FROM login_logs ll
        LEFT JOIN users u ON ll.user_id = u.id
        ORDER BY ll.created_at DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    logs = cur.fetchall()
    cur.close()
    return render_template('login_logs.html', logs=logs, user=user,
                           page=page, total_pages=total_pages,
                           total_count=total)


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    return redirect('/login')
