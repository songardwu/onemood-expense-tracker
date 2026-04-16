from collections import defaultdict
from datetime import date
from io import BytesIO

import pandas as pd
from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file

from services.utils import (
    admin_required,
    default_remit_date,
    get_conn,
    get_current_user,
    login_required,
)

bp = Blueprint('reports', __name__)


# =====================
# GET / — 清單頁
# =====================
@bp.route('/')
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
    vendor_totals = defaultdict(float)
    method_totals = defaultdict(float)
    grand_total = 0.0
    for r in rows:
        amt = float(r[3]) if r[3] else 0
        vendor_totals[r[1]] += amt
        method_totals[r[16] or '未設定'] += amt
        grand_total += amt

    # 相似廠商 / 同帳號標記
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
    dup_flags = {}
    for i, v1 in enumerate(all_vendors):
        core1 = get_core(v1)
        acct1 = vendor_accounts.get(v1, '')
        for v2 in all_vendors[i+1:]:
            core2 = get_core(v2)
            acct2 = vendor_accounts.get(v2, '')
            is_similar = False
            if core1 and core2 and (core1 == core2 or core1 in core2 or core2 in core1):
                is_similar = True
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
@bp.route('/new')
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
@bp.route('/submit', methods=['POST'])
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
@bp.route('/delete/<int:report_id>', methods=['POST'])
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
@bp.route('/update-remit-date/<int:report_id>', methods=['POST'])
@login_required
def update_remit_date(report_id):
    user = get_current_user()
    remit_date = request.form.get('remit_date', '').strip() or None
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

    cur.execute("UPDATE reports SET remit_date = %s WHERE id = %s",
                (remit_date, report_id))

    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# =====================
# POST /update-report/<id> — 管理員全欄位更新
# =====================
@bp.route('/update-report/<int:report_id>', methods=['POST'])
@admin_required
def update_report(report_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

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
@bp.route('/toggle-lock-project', methods=['POST'])
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
@bp.route('/api/check-vendor')
@login_required
def check_vendor():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'similar': []})

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT keyword FROM vendor_keywords")
    keywords = [row[0] for row in cur.fetchall()]

    core = q
    for kw in keywords:
        core = core.replace(kw, '')
    core = core.strip()

    if not core:
        cur.close(); conn.close()
        return jsonify({'similar': []})

    cur.execute("SELECT DISTINCT vendor FROM reports WHERE vendor != %s", (q,))
    report_vendors = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT name, account_no FROM vendors")
    vendor_accounts = {row[0]: row[1] for row in cur.fetchall()}

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
        if v_core and (v_core == core or core in v_core or v_core in core):
            similar.add(v)
        if q_account and vendor_accounts.get(v, '') == q_account:
            similar.add(v)

    return jsonify({'similar': sorted(similar)})


# =====================
# GET /export — 匯出 Excel
# =====================
@bp.route('/export')
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
        _write_detail_sheet(df, writer, is_admin=is_admin)
        _write_summary_sheet(df, writer, is_admin=is_admin)
    output.seek(0)

    today_str = date.today().strftime('%Y%m%d')
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'出帳報表_{today_str}.xlsx'
    )


def _write_detail_sheet(df, writer, is_admin=False):
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


def _write_summary_sheet(df, writer, is_admin=False):
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
