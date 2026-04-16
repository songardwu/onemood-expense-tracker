from datetime import date
from decimal import Decimal

from flask import Blueprint, abort, jsonify, redirect, render_template, request

from services.utils import (
    admin_required,
    check_project_access,
    get_conn,
    get_current_user,
    get_page_info,
    login_required,
    write_audit_log,
)

bp = Blueprint('projects', __name__)


def _generate_case_id(cur):
    """產生流水號 CASE-YYYYMMDD-NNN"""
    today_str = date.today().strftime('%Y%m%d')
    prefix = f'CASE-{today_str}-'
    cur.execute(
        "SELECT case_id FROM projects WHERE case_id LIKE %s ORDER BY case_id DESC LIMIT 1",
        (prefix + '%',)
    )
    row = cur.fetchone()
    if row:
        last_seq = int(row[0].split('-')[-1])
        return f'{prefix}{last_seq + 1:03d}'
    return f'{prefix}001'


def _get_project_summary(cur, project_id):
    """計算案場損益摘要"""
    cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        return None
    col_names = [desc[0] for desc in cur.description]
    p = dict(zip(col_names, row))

    original_contract = (p['system_furniture_amount'] or 0) + (p['non_system_furniture_amount'] or 0)

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM project_adjustments WHERE project_id = %s", (project_id,))
    net_adjustment = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM project_discounts WHERE project_id = %s", (project_id,))
    total_discount = cur.fetchone()[0]

    tax_amount = p['tax_amount'] or 0
    settlement_price = original_contract + net_adjustment + tax_amount - total_discount

    deposit_amount = p['deposit_amount'] or 0
    deposit_refund = p['deposit_refund'] or 0
    deposit_deduction = deposit_amount - deposit_refund

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM project_payments
        WHERE project_id = %s AND is_confirmed = TRUE
    """, (project_id,))
    total_received = cur.fetchone()[0]
    remaining_balance = settlement_price - total_received

    cur.execute("""
        SELECT COALESCE(SUM(pc.amount), 0) FROM project_costs pc
        JOIN cost_categories cc ON pc.category_id = cc.id
        WHERE pc.project_id = %s AND cc.cost_type = 'system'
    """, (project_id,))
    cost_system = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(pc.amount), 0) FROM project_costs pc
        JOIN cost_categories cc ON pc.category_id = cc.id
        WHERE pc.project_id = %s AND cc.cost_type = 'non_system'
    """, (project_id,))
    cost_non_system = cur.fetchone()[0]

    total_cost = cost_system + cost_non_system
    profit = (original_contract + net_adjustment + total_discount + deposit_deduction) - total_cost

    profit_share_pct = p['profit_share_pct'] or 0
    designer_bonus = profit * profit_share_pct / 100
    company_profit = profit - designer_bonus

    # 出帳差異
    disbursed_amount = None
    bonus_diff = None
    if p['bonus_disbursed'] and p['bonus_report_id']:
        cur.execute("SELECT amount FROM reports WHERE id = %s", (p['bonus_report_id'],))
        rpt = cur.fetchone()
        if rpt:
            disbursed_amount = rpt[0]
            bonus_diff = designer_bonus - Decimal(str(disbursed_amount))

    return {
        'original_contract': original_contract,
        'net_adjustment': net_adjustment,
        'tax_amount': tax_amount,
        'total_discount': total_discount,
        'settlement_price': settlement_price,
        'deposit_amount': deposit_amount,
        'deposit_refund': deposit_refund,
        'deposit_deduction': deposit_deduction,
        'total_received': total_received,
        'remaining_balance': remaining_balance,
        'cost_system': cost_system,
        'cost_non_system': cost_non_system,
        'total_cost': total_cost,
        'profit': profit,
        'profit_share_pct': profit_share_pct,
        'designer_bonus': designer_bonus,
        'company_profit': company_profit,
        'bonus_checked': p['bonus_checked'],
        'bonus_disbursed': p['bonus_disbursed'],
        'bonus_report_id': p['bonus_report_id'],
        'disbursed_amount': disbursed_amount,
        'bonus_diff': bonus_diff,
    }


# =====================================================
# Phase 1: 案場基本資料 CRUD
# =====================================================

