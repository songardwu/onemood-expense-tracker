from flask import Blueprint, redirect, render_template, request
from werkzeug.security import generate_password_hash

import psycopg2
from services.utils import admin_required, get_conn, get_current_user

bp = Blueprint('users', __name__)


@bp.route('/users')
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


@bp.route('/users/create', methods=['POST'])
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


@bp.route('/users/<int:uid>/toggle', methods=['POST'])
@admin_required
def user_toggle(uid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s", (uid,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/users')


@bp.route('/users/<int:uid>/reset-password', methods=['POST'])
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
