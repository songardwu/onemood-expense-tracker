from datetime import date
from decimal import Decimal

from flask import Blueprint, abort, jsonify, redirect, render_template, request

from services.utils import (
    admin_required,
    get_conn,
    get_current_user,
    get_page_info,
    login_required,
    write_audit_log,
)

bp = Blueprint('invoices', __name__)

VALID_STATUSES = ('draft', 'issued', 'paid', 'void')

ALLOWED_TRANSITIONS = {
    'draft': ('issued', 'void'),
    'issued': ('paid', 'void'),
    'paid': ('void',),
    'void': (),
}


def _generate_invoice_no(cur):
    """產生請款單編號 INV-YYYYMM-NNN"""
    today = date.today()
    prefix = f'INV-{today.year}{today.month:02d}-'
    cur.execute(
        "SELECT invoice_no FROM invoices WHERE invoice_no LIKE %s ORDER BY invoice_no DESC LIMIT 1",
        (prefix + '%',)
    )
    row = cur.fetchone()
    if row:
        last_seq = int(row[0].split('-')[-1])
        return f'{prefix}{last_seq + 1:03d}'
    return f'{prefix}001'


def _d(val):
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _suggest_amount(cur, project_id):
    """建議請款金額 = settlement_price - total_received（已確認收款）"""
    cur.execute(
        "SELECT system_furniture_amount, non_system_furniture_amount, tax_amount FROM projects WHERE id = %s",
        (project_id,)
    )
    row = cur.fetchone()
    if not row:
        return Decimal('0')
    original_contract = _d(row[0]) + _d(row[1])
    tax_amount = _d(row[2])

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM project_adjustments WHERE project_id = %s", (project_id,))
    net_adjustment = _d(cur.fetchone()[0])

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM project_discounts WHERE project_id = %s", (project_id,))
    total_discount = _d(cur.fetchone()[0])

    settlement_price = original_contract + net_adjustment + tax_amount - total_discount

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM project_payments WHERE project_id = %s AND is_confirmed = TRUE",
        (project_id,)
    )
    total_received = _d(cur.fetchone()[0])

    remaining = settlement_price - total_received
    return remaining if remaining > 0 else Decimal('0')


def _user_can_view_invoice(cur, invoice_id, user):
    """設計師可看自己案場相關的請款單；admin 全看"""
    if user['role'] == 'admin':
        return True
    cur.execute("""
        SELECT EXISTS(
            SELECT 1 FROM invoice_lines il
            JOIN projects p ON il.project_id = p.id
            WHERE il.invoice_id = %s AND p.designer_id = %s
        )
    """, (invoice_id, user['id']))
    return cur.fetchone()[0]


def _parse_lines_from_form():
    """從表單解析多行 lines"""
    project_ids = request.form.getlist('line_project_id[]')
    descriptions = request.form.getlist('line_description[]')
    amounts = request.form.getlist('line_amount[]')
    suggested_amounts = request.form.getlist('line_suggested[]')

    lines = []
    total = Decimal('0')
    for i, pid in enumerate(project_ids):
        desc = descriptions[i].strip() if i < len(descriptions) else ''
        if not desc:
            continue
        try:
            amt = Decimal(amounts[i].strip() or '0') if i < len(amounts) else Decimal('0')
            sugg = Decimal(suggested_amounts[i].strip() or '0') if i < len(suggested_amounts) else Decimal('0')
        except Exception:
            continue
        pid_int = int(pid) if pid else None
        lines.append((pid_int, desc, sugg, amt))
        total += amt
    return lines, total


# =====================================================
# LIST
# =====================================================
@bp.route('/invoices')
@login_required
def invoice_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    period_year = request.args.get('year', type=int)
    period_month = request.args.get('month', type=int)
    status_filter = request.args.get('status', '').strip()

    where_parts = []
    params = []

    if period_year:
        where_parts.append("i.period_year = %s")
        params.append(period_year)
    if period_month:
        where_parts.append("i.period_month = %s")
        params.append(period_month)
    if status_filter in VALID_STATUSES:
        where_parts.append("i.status = %s")
        params.append(status_filter)

    if user['role'] != 'admin':
        where_parts.append("""
            EXISTS (
                SELECT 1 FROM invoice_lines il
                JOIN projects p ON il.project_id = p.id
                WHERE il.invoice_id = i.id AND p.designer_id = %s
            )
        """)
        params.append(user['id'])

    where_sql = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

    cur.execute(f"SELECT COUNT(*) FROM invoices i {where_sql}", params)
    total_count = cur.fetchone()[0]

    page, per_page, offset, total_pages = get_page_info(total_count, per_page=50)

    cur.execute(f"""
        SELECT i.id, i.invoice_no, i.client_name, i.period_year, i.period_month,
               i.total_amount, i.status, i.issued_at, i.created_at,
               u.display_name as issued_by_name,
               (SELECT COUNT(*) FROM invoice_lines WHERE invoice_id = i.id) as line_count
        FROM invoices i
        LEFT JOIN users u ON i.issued_by = u.id
        {where_sql}
        ORDER BY i.period_year DESC, i.period_month DESC, i.id DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    invoices = cur.fetchall()

    cur.close()
    return render_template('invoices.html', invoices=invoices, user=user,
                           page=page, total_pages=total_pages, total_count=total_count,
                           filters={'year': period_year, 'month': period_month, 'status': status_filter})


# =====================================================
# NEW (form)
# =====================================================
@bp.route('/invoices/new')
@admin_required
def new_invoice():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.case_id, p.case_name, p.owner_name, u.display_name as designer_name
        FROM projects p
        JOIN users u ON p.designer_id = u.id
        WHERE p.status != 'closed'
        ORDER BY p.created_at DESC
    """)
    projects = cur.fetchall()

    today = date.today()
    cur.close()
    return render_template('invoice_form.html', user=user, invoice=None, lines=[],
                           projects=projects,
                           form_year=today.year, form_month=today.month,
                           error=request.args.get('error'))