@bp.route('/projects')
@login_required
def project_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    if user['role'] == 'admin':
        cur.execute("""
            SELECT p.id, p.case_id, p.case_name, p.owner_name, p.contract_date,
                   p.construction_start, p.construction_end, p.status,
                   u.display_name as designer_name,
                   p.system_furniture_amount, p.non_system_furniture_amount
            FROM projects p
            JOIN users u ON p.designer_id = u.id
            ORDER BY p.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT p.id, p.case_id, p.case_name, p.owner_name, p.contract_date,
                   p.construction_start, p.construction_end, p.status,
                   NULL as designer_name,
                   p.system_furniture_amount, p.non_system_furniture_amount
            FROM projects p
            WHERE p.designer_id = %s
            ORDER BY p.created_at DESC
        """, (user['id'],))

    all_projects = cur.fetchall()
    page, per_page, offset, total_pages = get_page_info(len(all_projects), per_page=50)
    projects = all_projects[offset:offset + per_page]
    cur.close()
    return render_template('projects.html', projects=projects, user=user,
                           page=page, total_pages=total_pages,
                           total_count=len(all_projects))


@bp.route('/projects/new')
@login_required
def new_project():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    designers = []
    if user['role'] == 'admin':
        cur.execute("SELECT id, display_name FROM users WHERE is_active = TRUE ORDER BY display_name")
        designers = cur.fetchall()
    cur.close()
    return render_template('project_form.html', user=user, project=None,
                           designers=designers, today=date.today().isoformat())


@bp.route('/projects/create', methods=['POST'])
@login_required
def create_project():
    user = get_current_user()
    case_name = request.form.get('case_name', '').strip()
    if not case_name:
        return redirect('/projects/new')

    owner_name = request.form.get('owner_name', '').strip()
    owner_phone = request.form.get('owner_phone', '').strip()
    owner_address = request.form.get('owner_address', '').strip()
    contract_date = request.form.get('contract_date', '').strip() or None
    construction_start = request.form.get('construction_start', '').strip() or None
    construction_end = request.form.get('construction_end', '').strip() or None

    if user['role'] == 'admin':
        designer_id = request.form.get('designer_id', '').strip()
        designer_id = int(designer_id) if designer_id else user['id']
    else:
        designer_id = user['id']

    conn = get_conn()
    cur = conn.cursor()
    case_id = _generate_case_id(cur)
    cur.execute("""
        INSERT INTO projects (case_id, case_name, owner_name, owner_phone,
                              owner_address, contract_date,
                              construction_start, construction_end, designer_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (case_id, case_name, owner_name, owner_phone, owner_address,
          contract_date, construction_start, construction_end, designer_id))
    project_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*, u.display_name as designer_name
        FROM projects p JOIN users u ON p.designer_id = u.id
        WHERE p.id = %s
    """, (project_id,))
    project = cur.fetchone()
    if not project:
        cur.close()
        abort(404)

    col_names = [desc[0] for desc in cur.description]
    proj = dict(zip(col_names, project))

    if user['role'] != 'admin' and proj['designer_id'] != user['id']:
        cur.close()
        abort(403)

    # 施工天數
    construction_days = None
    if proj['construction_start'] and proj['construction_end']:
        construction_days = (proj['construction_end'] - proj['construction_start']).days + 1

    # Phase 2: 追加減、折讓、收款
    cur.execute("SELECT id, adjust_date, description, amount FROM project_adjustments WHERE project_id = %s ORDER BY adjust_date, id", (project_id,))
    adjustments = cur.fetchall()

    cur.execute("SELECT id, item_name, amount FROM project_discounts WHERE project_id = %s ORDER BY id", (project_id,))
    discounts = cur.fetchall()

    cur.execute("""
        SELECT pp.id, pp.payment_date, pp.payment_method, pp.amount,
               pp.is_confirmed, u2.display_name as confirmed_by_name, pp.confirmed_at
        FROM project_payments pp
        LEFT JOIN users u2 ON pp.confirmed_by = u2.id
        WHERE pp.project_id = %s ORDER BY pp.payment_date, pp.id
    """, (project_id,))
    payments = cur.fetchall()

    # Phase 3: 成本科目
    cur.execute("""
        SELECT cc.id, cc.name, cc.cost_type, COALESCE(pc.amount, 0) as amount
        FROM cost_categories cc
        LEFT JOIN project_costs pc ON cc.id = pc.category_id AND pc.project_id = %s
        WHERE cc.is_active = TRUE
        ORDER BY cc.cost_type, cc.sort_order
    """, (project_id,))
    costs = cur.fetchall()

    # 損益摘要
    summary = _get_project_summary(cur, project_id)

    cur.close()
    return render_template('project_detail.html', project=proj, user=user,
                           construction_days=construction_days,
                           adjustments=adjustments, discounts=discounts,
                           payments=payments, costs=costs, summary=summary)


