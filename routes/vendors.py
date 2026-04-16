from io import BytesIO

import pandas as pd
import psycopg2
from flask import Blueprint, jsonify, redirect, render_template, request, send_file, session

from services.utils import admin_required, get_conn, get_current_user, login_required

bp = Blueprint('vendors', __name__)


@bp.route('/vendors')
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


@bp.route('/vendors/create', methods=['POST'])
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
        cur.close()
        return redirect('/vendors?error=duplicate')
    cur.close()
    return redirect('/vendors')


@bp.route('/vendors/update/<int:vendor_id>', methods=['POST'])
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
        cur.close()
        return redirect('/vendors?error=duplicate')
    cur.close()
    return redirect('/vendors')


@bp.route('/vendors/delete/<int:vendor_id>', methods=['POST'])
@admin_required
def vendor_delete(vendor_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    conn.commit()
    cur.close()
    return redirect('/vendors')


@bp.route('/vendors/template')
@login_required
def vendor_template():
    df = pd.DataFrame(columns=['名稱', '銀行分行名稱', '銀行代碼', '帳號', '戶名'])
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    return send_file(output, as_attachment=True,
                     download_name='廠商匯款資料範本.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/vendors/import', methods=['POST'])
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

    session['import_result'] = {
        'added': added, 'updated': updated,
        'skipped': skipped, 'errors': errors
    }
    return redirect('/vendors')


@bp.route('/api/vendor-bank')
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
    if row:
        return jsonify({
            'bank_name': row[0], 'bank_code': row[1],
            'account_no': row[2], 'account_name': row[3]
        })
    return jsonify({})
