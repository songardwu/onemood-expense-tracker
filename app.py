import os
from datetime import date
from io import BytesIO

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, send_file

load_dotenv('.env.local')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))


def get_conn():
    url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    return psycopg2.connect(url)


# ---------------------
# GET / — 清單頁
# ---------------------
@app.route('/')
def index():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, vendor, vendor_type, amount, category,
               invoice_no, invoice_date, remit_date, project_no, stage, created_at
        FROM reports
        ORDER BY invoice_date DESC, created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('list.html', reports=rows)


# ---------------------
# GET /new — 新增表單頁
# ---------------------
@app.route('/new')
def new_report():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT vendor FROM reports ORDER BY vendor")
    vendors = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT vendor_type FROM reports ORDER BY vendor_type")
    vendor_types = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template('new.html', vendors=vendors, vendor_types=vendor_types,
                           today=date.today().isoformat())


# ---------------------
# POST /submit — 寫入提報
# ---------------------
@app.route('/submit', methods=['POST'])
def submit():
    vendor = request.form.get('vendor', '').strip()
    vendor_type = request.form.get('vendor_type', '').strip()
    amount_str = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    invoice_no = request.form.get('invoice_no', '').strip() or None
    invoice_date = request.form.get('invoice_date', '').strip()
    remit_date = request.form.get('remit_date', '').strip() or None
    project_no = request.form.get('project_no', '').strip()
    stage = request.form.get('stage', '').strip() or None

    # 伺服器端驗證
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
                               form=request.form)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (vendor, vendor_type, amount, category,
                             invoice_no, invoice_date, remit_date, project_no, stage)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (vendor, vendor_type, amount_str, category,
          invoice_no, invoice_date, remit_date, project_no, stage))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# ---------------------
# POST /delete/<id> — 刪除提報
# ---------------------
@app.route('/delete/<int:report_id>', methods=['POST'])
def delete(report_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM reports WHERE id = %s", (report_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')


# ---------------------
# GET /export — 匯出 Excel
# ---------------------
@app.route('/export')
def export():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT invoice_date, vendor_type, vendor, project_no, stage,
               category, amount, invoice_no, remit_date
        FROM reports
        ORDER BY vendor_type, vendor, invoice_date
    """, conn)
    conn.close()

    if df.empty:
        return redirect('/')

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        write_detail_sheet(df, writer)
        write_summary_sheet(df, writer)
    output.seek(0)

    today_str = date.today().strftime('%Y%m%d')
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'出帳報表_{today_str}.xlsx'
    )


def write_detail_sheet(df, writer):
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

    # 按廠商分組，插入小計列
    for vendor, group in df.groupby('vendor', sort=False):
        for _, row in group.iterrows():
            rows.append(row.to_dict())
        rows.append({
            'vendor': f'【{vendor} 小計】',
            'amount': group['amount'].sum(),
        })

    # 按款項分類分計
    for cat, group in df.groupby('category'):
        rows.append({
            'category': f'【{cat} 分計】',
            'amount': group['amount'].sum(),
        })

    # 總計
    rows.append({
        'vendor': '【總計】',
        'amount': df['amount'].sum(),
    })

    result = pd.DataFrame(rows)
    # 按 col_map 的 key 順序排列欄位
    ordered_cols = [c for c in col_map.keys() if c in result.columns]
    result = result[ordered_cols]
    result.rename(columns=col_map, inplace=True)
    result.to_excel(writer, sheet_name='明細', index=False)


def write_summary_sheet(df, writer):
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


if __name__ == '__main__':
    app.run(debug=True)
