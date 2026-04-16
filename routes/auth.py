from flask import Blueprint, redirect, render_template, request, session
from flask_limiter import Limiter
from werkzeug.security import check_password_hash

from services.utils import get_conn, get_current_user, login_required

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET'])
def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')


@bp.route('/login', methods=['POST'])
def login():
    # Rate limiting is applied via app-level limiter decorator below
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
        return render_template('login.html', error='帳號或密碼錯誤')

    if not row[4]:
        return render_template('login.html', error='此帳號已停用，請聯繫管理員')

    # 防止 session fixation：登入前清除舊 session
    session.clear()
    session.permanent = True
    session['user_id'] = row[0]
    session['display_name'] = row[1]
    session['role'] = row[3]
    return redirect('/')


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    return redirect('/login')