@bp.route('/projects/<int:project_id>/edit')
@login_required
def edit_project(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user, require_editable=True)
    if not proj:
        cur.close()
        abort(403)
    designers = []
    if user['role'] == 'admin':
        cur.execute("SELECT id, display_name FROM users WHERE is_active = TRUE ORDER BY display_name")
        designers = cur.fetchall()
    cur.close()
    return render_template('project_form.html', user=user, project=proj,
                           designers=designers, today=date.today().isoformat())


@bp.route('/projects/<int:project_id>/update', methods=['POST'])
@login_required
def update_project(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user, require_editable=True)
    if not proj:
        cur.close()
        abort(403)

    case_name = request.form.get('case_name', '').strip()
    if not case_name:
        cur.close()
        return redirect(f'/projects/{project_id}/edit')

    fields = {
        'case_name': case_name,
        'owner_name': request.form.get('owner_name', '').strip(),
        'owner_phone': request.form.get('owner_phone', '').strip(),
        'owner_address': request.form.get('owner_address', '').strip(),
        'contract_date': request.form.get('contract_date', '').strip() or None,
        'construction_start': request.form.get('construction_start', '').strip() or None,
        'construction_end': request.form.get('construction_end', '').strip() or None,
    }
    if user['role'] == 'admin':
        did = request.form.get('designer_id', '').strip()
        if did:
            fields['designer_id'] = int(did)

    set_clause = ', '.join(f"{k} = %s" for k in fields)
    cur.execute(f"UPDATE projects SET {set_clause}, updated_at = NOW() WHERE id = %s",
                list(fields.values()) + [project_id])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/status', methods=['POST'])
@login_required
def update_status(project_id):
    user = get_current_user()
    new_status = request.form.get('status', '').strip()
    reason = request.form.get('reason', '').strip()

    if new_status not in ('active', 'completed', 'closed'):
        return redirect(f'/projects/{project_id}')

    if new_status == 'closed' and user['role'] != 'admin':
        abort(403)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, designer_id FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    current_status, designer_id = row
    if current_status == 'closed' and user['role'] != 'admin':
        cur.close()
        abort(403)
    if user['role'] != 'admin' and designer_id != user['id']:
        cur.close()
        abort(403)

    cur.execute("UPDATE projects SET status = %s, updated_at = NOW() WHERE id = %s",
                (new_status, project_id))
    write_audit_log(cur, 'projects', project_id, 'status',
                    current_status, new_status, user['id'], reason or None)
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


# =====================================================
# Phase 2: 合約收入 / 收款 / 押金
# =====================================================

