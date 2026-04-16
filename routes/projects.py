from datetime import date
from flask import Blueprint, abort, redirect, render_template, request

from services.utils import admin_required, get_conn, get_current_user, login_required

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


# =====================
# GET /projects — 案場列表
# =====================
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

    projects = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('projects.html', projects=projects, user=user)


# =====================
# GET /projects/new — 新增案場表單
# =====================
@bp.route('/projects/new')
@login_required
def new_project():
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    designers = []
    if user['role'] == 'admin':
        cur.execute("""
            SELECT id, display_name FROM users
            WHERE is_active = TRUE ORDER BY display_name
        """)
        designers = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('project_form.html', user=user, project=None,
                           designers=designers, today=date.today().isoformat())


# =====================
# POST /projects/create — 建立案場
# =====================
@bp.route('/projects/create', methods=['POST'])
@login_required
def create_project():
    user = get_current_user()
    case_name = request.form.get('case_name', '').strip()
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

    if not case_name:
        return redirect('/projects/new')

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
    conn.close()
    return redirect(f'/projects/{project_id}')


# =====================
# GET /projects/<id> — 案場詳情
# =====================
@bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*, u.display_name as designer_name
        FROM projects p
        JOIN users u ON p.designer_id = u.id
        WHERE p.id = %s
    """, (project_id,))
    project = cur.fetchone()

    if not project:
        cur.close(); conn.close()
        abort(404)

    # 權限檢查：設計師只能看自己的案場
    col_names = [desc[0] for desc in cur.description]
    proj = dict(zip(col_names, project))

    if user['role'] != 'admin' and proj['designer_id'] != user['id']:
        cur.close(); conn.close()
        abort(403)

    # 計算施工天數
    construction_days = None
    if proj['construction_start'] and proj['construction_end']:
        delta = proj['construction_end'] - proj['construction_start']
        construction_days = delta.days + 1

    cur.close()
    conn.close()
    return render_template('project_detail.html', project=proj, user=user,
                           construction_days=construction_days)


# =====================
# GET /projects/<id>/edit — 編輯案場表單
# =====================
@bp.route('/projects/<int:project_id>/edit')
@login_required
def edit_project(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    project = cur.fetchone()
    if not project:
        cur.close(); conn.close()
        abort(404)

    col_names = [desc[0] for desc in cur.description]
    proj = dict(zip(col_names, project))

    # 權限：設計師只能編輯自己的、且未結案的
    if user['role'] != 'admin' and proj['designer_id'] != user['id']:
        cur.close(); conn.close()
        abort(403)
    if proj['status'] == 'closed' and user['role'] != 'admin':
        cur.close(); conn.close()
        abort(403)

    designers = []
    if user['role'] == 'admin':
        cur.execute("""
            SELECT id, display_name FROM users
            WHERE is_active = TRUE ORDER BY display_name
        """)
        designers = cur.fetchall()

    cur.close()
    conn.close()
    return render_template('project_form.html', user=user, project=proj,
                           designers=designers, today=date.today().isoformat())


# =====================
# POST /projects/<id>/update — 更新案場
# =====================
@bp.route('/projects/<int:project_id>/update', methods=['POST'])
@login_required
def update_project(project_id):
    user = get_current_user()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT designer_id, status FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)

    # 權限檢查
    if user['role'] != 'admin' and row[0] != user['id']:
        cur.close(); conn.close()
        abort(403)
    if row[1] == 'closed' and user['role'] != 'admin':
        cur.close(); conn.close()
        abort(403)

    case_name = request.form.get('case_name', '').strip()
    owner_name = request.form.get('owner_name', '').strip()
    owner_phone = request.form.get('owner_phone', '').strip()
    owner_address = request.form.get('owner_address', '').strip()
    contract_date = request.form.get('contract_date', '').strip() or None
    construction_start = request.form.get('construction_start', '').strip() or None
    construction_end = request.form.get('construction_end', '').strip() or None

    if not case_name:
        cur.close(); conn.close()
        return redirect(f'/projects/{project_id}/edit')

    update_fields = {
        'case_name': case_name,
        'owner_name': owner_name,
        'owner_phone': owner_phone,
        'owner_address': owner_address,
        'contract_date': contract_date,
        'construction_start': construction_start,
        'construction_end': construction_end,
    }

    if user['role'] == 'admin':
        designer_id = request.form.get('designer_id', '').strip()
        if designer_id:
            update_fields['designer_id'] = int(designer_id)

    set_clause = ', '.join(f"{k} = %s" for k in update_fields)
    values = list(update_fields.values())
    values.append(project_id)

    cur.execute(
        f"UPDATE projects SET {set_clause}, updated_at = NOW() WHERE id = %s",
        values
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(f'/projects/{project_id}')


# =====================
# POST /projects/<id>/status — 變更案場狀態
# =====================
@bp.route('/projects/<int:project_id>/status', methods=['POST'])
@login_required
def update_status(project_id):
    user = get_current_user()
    new_status = request.form.get('status', '').strip()

    if new_status not in ('active', 'completed', 'closed'):
        return redirect(f'/projects/{project_id}')

    # 只有管理者可以結案/解鎖
    if new_status == 'closed' and user['role'] != 'admin':
        abort(403)
    # 從結案改回其他狀態也只有管理者可以
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status, designer_id FROM projects WHERE id = %s", (project_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        abort(404)

    current_status = row[0]
    if current_status == 'closed' and user['role'] != 'admin':
        cur.close(); conn.close()
        abort(403)
    if user['role'] != 'admin' and row[1] != user['id']:
        cur.close(); conn.close()
        abort(403)

    cur.execute(
        "UPDATE projects SET status = %s, updated_at = NOW() WHERE id = %s",
        (new_status, project_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return redirect(f'/projects/{project_id}')