# =====================================================
# CREATE
# =====================================================
@bp.route('/invoices/create', methods=['POST'])
@admin_required
def create_invoice():
    user = get_current_user()
    client_name = request.form.get('client_name', '').strip()
    client_address = request.form.get('client_address', '').strip()
    period_year_str = request.form.get('period_year', '').strip()
    period_month_str = request.form.get('period_month', '').strip()
    notes = request.form.get('notes', '').strip()

    if not client_name or not period_year_str or not period_month_str:
        return redirect('/invoices/new?error=missing')

    try:
        period_year = int(period_year_str)
        period_month = int(period_month_str)
        if not (1 <= period_month <= 12):
            raise ValueError
        if not (2020 <= period_year <= 2099):
            raise ValueError
    except ValueError:
        return redirect('/invoices/new?error=invalid_period')

    lines, total = _parse_lines_from_form()
    if not lines:
        return redirect('/invoices/new?error=no_lines')

    conn = get_conn()
    cur = conn.cursor()
    try:
        invoice_no = _generate_invoice_no(cur)
        cur.execute("""
            INSERT INTO invoices (invoice_no, client_name, client_address,
                                  period_year, period_month, total_amount,
                                  status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s)
            RETURNING id
        """, (invoice_no, client_name, client_address, period_year, period_month,
              total, notes))
        invoice_id = cur.fetchone()[0]

        for sort_order, (pid, desc, sugg, amt) in enumerate(lines):
            cur.execute("""
                INSERT INTO invoice_lines (invoice_id, project_id, description,
                                           suggested_amount, amount, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (invoice_id, pid, desc, sugg, amt, sort_order))

        write_audit_log(cur, 'invoices', invoice_id, 'created', None, invoice_no, user['id'])
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    cur.close()
    return redirect(f'/invoices/{invoice_id}')


# =====================================================
# DETAIL
# =====================================================
@bp.route('/invoices/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    if not _user_can_view_invoice(cur, invoice_id, user):
        cur.close()
        abort(403)

    cur.execute("""
        SELECT i.*, u.display_name as issued_by_name
        FROM invoices i
        LEFT JOIN users u ON i.issued_by = u.id
        WHERE i.id = %s
    """, (invoice_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    col_names = [desc[0] for desc in cur.description]
    invoice = dict(zip(col_names, row))

    cur.execute("""
        SELECT il.id, il.project_id, p.case_id, p.case_name, il.description,
               il.suggested_amount, il.amount, il.sort_order
        FROM invoice_lines il
        LEFT JOIN projects p ON il.project_id = p.id
        WHERE il.invoice_id = %s
        ORDER BY il.sort_order, il.id
    """, (invoice_id,))
    lines = cur.fetchall()

    cur.execute("""
        SELECT pp.id, p.case_id, p.case_name, pp.payment_date,
               pp.payment_method, pp.amount, pp.is_confirmed
        FROM project_payments pp
        JOIN projects p ON pp.project_id = p.id
        WHERE pp.invoice_id = %s
        ORDER BY pp.payment_date DESC, pp.id DESC
    """, (invoice_id,))
    linked_payments = cur.fetchall()

    cur.close()
    return render_template('invoice_detail.html', invoice=invoice, lines=lines,
                           linked_payments=linked_payments, user=user,
                           allowed_transitions=ALLOWED_TRANSITIONS.get(invoice['status'], ()),
                           error=request.args.get('error'))


# =====================================================
# EDIT (form, draft only)
# =====================================================
@bp.route('/invoices/<int:invoice_id>/edit')
@admin_required
def edit_invoice(invoice_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM invoices WHERE id = %s", (invoice_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    col_names = [desc[0] for desc in cur.description]
    invoice = dict(zip(col_names, row))

    if invoice['status'] != 'draft':
        cur.close()
        return redirect(f'/invoices/{invoice_id}?error=not_editable')

    cur.execute("""
        SELECT il.id, il.project_id, p.case_id, p.case_name, il.description,
               il.suggested_amount, il.amount
        FROM invoice_lines il
        LEFT JOIN projects p ON il.project_id = p.id
        WHERE il.invoice_id = %s
        ORDER BY il.sort_order, il.id
    """, (invoice_id,))
    lines = cur.fetchall()

    cur.execute("""
        SELECT p.id, p.case_id, p.case_name, p.owner_name, u.display_name as designer_name
        FROM projects p
        JOIN users u ON p.designer_id = u.id
        WHERE p.status != 'closed'
        ORDER BY p.created_at DESC
    """)
    projects = cur.fetchall()

    cur.close()
    return render_template('invoice_form.html', user=user, invoice=invoice, lines=lines,
                           projects=projects,
                           form_year=invoice['period_year'],
                           form_month=invoice['period_month'],
                           error=request.args.get('error'))


# =====================================================
# UPDATE (admin, draft only)
# =====================================================
@bp.route('/invoices/<int:invoice_id>/update', methods=['POST'])
@admin_required
def update_invoice(invoice_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status FROM invoices WHERE id = %s", (invoice_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if row[0] != 'draft':
        cur.close()
        return redirect(f'/invoices/{invoice_id}?error=not_editable')

    client_name = request.form.get('client_name', '').strip()
    client_address = request.form.get('client_address', '').strip()
    notes = request.form.get('notes', '').strip()

    if not client_name:
        cur.close()
        return redirect(f'/invoices/{invoice_id}/edit?error=missing')

    lines, total = _parse_lines_from_form()
    if not lines:
        cur.close()
        return redirect(f'/invoices/{invoice_id}/edit?error=no_lines')

    try:
        cur.execute("DELETE FROM invoice_lines WHERE invoice_id = %s", (invoice_id,))
        for sort_order, (pid, desc, sugg, amt) in enumerate(lines):
            cur.execute("""
                INSERT INTO invoice_lines (invoice_id, project_id, description,
                                           suggested_amount, amount, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (invoice_id, pid, desc, sugg, amt, sort_order))

        cur.execute("""
            UPDATE invoices SET client_name = %s, client_address = %s,
                                notes = %s, total_amount = %s, updated_at = NOW()
            WHERE id = %s
        """, (client_name, client_address, notes, total, invoice_id))

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    cur.close()
    return redirect(f'/invoices/{invoice_id}')


# =====================================================
# STATUS TRANSITION (admin)
# =====================================================
@bp.route('/invoices/<int:invoice_id>/status', methods=['POST'])
@admin_required
def change_status(invoice_id):
    user = get_current_user()
    new_status = request.form.get('status', '').strip()

    if new_status not in VALID_STATUSES:
        return redirect(f'/invoices/{invoice_id}')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status FROM invoices WHERE id = %s", (invoice_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    current_status = row[0]
    if new_status not in ALLOWED_TRANSITIONS.get(current_status, ()):
        cur.close()
        return redirect(f'/invoices/{invoice_id}?error=invalid_transition')

    if new_status == 'issued':
        cur.execute("""
            UPDATE invoices SET status = %s, issued_by = %s, issued_at = NOW(), updated_at = NOW()
            WHERE id = %s
        """, (new_status, user['id'], invoice_id))
    else:
        cur.execute("UPDATE invoices SET status = %s, updated_at = NOW() WHERE id = %s",
                    (new_status, invoice_id))

    write_audit_log(cur, 'invoices', invoice_id, 'status', current_status, new_status, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/invoices/{invoice_id}')


# =====================================================
# DELETE (admin, draft only)
# =====================================================
@bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@admin_required
def delete_invoice(invoice_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, invoice_no FROM invoices WHERE id = %s", (invoice_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if row[0] != 'draft':
        cur.close()
        return redirect(f'/invoices/{invoice_id}?error=not_deletable')

    write_audit_log(cur, 'invoices', invoice_id, 'deleted', row[1], 'DELETED', user['id'])
    cur.execute("DELETE FROM invoices WHERE id = %s", (invoice_id,))
    conn.commit()
    cur.close()
    return redirect('/invoices')


# =====================================================
# API: 取單一案場建議金額（form 動態填入）
# =====================================================
@bp.route('/api/invoice-suggest/<int:project_id>')
@admin_required
def api_suggest(project_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT case_id, case_name FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'not_found'}), 404
    amount = _suggest_amount(cur, project_id)
    cur.close()
    return jsonify({
        'project_id': project_id,
        'case_id': row[0],
        'case_name': row[1],
        'description': f'{row[0]} {row[1]}',
        'suggested_amount': float(amount),
    })