@bp.route('/projects/<int:project_id>/revenue', methods=['POST'])
@login_required
def update_revenue(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    fields = {
        'system_furniture_amount': request.form.get('system_furniture_amount', '0').strip(),
        'non_system_furniture_amount': request.form.get('non_system_furniture_amount', '0').strip(),
        'tax_amount': request.form.get('tax_amount', '0').strip(),
    }
    for k, v in fields.items():
        try:
            new_val = Decimal(v) if v else Decimal('0')
        except Exception:
            new_val = Decimal('0')
        old_val = proj.get(k) or 0
        if Decimal(str(old_val)) != new_val:
            write_audit_log(cur, 'projects', project_id, k, old_val, new_val, user['id'])
        fields[k] = new_val

    cur.execute("""
        UPDATE projects SET system_furniture_amount = %s, non_system_furniture_amount = %s,
               tax_amount = %s, updated_at = NOW() WHERE id = %s
    """, (fields['system_furniture_amount'], fields['non_system_furniture_amount'],
          fields['tax_amount'], project_id))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/deposit', methods=['POST'])
@login_required
def update_deposit(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    try:
        dep_amt = Decimal(request.form.get('deposit_amount', '0').strip() or '0')
        dep_ref = Decimal(request.form.get('deposit_refund', '0').strip() or '0')
    except Exception:
        dep_amt = Decimal('0')
        dep_ref = Decimal('0')

    # 自動判定狀態
    if dep_ref == 0 and dep_amt > 0:
        dep_status = 'pending'
    elif dep_ref < dep_amt:
        dep_status = 'partial'
    else:
        dep_status = 'refunded'

    for field, new_val in [('deposit_amount', dep_amt), ('deposit_refund', dep_ref), ('deposit_status', dep_status)]:
        old_val = proj.get(field)
        if str(old_val) != str(new_val):
            write_audit_log(cur, 'projects', project_id, field, old_val, new_val, user['id'])

    cur.execute("""
        UPDATE projects SET deposit_amount = %s, deposit_refund = %s,
               deposit_status = %s, updated_at = NOW() WHERE id = %s
    """, (dep_amt, dep_ref, dep_status, project_id))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


# --- 追加減明細 ---
@bp.route('/projects/<int:project_id>/adjustments/add', methods=['POST'])
@login_required
def add_adjustment(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    adjust_date = request.form.get('adjust_date', '').strip() or None
    description = request.form.get('description', '').strip()
    try:
        amount = Decimal(request.form.get('amount', '0').strip())
    except Exception:
        cur.close()
        return redirect(f'/projects/{project_id}')

    cur.execute("""
        INSERT INTO project_adjustments (project_id, adjust_date, description, amount)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, (project_id, adjust_date, description, amount))
    aid = cur.fetchone()[0]
    write_audit_log(cur, 'project_adjustments', aid, 'amount', None, amount, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/adjustments/<int:aid>/delete', methods=['POST'])
@login_required
def delete_adjustment(project_id, aid):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    cur.execute("SELECT amount FROM project_adjustments WHERE id = %s AND project_id = %s", (aid, project_id))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    write_audit_log(cur, 'project_adjustments', aid, 'amount', row[0], 'DELETED', user['id'])
    cur.execute("DELETE FROM project_adjustments WHERE id = %s", (aid,))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


# --- 折讓/扣抵明細 ---
@bp.route('/projects/<int:project_id>/discounts/add', methods=['POST'])
@login_required
def add_discount(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    item_name = request.form.get('item_name', '').strip()
    try:
        amount = Decimal(request.form.get('amount', '0').strip())
    except Exception:
        cur.close()
        return redirect(f'/projects/{project_id}')

    if not item_name:
        cur.close()
        return redirect(f'/projects/{project_id}')

    cur.execute("""
        INSERT INTO project_discounts (project_id, item_name, amount)
        VALUES (%s, %s, %s) RETURNING id
    """, (project_id, item_name, amount))
    did = cur.fetchone()[0]
    write_audit_log(cur, 'project_discounts', did, 'amount', None, amount, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/discounts/<int:did>/delete', methods=['POST'])
@login_required
def delete_discount(project_id, did):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    cur.execute("SELECT amount FROM project_discounts WHERE id = %s AND project_id = %s", (did, project_id))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    write_audit_log(cur, 'project_discounts', did, 'amount', row[0], 'DELETED', user['id'])
    cur.execute("DELETE FROM project_discounts WHERE id = %s", (did,))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


# --- 收款明細 ---
@bp.route('/projects/<int:project_id>/payments/add', methods=['POST'])
@login_required
def add_payment(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    payment_date = request.form.get('payment_date', '').strip()
    payment_method = request.form.get('payment_method', '').strip()
    try:
        amount = Decimal(request.form.get('amount', '0').strip())
    except Exception:
        cur.close()
        return redirect(f'/projects/{project_id}')

    if not payment_date or payment_method not in ('現金', '匯款', '其他'):
        cur.close()
        return redirect(f'/projects/{project_id}')

    cur.execute("""
        INSERT INTO project_payments (project_id, payment_date, payment_method, amount)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, (project_id, payment_date, payment_method, amount))
    pid = cur.fetchone()[0]
    write_audit_log(cur, 'project_payments', pid, 'amount', None, amount, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/payments/<int:pid>/delete', methods=['POST'])
@login_required
def delete_payment(project_id, pid):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    cur.execute("SELECT amount FROM project_payments WHERE id = %s AND project_id = %s", (pid, project_id))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    write_audit_log(cur, 'project_payments', pid, 'amount', row[0], 'DELETED', user['id'])
    cur.execute("DELETE FROM project_payments WHERE id = %s", (pid,))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/payments/<int:pid>/confirm', methods=['POST'])
@admin_required
def confirm_payment(project_id, pid):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT is_confirmed FROM project_payments WHERE id = %s AND project_id = %s", (pid, project_id))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    cur.execute("""
        UPDATE project_payments SET is_confirmed = TRUE,
               confirmed_by = %s, confirmed_at = NOW()
        WHERE id = %s
    """, (user['id'], pid))
    write_audit_log(cur, 'project_payments', pid, 'is_confirmed', False, True, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


# =====================================================
# Phase 3: 支出成本 + Dashboard API + 科目管理
# =====================================================

@bp.route('/projects/<int:project_id>/costs', methods=['POST'])
@login_required
def update_costs(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    proj = check_project_access(cur, project_id, user)
    if not proj:
        cur.close()
        abort(403)

    cur.execute("SELECT id FROM cost_categories WHERE is_active = TRUE")
    cat_ids = [r[0] for r in cur.fetchall()]

    try:
        for cat_id in cat_ids:
            try:
                new_amount = Decimal(request.form.get(f'cost_{cat_id}', '0').strip() or '0')
            except Exception:
                new_amount = Decimal('0')

            cur.execute("SELECT amount FROM project_costs WHERE project_id = %s AND category_id = %s",
                        (project_id, cat_id))
            existing = cur.fetchone()
            old_amount = existing[0] if existing else Decimal('0')

            if new_amount != old_amount:
                if existing:
                    cur.execute("UPDATE project_costs SET amount = %s WHERE project_id = %s AND category_id = %s",
                                (new_amount, project_id, cat_id))
                else:
                    cur.execute("INSERT INTO project_costs (project_id, category_id, amount) VALUES (%s, %s, %s)",
                                (project_id, cat_id, new_amount))
                write_audit_log(cur, 'project_costs', project_id, f'category_{cat_id}',
                                old_amount, new_amount, user['id'])
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/api/projects/<int:project_id>/summary')
@login_required
def api_project_summary(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT designer_id FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if user['role'] != 'admin' and row[0] != user['id']:
        cur.close()
        abort(403)

    summary = _get_project_summary(cur, project_id)
    cur.close()
    return jsonify(summary)


# --- 成本科目管理 ---
@bp.route('/cost-categories')
@admin_required
def cost_category_list():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, cost_type, sort_order, is_active FROM cost_categories ORDER BY cost_type, sort_order")
    categories = cur.fetchall()
    cur.close()
    return render_template('cost_categories.html', categories=categories, user=user)


@bp.route('/cost-categories/create', methods=['POST'])
@admin_required
def cost_category_create():
    name = request.form.get('name', '').strip()
    cost_type = request.form.get('cost_type', '').strip()
    if not name or cost_type not in ('system', 'non_system'):
        return redirect('/cost-categories')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM cost_categories WHERE cost_type = %s", (cost_type,))
    next_order = cur.fetchone()[0]
    cur.execute("INSERT INTO cost_categories (name, cost_type, sort_order) VALUES (%s, %s, %s)",
                (name, cost_type, next_order))
    conn.commit()
    cur.close()
    return redirect('/cost-categories')


@bp.route('/cost-categories/<int:cid>/update', methods=['POST'])
@admin_required
def cost_category_update(cid):
    name = request.form.get('name', '').strip()
    if not name:
        return redirect('/cost-categories')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE cost_categories SET name = %s WHERE id = %s", (name, cid))
    conn.commit()
    cur.close()
    return redirect('/cost-categories')


@bp.route('/cost-categories/<int:cid>/toggle', methods=['POST'])
@admin_required
def cost_category_toggle(cid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE cost_categories SET is_active = NOT is_active WHERE id = %s", (cid,))
    conn.commit()
    cur.close()
    return redirect('/cost-categories')


# =====================================================
# Phase 4: 分潤結算 + 獎金出帳 + Audit Log 查看
# =====================================================

@bp.route('/projects/<int:project_id>/settlement', methods=['POST'])
@admin_required
def update_settlement(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT profit_share_pct FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    try:
        new_pct = Decimal(request.form.get('profit_share_pct', '0').strip() or '0')
    except Exception:
        new_pct = Decimal('0')

    old_pct = row[0] or 0
    if Decimal(str(old_pct)) != new_pct:
        write_audit_log(cur, 'projects', project_id, 'profit_share_pct', old_pct, new_pct, user['id'])

    cur.execute("UPDATE projects SET profit_share_pct = %s, updated_at = NOW() WHERE id = %s",
                (new_pct, project_id))
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/bonus-check', methods=['POST'])
@admin_required
def bonus_check(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT bonus_checked FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)

    new_val = not row[0]
    cur.execute("UPDATE projects SET bonus_checked = %s, updated_at = NOW() WHERE id = %s",
                (new_val, project_id))
    write_audit_log(cur, 'projects', project_id, 'bonus_checked', row[0], new_val, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/bonus-disburse', methods=['POST'])
@admin_required
def bonus_disburse(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT bonus_checked, bonus_disbursed, designer_id FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if not row[0] or row[1]:  # 未核對 or 已出帳
        cur.close()
        return redirect(f'/projects/{project_id}')

    summary = _get_project_summary(cur, project_id)
    bonus_amount = summary['designer_bonus']

    # 取得設計師姓名
    cur.execute("SELECT display_name FROM users WHERE id = %s", (row[2],))
    designer_name = cur.fetchone()[0]

    # 取得案名
    cur.execute("SELECT case_name FROM projects WHERE id = %s", (project_id,))
    case_name = cur.fetchone()[0]

    # 建立報帳紀錄
    cur.execute("""
        INSERT INTO reports (vendor, vendor_type, amount, category,
                             invoice_date, project_no, payment_method, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (designer_name, 'designer_bonus', bonus_amount, '獎金',
          date.today().isoformat(), case_name, '公司轉帳', user['id']))
    report_id = cur.fetchone()[0]

    cur.execute("""
        UPDATE projects SET bonus_disbursed = TRUE, bonus_report_id = %s,
               updated_at = NOW() WHERE id = %s
    """, (report_id, project_id))
    write_audit_log(cur, 'projects', project_id, 'bonus_disbursed', False, True, user['id'])
    conn.commit()
    cur.close()
    return redirect(f'/projects/{project_id}')


@bp.route('/projects/<int:project_id>/logs')
@login_required
def project_logs(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT designer_id FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        abort(404)
    if user['role'] != 'admin' and row[0] != user['id']:
        cur.close()
        abort(403)

    cur.execute("""
        SELECT al.changed_at, u.display_name, al.table_name, al.field_name,
               al.old_value, al.new_value, al.reason
        FROM audit_logs al
        LEFT JOIN users u ON al.changed_by = u.id
        WHERE (al.table_name = 'projects' AND al.record_id = %s)
           OR (al.table_name IN ('project_adjustments', 'project_discounts',
                                  'project_payments', 'project_costs')
               AND al.record_id IN (
                   SELECT id FROM project_adjustments WHERE project_id = %s
                   UNION SELECT id FROM project_discounts WHERE project_id = %s
                   UNION SELECT id FROM project_payments WHERE project_id = %s
               ))
           OR (al.table_name = 'project_costs' AND al.record_id = %s)
        ORDER BY al.changed_at DESC
    """, (project_id, project_id, project_id, project_id, project_id))
    all_logs = cur.fetchall()
    page, per_page, offset, total_pages = get_page_info(len(all_logs), per_page=50)
    logs = all_logs[offset:offset + per_page]

    cur.execute("SELECT case_name FROM projects WHERE id = %s", (project_id,))
    case_name = cur.fetchone()[0]

    cur.close()
    return render_template('project_logs.html', logs=logs, user=user,
                           project_id=project_id, case_name=case_name,
                           page=page, total_pages=total_pages,
                           total_count=len(all_logs))
