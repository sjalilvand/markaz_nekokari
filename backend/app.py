# -*- coding: utf-8 -*-
"""
سامانه داشبورد جامع مراکز نیکوکاری و توانمندسازی
Backend: Flask + SQLite  |  Frontend: React (سرو از همین سرور)
"""
import io
import json
import os
import sys
import time

from flask import Flask, Response, g, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import constants as C
import narrative
from api_ext import bp as ext_bp
from apicache import cached, bump as cache_bump
from db import DB_PATH, connect, ensure_schema, get_meta, set_meta
from norm import norm

SERVER_VERSION = '2.4.0'  # برای تشخیص نسخه در حال اجرا در /api/health و /api/meta

BASE = os.path.dirname(os.path.abspath(__file__))
FRONT_DIST = os.path.join(os.path.dirname(BASE), 'frontend', 'dist')
UPLOAD_DIR = os.path.join(BASE, 'data', 'uploads')

app = Flask(__name__, static_folder=None)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024 * 1024
app.register_blueprint(ext_bp)

MONTHS_J = C.MONTHS_J

# ── فشرده‌سازی gzip پاسخ‌های بزرگ (JSON داشبوردها تا ۸۵KB → حدود ۱۰KB روی سیم) ──
_COMPRESS_TYPES = {'application/json', 'text/html', 'text/csv', 'text/plain', 'text/css',
                   'application/javascript', 'image/svg+xml'}


@app.after_request
def _gzip_response(resp):
    """اگر کلاینت gzip بپذیرد و پاسخ به‌اندازهٔ کافی بزرگ باشد، فشرده شود."""
    if (resp.status_code not in (200, 404)
            or resp.direct_passthrough
            or (resp.headers.get('Content-Encoding') or '')):
        return resp
    if (resp.headers.get('Content-Type') or '').split(';')[0].strip() not in _COMPRESS_TYPES:
        return resp
    accept = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept.lower():
        return resp
    try:
        raw = resp.get_data()
        if len(raw) < 1024:
            return resp
        import gzip as _gzip
        packed = _gzip.compress(raw, compresslevel=5)
        if len(packed) >= len(raw):
            return resp
        resp.set_data(packed)
        resp.headers['Content-Encoding'] = 'gzip'
        resp.headers['Content-Length'] = str(len(packed))
        resp.headers['Vary'] = 'Accept-Encoding'
    except Exception:  # noqa — در بدترین حالت پاسخ فشرده‌نشده می‌رود
        pass
    return resp


def get_db():
    if 'db' not in g:
        g.db = connect()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def F(args):
    """استخراج و اعتبارسنجی فیلترها — هر مقدار غیرعددی (جز 'all') نادیده گرفته می‌شود
    تا هیچ endpoint هرگز به‌خاطر پارامتر بد، 500 ندهد و از SQL injection هم محفوظ بماند"""

    def _id(v):
        v = (v or 'all').strip()
        if v in ('', 'all'):
            return 'all'
        try:
            return str(int(v))
        except ValueError:
            return 'all'

    year = (args.get('year') or 'all').strip()
    if year not in ('', 'all'):
        try:
            year = str(int(year))
        except ValueError:
            year = 'all'
    return {
        'year': year,
        'province': _id(args.get('province')),
        'office': _id(args.get('office')),
        'center': _id(args.get('center')),
    }


def f_conds(f, alias='t', with_year=True, with_office=True, with_center=True):
    conds, params = [], []
    if with_year and f['year'] != 'all':
        conds.append(f'{alias}.year = ?')
        params.append(int(f['year']))
    if f['province'] != 'all':
        conds.append(f'{alias}.province_id = ?')
        params.append(int(f['province']))
    if with_office and f['office'] != 'all':
        if alias == 'c':  # خود جدول مراکز ستون office_id دارد
            conds.append(f'{alias}.office_id = ?')
        else:  # بقیه جدول‌ها با زیرپرس از مراکز فیلتر می‌شوند (transactions، requests، needy، members، ...)
            conds.append(f'{alias}.center_id IN (SELECT id FROM centers WHERE office_id = ?)')
        params.append(int(f['office']))
    if with_center and f['center'] != 'all' and f['center']:
        conds.append(f'{alias}.center_id = ?')
        params.append(int(f['center']))
    return conds, params


def where(f, alias='t', **kw):
    conds, params = f_conds(f, alias, **kw)
    return ('WHERE ' + ' AND '.join(conds)) if conds else '', params


def rows_as_dicts(cur):
    return [dict(r) for r in cur.fetchall()]


# ───────────────────────────── meta ─────────────────────────────

@app.route('/api/meta')
@cached()
def api_meta():
    db = get_db()
    provs = rows_as_dicts(db.execute('SELECT id, name FROM provinces ORDER BY name'))
    offs = rows_as_dicts(db.execute(
        'SELECT o.id, o.province_id, o.name FROM offices o ORDER BY o.name'))
    years = [r['year'] for r in db.execute(
        'SELECT DISTINCT year FROM transactions WHERE year IS NOT NULL ORDER BY year')]
    if not years:
        years = [1403, 1404, 1405]
    totals = {
        'centers': db.execute('SELECT COUNT(*) n FROM centers').fetchone()['n'],
        'members_active': db.execute('SELECT SUM(total_active) s FROM centers').fetchone()['s'] or 0,
        'members_inactive': db.execute('SELECT SUM(total_inactive) s FROM centers').fetchone()['s'] or 0,
        'needy': db.execute('SELECT COUNT(*) n FROM needy').fetchone()['n'],
        'hamyaran': db.execute('SELECT COUNT(*) n FROM hamyaran').fetchone()['n'],
        'requests': db.execute('SELECT COUNT(*) n FROM requests').fetchone()['n'],
        'transactions': db.execute('SELECT COUNT(*) n FROM transactions').fetchone()['n'],
        'payments_all': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='پرداخت'").fetchone()['s'] or 0,
        'receipts_all': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='دریافت'").fetchone()['s'] or 0,
    }
    return jsonify({
        'server_version': SERVER_VERSION,
        'provinces': provs, 'offices': offs, 'years': years, 'months': MONTHS_J,
        'request_types': [r['request_type'] for r in db.execute(
            'SELECT DISTINCT request_type FROM requests WHERE request_type IS NOT NULL')],
        'need_types': list(C.NEEDY_TYPE_DIST.keys()),
        'need_groups': list(C.NEEDY_GROUP_DIST.keys()),
        'networks': [n for n, _ in C.NETWORKS],
        'medals': ['پلاتین', 'طلا', 'نقره', 'برنز', 'نیازمند بهبود'],
        'data_mode': get_meta(db, 'data_mode', 'demo'),
        'generated_at': get_meta(db, 'generated_at'),
        'imported_at': get_meta(db, 'imported_at'),
        'totals': totals,
    })


# ─────────────────────────── overview ───────────────────────────

@app.route('/api/overview')
@cached()
def api_overview():
    db = get_db()
    f = F(request.args)
    W, P = where(f, 't', with_year=True)
    Wp, Pp = where(f, 'r', with_year=True, with_office=False)

    def one(sql, params=()):
        r = db.execute(sql, params).fetchone()
        return r['s'] if r and r['s'] is not None else 0

    # بهینه‌سازی: همهٔ اسکالرها در «یک» اسکن جدول تراکنش‌ها (به‌جای ۴ اسکن کامل)
    row = db.execute(
        'SELECT '
        " SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) payments,"
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) receipts,"
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='نقدی' THEN t.amount ELSE 0 END) pay_cash,"
        " SUM(CASE WHEN t.flow='پرداخت' THEN 1 ELSE 0 END) pay_count"
        f' FROM transactions t {W}', P).fetchone()
    payments = row['payments'] or 0
    receipts = row['receipts'] or 0
    pay_cash = row['pay_cash'] or 0
    pay_count = row['pay_count'] or 0
    requests = one(f"SELECT COUNT(*) s FROM requests r {Wp}", Pp)

    # سری ماهانه ۱۴۰۳-۰۱ تا ۱۴۰۵-۰۸ (برای اسپارک‌لاین و نمودار روند)
    Wm, Pm = where(f, 't', with_year=False)
    mnull = 't.year IS NOT NULL AND t.month IS NOT NULL'
    Mcond = (Wm + ' AND ' + mnull) if Wm else ('WHERE ' + mnull)
    ycond = (Wm + ' AND t.year IS NOT NULL') if Wm else 'WHERE t.year IS NOT NULL'
    monthly = rows_as_dicts(db.execute(
        'SELECT t.year y, t.month m, '
        " SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) payments, "
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) receipts, "
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='نقدی' THEN t.amount ELSE 0 END) cash, "
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='غیرنقدی' THEN t.amount ELSE 0 END) inkind "
        f'FROM transactions t {Mcond} GROUP BY t.year, t.month ORDER BY t.year, t.month', Pm))

    # مقایسه سالانه برای دلتاها
    yearly = {r['y']: r for r in rows_as_dicts(db.execute(
        "SELECT t.year y, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) payments,"
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) receipts"
        f' FROM transactions t {ycond} GROUP BY t.year', Pm))}
    years_sorted = sorted(y for y in yearly.keys() if y is not None)
    cur_year = int(f['year']) if f['year'] != 'all' else (years_sorted[-1] if years_sorted else None)
    prev_year = years_sorted[years_sorted.index(cur_year) - 1] if cur_year in years_sorted and years_sorted.index(cur_year) > 0 else None

    # وقتی فیلتر «همه سال‌ها» است، دلتا بر اساس سال جاری محاسبه شود نه کل دوره
    # مقایسه هم‌دوره‌ای: سال جاری (ناقص) با ماه‌های مشابه سال قبل
    def year_sum(year, key, m_max=None):
        return sum((r[key] or 0) for r in monthly if r['y'] == year and (m_max is None or r['m'] <= m_max))

    cur_max_m = max((r['m'] for r in monthly if r['y'] == cur_year), default=None)
    if f['year'] != 'all':
        cur_pay_cmp = payments          # فیلترشده به همان سال (کل سال)
        cur_rec_cmp = receipts
        prev_pay = year_sum(prev_year, 'payments') if prev_year else None
        prev_rec = year_sum(prev_year, 'receipts') if prev_year else None
    else:
        cur_pay_cmp = year_sum(cur_year, 'payments')
        cur_rec_cmp = year_sum(cur_year, 'receipts')
        prev_pay = year_sum(prev_year, 'payments', m_max=cur_max_m) if prev_year else None
        prev_rec = year_sum(prev_year, 'receipts', m_max=cur_max_m) if prev_year else None

    def delta(cur, prev):
        if prev in (0, None) or cur is None:
            return None
        return round((cur - prev) / prev * 100, 1)

    kpis = [
        {'key': 'payments', 'label': 'جمع پرداخت‌ها', 'value': payments, 'unit': 'rial',
         'delta': delta(cur_pay_cmp, prev_pay),
         'note': f'در {fmt(pay_count)} تراکنش'},
        {'key': 'receipts', 'label': 'جمع دریافت‌ها', 'value': receipts, 'unit': 'rial',
         'delta': delta(cur_rec_cmp, prev_rec)},
        {'key': 'balance', 'label': 'مانده باقی‌مانده', 'value': receipts - payments, 'unit': 'rial'},
        {'key': 'requests', 'label': 'درخواست‌های ثبت‌شده', 'value': requests, 'unit': 'count'},
        {'key': 'centers', 'label': 'مراکز فعال', 'value': db.execute(
            "SELECT COUNT(*) s FROM centers c WHERE c.status='فعال'" +
            (' AND c.province_id=' + str(f['province']) if f['province'] != 'all' else '')).fetchone()['s'],
         'unit': 'count'},
        {'key': 'members', 'label': 'اعضای فعال شبکه', 'value': db.execute(
            'SELECT SUM(c.total_active) s FROM centers c' +
            (' WHERE c.province_id=' + str(f['province']) if f['province'] != 'all' else '')).fetchone()['s'] or 0,
         'unit': 'count'},
        {'key': 'needy', 'label': 'نیازمندان ثبت‌شده', 'value': db.execute(
            'SELECT COUNT(*) s FROM needy n' +
            (' WHERE n.province_id=' + str(f['province']) if f['province'] != 'all' else '')).fetchone()['s'],
         'unit': 'count'},
        {'key': 'hamyaran', 'label': 'همیاران', 'value': db.execute(
            'SELECT COUNT(*) s FROM hamyaran h' +
            (' WHERE h.province_id=' + str(f['province']) if f['province'] != 'all' else '')).fetchone()['s'],
         'unit': 'count'},
    ]

    top_prov = rows_as_dicts(db.execute(
        "SELECT p.id, p.name, SUM(t.amount) s FROM transactions t JOIN provinces p ON p.id=t.province_id "
        + (W + " AND t.flow='پرداخت'" if W else "WHERE t.flow='پرداخت'") +
        ' GROUP BY p.id, p.name ORDER BY s DESC LIMIT 10', P))
    req_cats = rows_as_dicts(db.execute(
        f'SELECT r.category label, COUNT(*) s FROM requests r {Wp} GROUP BY r.category', Pp))
    top_centers = rows_as_dicts(db.execute(
        "SELECT c.id, c.name, p.name prov, c.medal, c.score, SUM(t.amount) s "
        'FROM transactions t JOIN centers c ON c.id=t.center_id JOIN provinces p ON p.id=c.province_id '
        + (W + " AND t.flow='پرداخت' AND t.center_id IS NOT NULL" if W else "WHERE t.flow='پرداخت' AND t.center_id IS NOT NULL") +
        ' GROUP BY c.id ORDER BY s DESC LIMIT 10', P))
    insights = narrative.build_insights(db, f)[:5]

    return jsonify({
        'kpis': kpis, 'monthly': monthly, 'yearly': yearly, 'cur_year': cur_year,
        'prev_year': prev_year,
        'pay_by_method': [
            {'label': 'نقدی', 'value': pay_cash},
            {'label': 'غیرنقدی', 'value': payments - pay_cash}],
        'req_categories': req_cats, 'top_provinces': top_prov, 'top_centers': top_centers,
        'insights': insights,
    })


def fmt(n):
    try:
        return f'{n:,.0f}'
    except (TypeError, ValueError):
        return str(n)


# ───────────────────────── demographics ─────────────────────────

@app.route('/api/demographics')
@cached()
def api_demographics():
    db = get_db()
    f = F(request.args)
    conds, params = [], []
    if f['province'] != 'all':
        conds.append('province_id = ?')
        params.append(int(f['province']))
    W = ('WHERE ' + ' AND '.join(conds)) if conds else ''

    # بهینه‌سازی: هیستوگرام سن در «یک» اسکن با CASE (به‌جای ۱۰ کوئری جداگانه)
    age_sql = db.execute(
        f'''SELECT
          SUM(CASE WHEN age BETWEEN 0 AND 10 THEN 1 ELSE 0 END) b0,
          SUM(CASE WHEN age BETWEEN 11 AND 20 THEN 1 ELSE 0 END) b1,
          SUM(CASE WHEN age BETWEEN 21 AND 30 THEN 1 ELSE 0 END) b2,
          SUM(CASE WHEN age BETWEEN 31 AND 40 THEN 1 ELSE 0 END) b3,
          SUM(CASE WHEN age BETWEEN 41 AND 50 THEN 1 ELSE 0 END) b4,
          SUM(CASE WHEN age BETWEEN 51 AND 60 THEN 1 ELSE 0 END) b5,
          SUM(CASE WHEN age BETWEEN 61 AND 70 THEN 1 ELSE 0 END) b6,
          SUM(CASE WHEN age BETWEEN 71 AND 80 THEN 1 ELSE 0 END) b7,
          SUM(CASE WHEN age BETWEEN 81 AND 90 THEN 1 ELSE 0 END) b8,
          SUM(CASE WHEN age > 90 THEN 1 ELSE 0 END) b9
        FROM needy {W}''', params).fetchone()
    age_hist = [
        {'label': '۰-۱۰', 'value': age_sql['b0'] or 0}, {'label': '۱۱-۲۰', 'value': age_sql['b1'] or 0},
        {'label': '۲۱-۳۰', 'value': age_sql['b2'] or 0}, {'label': '۳۱-۴۰', 'value': age_sql['b3'] or 0},
        {'label': '۴۱-۵۰', 'value': age_sql['b4'] or 0}, {'label': '۵۱-۶۰', 'value': age_sql['b5'] or 0},
        {'label': '۶۱-۷۰', 'value': age_sql['b6'] or 0}, {'label': '۷۱-۸۰', 'value': age_sql['b7'] or 0},
        {'label': '۸۱-۹۰', 'value': age_sql['b8'] or 0}, {'label': '۹۱+', 'value': age_sql['b9'] or 0},
    ]
    stats = db.execute(f'SELECT AVG(age) mean FROM needy {W}', params).fetchone()

    # بهینه‌سازی: جنسیت + میانگین سن هر جنسیت در یک کوئری؛ دهک + میانگین سن هر دهک در یک کوئری
    gender_rows = rows_as_dicts(db.execute(
        f"SELECT gender label, COUNT(*) n, AVG(age) avg_age FROM needy {W + ' AND' if W else 'WHERE'} gender IS NOT NULL GROUP BY gender", params))
    gender = [{'label': r['label'], 'n': r['n']} for r in gender_rows]
    age_gender = [{'gender': r['label'], 'avg_age': r['avg_age'], 'n': r['n']} for r in gender_rows]
    need_types = rows_as_dicts(db.execute(
        f"SELECT need_type label, COUNT(*) n FROM needy {W + ' AND' if W else 'WHERE'} need_type IS NOT NULL GROUP BY need_type ORDER BY n DESC", params))
    need_groups = rows_as_dicts(db.execute(
        f"SELECT need_group label, COUNT(*) n FROM needy {W + ' AND' if W else 'WHERE'} need_group IS NOT NULL GROUP BY need_group ORDER BY n DESC LIMIT 12", params))
    vital = rows_as_dicts(db.execute(
        f"SELECT vital label, COUNT(*) n FROM needy {W + ' AND' if W else 'WHERE'} vital IS NOT NULL GROUP BY vital", params))
    offices = rows_as_dicts(db.execute(
        f'SELECT office label, COUNT(*) n FROM needy {W + " AND office IS NOT NULL" if W else "WHERE office IS NOT NULL"} GROUP BY office ORDER BY n DESC LIMIT 10', params))
    # دهک × سن (هیتمپ ساده) — در همان اسکن گروه‌بندی دهک
    dec_rows = rows_as_dicts(db.execute(
        f"SELECT decile d, COUNT(*) n, AVG(age) avg_age FROM needy {W + ' AND' if W else 'WHERE'} decile IS NOT NULL GROUP BY decile ORDER BY decile", params))
    decile = [{'d': r['d'], 'n': r['n']} for r in dec_rows]
    dec_age = [{'d': r['d'], 'avg_age': r['avg_age'], 'n': r['n']} for r in dec_rows]
    return jsonify({'age_hist': age_hist, 'age_stats': {'mean': round(stats['mean'] or 0, 1)},
                    'decile': decile, 'gender': gender, 'need_types': need_types,
                    'need_groups': need_groups, 'vital': vital, 'top_offices': offices,
                    'age_gender': age_gender, 'dec_age': dec_age})


# ─────────────────────────── payments ───────────────────────────

@app.route('/api/payments/trend')
@cached()
def api_trend():
    db = get_db()
    f = F(request.args)
    flow = request.args.get('flow', 'پرداخت')
    W, P = where(f, 't', with_year=False)
    nd = ' AND t.year IS NOT NULL AND t.month IS NOT NULL '
    sql = ('SELECT t.year y, t.month m, SUM(t.amount) amount, COUNT(*) cnt, '
           "SUM(CASE WHEN t.method='نقدی' THEN t.amount ELSE 0 END) cash, "
           "SUM(CASE WHEN t.method='غیرنقدی' THEN t.amount ELSE 0 END) inkind "
           f'FROM transactions t ' + (W + nd + ' AND t.flow = ? ' if W else 'WHERE t.flow = ? ' + nd) +
           'GROUP BY t.year, t.month ORDER BY t.year, t.month')
    series = [r for r in rows_as_dicts(db.execute(sql, P + [flow]))
              if r['y'] is not None and r['m'] is not None]
    # میانگین متحرک ۳ ماهه
    for i, r in enumerate(series):
        try:
            r['label'] = f'{int(r["y"])}/{int(r["m"]):02d}'
        except (TypeError, ValueError):
            r['label'] = str(r['y'])
        if i >= 2:
            r['ma3'] = round(sum(s['amount'] for s in series[i - 2:i + 1]) / 3, 0)
    annual = rows_as_dicts(db.execute(
        'SELECT t.year y, '
        " SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) payments,"
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) receipts, "
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='نقدی' THEN t.amount ELSE 0 END) cash,"
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='غیرنقدی' THEN t.amount ELSE 0 END) inkind, "
        ' COUNT(*) cnt FROM transactions t WHERE t.year IS NOT NULL GROUP BY t.year ORDER BY t.year'))
    return jsonify({'series': series, 'annual': annual})


@app.route('/api/payments/compare')
@cached()
def api_compare():
    db = get_db()
    by_year = rows_as_dicts(db.execute(
        "SELECT year y, SUM(CASE WHEN flow='پرداخت' THEN amount ELSE 0 END) payments,"
        " SUM(CASE WHEN flow='دریافت' THEN amount ELSE 0 END) receipts,"
        " SUM(CASE WHEN flow='پرداخت' AND method='نقدی' THEN amount ELSE 0 END) cash,"
        " SUM(CASE WHEN flow='پرداخت' AND method='غیرنقدی' THEN amount ELSE 0 END) inkind"
        ' FROM transactions WHERE year IS NOT NULL GROUP BY year ORDER BY year'))
    prev = None
    for r in by_year:
        r['growth'] = round((r['payments'] - prev) / prev * 100, 1) if prev else None
        prev = r['payments']
    matrix = rows_as_dicts(db.execute(
        'SELECT p.name, t.year y, SUM(t.amount) amount FROM transactions t '
        'JOIN provinces p ON p.id=t.province_id WHERE t.flow=? AND t.year IS NOT NULL GROUP BY p.id, t.year', ('پرداخت',)))
    provs = {}
    for r in matrix:
        provs.setdefault(r['name'], {})[str(r['y'])] = r['amount']
    years = [str(r['y']) for r in by_year]
    rows = [{'province': k, **{y: v.get(y, 0) for y in years}} for k, v in provs.items()]
    rows.sort(key=lambda r: -sum(r[y] for y in years))
    return jsonify({'by_year': by_year, 'years': years, 'province_matrix': rows[:12]})


@app.route('/api/payments/categories')
@cached()
def api_categories():
    db = get_db()
    f = F(request.args)
    W, P = where(f, 't', with_year=True)
    cats = rows_as_dicts(db.execute(
        'SELECT t.category label, t.method, SUM(t.amount) s, COUNT(*) cnt FROM transactions t '
        + (W + " AND t.category IS NOT NULL" if W else "WHERE t.category IS NOT NULL") +
        ' GROUP BY t.category, t.method ORDER BY s DESC LIMIT 25', P))
    sources = rows_as_dicts(db.execute(
        'SELECT t.source label, SUM(t.amount) s FROM transactions t '
        + (W + " AND t.source IS NOT NULL" if W else "WHERE t.source IS NOT NULL") +
        ' GROUP BY t.source ORDER BY s DESC', P))
    coverage = rows_as_dicts(db.execute(
        'SELECT t.coverage label, COUNT(*) s FROM transactions t '
        + (W + " AND t.coverage IS NOT NULL" if W else "WHERE t.coverage IS NOT NULL") +
        ' GROUP BY t.coverage ORDER BY s DESC', P))
    return jsonify({'categories': cats, 'sources': sources, 'coverage': coverage})


# ─────────────────────────── provinces ──────────────────────────

@app.route('/api/provinces')
@cached()
def api_provinces():
    db = get_db()
    f = F(request.args)
    # تجمیع‌های سنگین یک‌بار به‌صورت GROUP BY انجام می‌شوند (چند برابر سریع‌تر از زیرپرس همبسته)
    year = f['year']
    tx_ycond = (' WHERE year = ' + str(int(year))) if year != 'all' else ''
    tx_agg = {r['pid']: r for r in rows_as_dicts(db.execute(
        'SELECT province_id pid, '
        "SUM(CASE WHEN flow='پرداخت' THEN amount ELSE 0 END) payments, "
        "SUM(CASE WHEN flow='دریافت' THEN amount ELSE 0 END) receipts "
        f'FROM transactions{tx_ycond} GROUP BY province_id'))}
    req_ycond = (' WHERE year = ' + str(int(year))) if year != 'all' else ''
    req_agg = {r['pid']: r['n'] for r in rows_as_dicts(db.execute(
        f'SELECT province_id pid, COUNT(*) n FROM requests{req_ycond} GROUP BY province_id'))}
    prov_filter = ''
    prov_param = []
    if f['province'] != 'all':
        prov_filter = ' WHERE p.id = ?'
        prov_param = [int(f['province'])]
    rows = rows_as_dicts(db.execute(
        'SELECT p.id, p.name,'
        ' (SELECT COUNT(*) FROM centers c WHERE c.province_id=p.id) centers,'
        ' (SELECT COALESCE(SUM(c.total_active),0) FROM centers c WHERE c.province_id=p.id) members,'
        ' (SELECT COUNT(*) FROM needy n WHERE n.province_id=p.id) needy,'
        ' (SELECT COUNT(*) FROM hamyaran h WHERE h.province_id=p.id) hamyaran,'
        ' (SELECT AVG(c.score) FROM centers c WHERE c.province_id=p.id) avg_score'
        f' FROM provinces p{prov_filter} ORDER BY p.name', prov_param))
    total_pay = sum((tx_agg.get(r['id'], {}).get('payments') or 0) for r in rows)
    for r in rows:
        t = tx_agg.get(r['id']) or {}
        r['payments'] = t.get('payments') or 0
        r['receipts'] = t.get('receipts') or 0
        r['requests'] = req_agg.get(r['id'], 0)
        r['balance'] = r['receipts'] - r['payments']
        r['pay_per_center'] = r['payments'] / r['centers'] if r['centers'] else 0
        r['needy_per_center'] = r['needy'] / r['centers'] if r['centers'] else 0
        r['pay_per_needy'] = r['payments'] / r['needy'] if r['needy'] else 0
        r['hamyaran_per_1000'] = r['hamyaran'] / r['needy'] * 1000 if r['needy'] else 0
        r['share'] = r['payments'] / total_pay * 100 if total_pay else 0
        sc = r['avg_score'] or 0
        r['medal'] = ('پلاتین' if sc >= 90 else 'طلا' if sc >= 80 else
                      'نقره' if sc >= 70 else 'برنز' if sc >= 60 else 'نیازمند بهبود')
    return jsonify({'rows': rows, 'total_payments': total_pay})


# ─────────────────────────── centers ────────────────────────────

@app.route('/api/centers')
@cached()
def api_centers():
    db = get_db()
    f = F(request.args)
    page = max(1, int(request.args.get('page', 1)))
    per = min(100, max(5, int(request.args.get('per', 20))))
    search = norm(request.args.get('search', ''))
    medal = request.args.get('medal', 'all')
    sort = request.args.get('sort', 'score')
    d = 'DESC' if request.args.get('dir', 'desc') == 'desc' else 'ASC'
    conds, params = [], []
    if f['province'] != 'all':
        conds.append('c.province_id = ?')
        params.append(int(f['province']))
    if f['office'] != 'all':
        conds.append('c.office_id = ?')
        params.append(int(f['office']))
    if medal != 'all':
        conds.append('c.medal = ?')
        params.append(medal)
    if search:
        conds.append('(c.name LIKE ? OR c.license_no LIKE ?)')
        params += [f'%{search}%', f'%{search}%']
    W = ('WHERE ' + ' AND '.join(conds)) if conds else ''
    sort_map = {'score': 'c.score', 'payments': 'pay', 'members': 'c.total_active',
                'name': 'c.name', 'inactive': 'c.total_inactive'}
    order = f'{sort_map.get(sort, "c.score")} {d}, c.score DESC'
    total = db.execute(f'SELECT COUNT(*) n FROM centers c {W}', params).fetchone()['n']
    rows = rows_as_dicts(db.execute(
        'SELECT c.id, c.name, c.license_no, p.name prov, o.name office, c.status,'
        ' c.chair, c.vice, c.exec_mgr, c.finance, c.members, c.inspector, c.alt_inspector,'
        ' c.total_active, c.total_inactive, c.center_type, c.urban_rural, c.ownership,'
        ' c.score, c.medal,'
        ' COALESCE((SELECT SUM(t.amount) FROM transactions t WHERE t.center_id=c.id AND t.flow="پرداخت"),0) pay,'
        ' COALESCE((SELECT COUNT(*) FROM needy n WHERE n.center_id=c.id),0) needy_cnt,'
        ' (SELECT COUNT(*) FROM members m WHERE m.center_id=c.id AND m.status="فعال") member_rows'
        f' FROM centers c JOIN provinces p ON p.id=c.province_id LEFT JOIN offices o ON o.id=c.office_id'
        f' {W} ORDER BY {order} LIMIT ? OFFSET ?', params + [per, (page - 1) * per]))
    return jsonify({'rows': rows, 'total': total, 'page': page, 'per': per})


@app.route('/api/centers/summary')
@cached()
def api_centers_summary():
    db = get_db()
    f = F(request.args)
    prov_f = ' AND c.province_id = ' + str(int(f['province'])) if f['province'] != 'all' else ''
    medal_dist = rows_as_dicts(db.execute(
        f'SELECT c.medal label, COUNT(*) n FROM centers c WHERE 1=1{prov_f} GROUP BY c.medal'))
    roles = rows_as_dicts(db.execute(
        f'''SELECT
          ROUND(100.0*SUM(CASE WHEN c.chair>0 THEN 1 ELSE 0 END)/COUNT(*),1) chair,
          ROUND(100.0*SUM(CASE WHEN c.vice>0 THEN 1 ELSE 0 END)/COUNT(*),1) vice,
          ROUND(100.0*SUM(CASE WHEN c.exec_mgr>0 THEN 1 ELSE 0 END)/COUNT(*),1) exec_mgr,
          ROUND(100.0*SUM(CASE WHEN c.finance>0 THEN 1 ELSE 0 END)/COUNT(*),1) finance,
          ROUND(100.0*SUM(CASE WHEN c.members>0 THEN 1 ELSE 0 END)/COUNT(*),1) members,
          ROUND(100.0*SUM(CASE WHEN c.inspector>0 THEN 1 ELSE 0 END)/COUNT(*),1) inspector,
          ROUND(100.0*SUM(CASE WHEN c.alt_inspector>0 THEN 1 ELSE 0 END)/COUNT(*),1) alt_inspector,
          COUNT(*) n FROM centers c WHERE 1=1{prov_f}'''))[0]
    comp_hist = rows_as_dicts(db.execute(
        f'SELECT c.total_active x, COUNT(*) n FROM centers c WHERE 1=1{prov_f} GROUP BY x ORDER BY x'))
    scatter = rows_as_dicts(db.execute(
        'SELECT c.total_active x, ROUND(SUM(t.amount)/1e9,1) y, c.medal, c.name'
        ' FROM centers c JOIN transactions t ON t.center_id=c.id AND t.flow="پرداخت"'
        f' WHERE 1=1{prov_f} GROUP BY c.id ORDER BY SUM(t.amount) DESC LIMIT 600'))
    top = rows_as_dicts(db.execute(
        f'SELECT c.id, c.name, p.name prov, c.score, c.medal, c.total_active FROM centers c '
        f'JOIN provinces p ON p.id=c.province_id WHERE 1=1{prov_f} ORDER BY c.score DESC LIMIT 10'))
    bottom = rows_as_dicts(db.execute(
        f'SELECT c.id, c.name, p.name prov, c.score, c.medal, c.total_active FROM centers c '
        f'JOIN provinces p ON p.id=c.province_id WHERE 1=1{prov_f} ORDER BY c.score ASC LIMIT 10'))
    radar = rows_as_dicts(db.execute(
        '''SELECT p.name,
          ROUND(AVG((c.exec_mgr + c.finance + c.inspector)/3.0)*100,1) structure,
          ROUND(AVG(MIN(c.total_active,7)/7.0)*100,1) capacity,
          ROUND(100 - 100.0*SUM(c.total_inactive)/MAX(SUM(c.total_active+c.total_inactive),1),1) quality,
          ROUND(AVG(c.score),1) score
        FROM centers c JOIN provinces p ON p.id=c.province_id
        WHERE p.name IN (SELECT pname FROM (SELECT p2.name pname, AVG(c2.score) s2 FROM centers c2
          JOIN provinces p2 ON p2.id=c2.province_id GROUP BY p2.name ORDER BY s2 DESC LIMIT 5))
        GROUP BY p.name'''))
    return jsonify({'medal_dist': medal_dist, 'roles': roles, 'completeness_hist': comp_hist,
                    'scatter': scatter, 'top': top, 'bottom': bottom, 'radar': radar})


# ─────────────────────────── KPIs ───────────────────────────────

@app.route('/api/kpis')
@cached()
def api_kpis():
    db = get_db()
    f = F(request.args)
    W, P = where(f, 't', with_year=True)
    yr = int(f['year']) if f['year'] != 'all' else None

    def one(sql, params=()):
        r = db.execute(sql, params).fetchone()
        return (r['s'] if r and r['s'] is not None else 0)

    centers = one('SELECT COUNT(*) s FROM centers c' + (' WHERE c.province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    needy = one('SELECT COUNT(*) s FROM needy n' + (' WHERE n.province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    hamyaran = one('SELECT COUNT(*) s FROM hamyaran h' + (' WHERE h.province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    # بهینه‌سازی: سه اسکن تراکنش‌ها در یک اسکن واحد
    r0 = db.execute(
        'SELECT '
        " SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay_all,"
        " SUM(CASE WHEN t.flow='پرداخت' AND t.method='نقدی' THEN t.amount ELSE 0 END) pay_cash,"
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) receipts"
        f' FROM transactions t {W}', P).fetchone()
    pay_all = r0['pay_all'] or 0
    pay_cash = r0['pay_cash'] or 0
    receipts = r0['receipts'] or 0
    reqs = one('SELECT COUNT(*) s FROM requests r' +
               (f' WHERE r.year={yr}' if yr else '') +
               ((' AND ' if yr else ' WHERE ') + f'r.province_id = {int(f["province"])}' if f['province'] != 'all' else ''))
    req_nat = one("SELECT COUNT(*) s FROM requests r WHERE r.national_id IS NOT NULL AND r.national_id != ''" +
                  (f" AND r.year={yr}" if yr else "") +
                  (' AND r.province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    members_act = one('SELECT SUM(c.total_active) s FROM centers c' + (' WHERE c.province_id=' + str(f['province']) if f['province'] != 'all' else ''))

    # سهم ۵ استان برتر
    top5 = one("SELECT SUM(s) s FROM (SELECT SUM(t.amount) s FROM transactions t " +
               (W + " AND t.flow='پرداخت'" if W else "WHERE t.flow='پرداخت'") +
               " GROUP BY t.province_id ORDER BY s DESC LIMIT 5)", P)

    # بهینه‌سازی: پرداخت سالانه + حداکثر ماه هر سال در یک اسکن
    _yrow = db.execute(
        "SELECT year y, SUM(CASE WHEN flow='پرداخت' THEN amount ELSE 0 END) s, MAX(month) m "
        'FROM transactions WHERE year IS NOT NULL GROUP BY year')
    yearly_pay = {}
    ym = {}
    for r in _yrow:
        yearly_pay[r['y']] = r['s']
        ym[r['y']] = r['m']
    ys = sorted(y for y in yearly_pay.keys() if y is not None)
    last_y = ys[-1] if ys else None
    max_m = ym.get(last_y) if last_y else None

    def ytd_sum(year, m_max=None):
        sql = 'SELECT SUM(amount) s FROM transactions WHERE flow=? AND year=?'
        params = ['پرداخت', year]
        if m_max is not None:
            sql += ' AND month<=?'
            params.append(m_max)
        r = db.execute(sql, params).fetchone()
        return r['s'] or 0

    growth = None
    if yr and (yr - 1) in yearly_pay and yearly_pay[yr - 1]:
        growth = round((yearly_pay[yr] - yearly_pay[yr - 1]) / yearly_pay[yr - 1] * 100, 1)
    elif len(ys) >= 2 and yearly_pay[ys[0]]:
        cur_v = ytd_sum(last_y, max_m)
        prev_v = ytd_sum(ys[-2], max_m)
        if prev_v:
            growth = round((cur_v - prev_v) / prev_v * 100, 1)

    d12 = one('SELECT COUNT(*) s FROM needy WHERE decile IN (1,2)' + (' AND province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    dtot = one('SELECT COUNT(*) s FROM needy WHERE decile IS NOT NULL' + (' AND province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    no_exec = one('SELECT COUNT(*) s FROM centers WHERE exec_mgr=0' + (' AND province_id=' + str(f['province']) if f['province'] != 'all' else ''))
    anom = one('SELECT COUNT(*) s FROM anomalies')

    def kpi(key, label, value, unit, target, direction='up', desc='', fmt_kind='num'):
        att = None
        if target:
            att = round(value / target * 100, 1) if direction == 'up' else round(target / max(value, 1e-9) * 100, 1)
        status = 'ok' if (att is not None and att >= 100) else ('warn' if att and att >= 80 else 'bad')
        return {'key': key, 'label': label, 'value': value, 'unit': unit, 'target': target,
                'attainment': att, 'direction': direction, 'desc': desc, 'status': status,
                'fmt': fmt_kind, 'spark': [yearly_pay.get(y, 0) for y in ys] if key == 'payments' else None}

    kpis = [
        kpi('self_sufficiency', 'نسبت دریافت به پرداخت', round(receipts / max(pay_all, 1) * 100, 1),
            'percent', 150, 'up', 'پایداری مالی شبکه مردمی', 'pct'),
        kpi('cash_share', 'سهم پرداخت نقدی', round(pay_cash / max(pay_all, 1) * 100, 1),
            'percent', 40, 'down', 'کنترل ترکیب روش پرداخت', 'pct'),
        kpi('avg_members', 'میانگین اعضای فعال هر مرکز', round(members_act / max(centers, 1), 2),
            'count', 7, 'up', 'ظرفیت ساختاری هیات امنا'),
        kpi('exec_rate', 'پوشش مدیر اجرایی', round((centers - no_exec) / max(centers, 1) * 100, 1),
            'percent', 80, 'up', f'{fmt(no_exec)} مرکز بدون مدیر اجرایی', 'pct'),
        kpi('hamyaran_ratio', 'همیار به ازای هزار نیازمند', round(hamyaran / max(needy, 1) * 1000, 1),
            'count', 4, 'up', 'پوشش شبکه همیاران'),
        kpi('deep_poverty', 'تمرکز دهک ۱-۲', round(d12 / max(dtot, 1) * 100, 1),
            'percent', 75, 'up', 'هدف‌گیری فقر شدید', 'pct'),
        kpi('nat_id', 'تکمیل کدملی در درخواست‌ها', round(req_nat / max(reqs, 1) * 100, 1),
            'percent', 95, 'up', 'کیفیت داده مددجویی', 'pct'),
        kpi('growth', 'رشد پرداخت‌ها (سالانه)', growth or 0, 'percent', 15, 'up',
            'مقایسه با سال گذشته', 'pct'),
        kpi('top5_share', 'تمرکز جغرافیایی ۵ استان برتر', round(top5 / max(pay_all, 1) * 100, 1),
            'percent', 45, 'down', 'توازن توزیع جغرافیایی', 'pct'),
        kpi('anomalies', 'تراکنش‌های ثبت‌نشده شناسایی‌شده', anom, 'count', 0, 'down',
            'اسناد بدون تراکنش بانکی'),
        kpi('needy_per_center', 'نیازمند به ازای هر مرکز', round(needy / max(centers, 1), 1),
            'count', 90, 'down', 'بار پوشش هر مرکز'),
    ]
    return jsonify({'kpis': kpis})


# ───────────────────── records / pivot / export ─────────────────

DATASETS = {
    'transactions': {
        'table': 'transactions t LEFT JOIN centers c ON c.id=t.center_id LEFT JOIN provinces p ON p.id=t.province_id',
        'select': ('t.id, t.tracking_no, t.date_j, p.name province, c.name center, t.flow, t.method, '
                   't.category, t.source, t.amount, t.beneficiaries, t.coverage, t.year, t.month'),
        'cols': [
            ('tracking_no', 'شماره رهگیری'), ('date_j', 'تاریخ'), ('province', 'استان'),
            ('center', 'مرکز'), ('flow', 'نوع'), ('method', 'روش'), ('category', 'فعالیت'),
            ('source', 'منبع'), ('amount', 'مبلغ (ریال)'), ('beneficiaries', 'تعداد ذی‌نفع'),
            ('coverage', 'وضعیت تحت پوشش')],
        'sort': 't.amount',
    },
    'requests': {
        'table': 'requests r LEFT JOIN centers c ON c.id=r.center_id LEFT JOIN provinces p ON p.id=r.province_id',
        'select': ('r.id, r.tracking_no, r.date_j, p.name province, c.name center, r.request_type, '
                   'r.category, r.national_id, r.status, r.process_status, r.amount, r.year, r.month'),
        'cols': [
            ('tracking_no', 'شماره پیگیری'), ('date_j', 'تاریخ'), ('province', 'استان'),
            ('center', 'مرکز'), ('request_type', 'نوع درخواست'), ('category', 'دسته'),
            ('national_id', 'کدملی'), ('status', 'وضعیت درخواست'),
            ('process_status', 'وضعیت فرآیندی'), ('amount', 'مبلغ (ریال)')],
        'sort': 'r.date_j',
    },
    'needy': {
        'table': 'needy n LEFT JOIN centers c ON c.id=n.center_id LEFT JOIN provinces p ON p.id=n.province_id',
        'select': ('n.id, n.national_id, n.name, n.family, n.gender, n.birth, n.age, p.name province, '
                   'n.office, c.name center, n.need_type, n.need_group, n.vital, n.decile'),
        'cols': [
            ('national_id', 'کدملی'), ('name', 'نام'), ('family', 'نام خانوادگی'),
            ('gender', 'جنسیت'), ('birth', 'تاریخ تولد'), ('age', 'سن'), ('province', 'استان'),
            ('office', 'اداره'), ('center', 'مرکز'), ('need_type', 'نوع نیازمند'),
            ('need_group', 'گروه نیازمندی'), ('vital', 'وضعیت حیات'), ('decile', 'دهک')],
        'sort': 'n.id',
    },
    'members': {
        'table': 'members m LEFT JOIN centers c ON c.id=m.center_id LEFT JOIN provinces p ON p.id=c.province_id',
        'select': ('m.id, m.national_id, m.name, m.family, m.gender, m.role, m.status, p.name province, '
                   'c.name center, m.age, m.education, m.job, m.bank_debt, m.tax_debt, m.alive'),
        'cols': [
            ('national_id', 'کدملی'), ('name', 'نام'), ('family', 'نام خانوادگی'),
            ('gender', 'جنسیت'), ('role', 'مسئولیت'), ('status', 'وضعیت عضو'),
            ('province', 'استان'), ('center', 'مرکز'), ('age', 'سن'),
            ('education', 'تحصیلات'), ('job', 'شغل'), ('bank_debt', 'بدهکار بانکی'),
            ('tax_debt', 'بدهکار مالیاتی'), ('alive', 'قید حیات')],
        'sort': 'm.id',
    },
    'anomalies': {
        'table': 'anomalies a LEFT JOIN provinces p ON p.id=a.province_id',
        'select': 'a.id, p.name province, a.doc_no, a.date_j, a.title, a.descr, a.flow, a.amount',
        'cols': [
            ('province', 'استان'), ('doc_no', 'شماره سند'), ('date_j', 'تاریخ'),
            ('title', 'عنوان'), ('descr', 'شرح'), ('flow', 'نوع'), ('amount', 'مبلغ (ریال)')],
        'sort': 'a.id',
    },
}


@app.route('/api/records')
@cached()   # صفحه‌بندی/جست‌وجو/مرتب‌سازی در query string است ← کلید کش جدا و صحیح
def api_records():
    db = get_db()
    ds = request.args.get('dataset', 'transactions')
    if ds not in DATASETS:
        return jsonify({'error': 'dataset نامعتبر'}), 400
    d = DATASETS[ds]
    f = F(request.args)
    alias = d['table'].split()[0].split('.')[0] if False else {'transactions': 't', 'requests': 'r',
                                                               'needy': 'n', 'members': 'm', 'anomalies': 'a'}[ds]
    conds, params = [], []
    if ds in ('transactions', 'requests'):
        cy, cp = f_conds(f, alias, with_year=True, with_office=False)
        conds += cy
        params += cp
    elif ds == 'anomalies':
        pass
    else:
        if f['province'] != 'all':
            conds.append(f'{alias}.province_id = ?' if ds != 'members' else 'c.province_id = ?')
            params.append(int(f['province']))
    search = norm(request.args.get('search', ''))
    if search and ds in ('transactions', 'requests'):
        conds.append('(t.tracking_no LIKE ? OR c.name LIKE ?)' if ds == 'transactions'
                     else '(r.tracking_no LIKE ? OR c.name LIKE ? OR r.national_id LIKE ?)')
        params += [f'%{search}%'] * (2 if ds == 'transactions' else 3)
    elif search and ds == 'needy':
        conds.append('(n.name LIKE ? OR n.family LIKE ? OR n.national_id LIKE ?)')
        params += [f'%{search}%'] * 3
    elif search and ds == 'members':
        conds.append('(m.name LIKE ? OR m.family LIKE ? OR m.national_id LIKE ? OR c.name LIKE ?)')
        params += [f'%{search}%'] * 4
    W = ('WHERE ' + ' AND '.join(conds)) if conds else ''
    page = max(1, int(request.args.get('page', 1)))
    per = min(200, max(5, int(request.args.get('per', 15))))
    sort_col = request.args.get('sort', '')
    allowed = {c[0] for c in d['cols']}
    order = (sort_col if sort_col in allowed else d['sort'].split('.')[-1])
    dir_ = 'DESC' if request.args.get('dir', 'desc') == 'desc' else 'ASC'
    total = db.execute(f'SELECT COUNT(*) n FROM {d["table"]} {W}', params).fetchone()['n']
    rows = rows_as_dicts(db.execute(
        f'SELECT {d["select"]} FROM {d["table"]} {W} ORDER BY {order} {dir_} LIMIT ? OFFSET ?',
        params + [per, (page - 1) * per]))
    agg = db.execute(f'SELECT SUM(amount) s, COUNT(*) n FROM {d["table"]} {W}',
                     params).fetchone() if 'amount' in d['select'] else None
    return jsonify({'rows': rows, 'total': total, 'page': page, 'per': per,
                    'cols': d['cols'], 'sum_amount': agg['s'] if agg else None})


@app.route('/api/pivot')
@cached()
def api_pivot():
    db = get_db()
    f = F(request.args)
    row_dim = request.args.get('row', 'province')
    col_dim = request.args.get('col', 'year')
    metric = request.args.get('metric', 'amount')
    W, P = where(f, 't', with_year=(col_dim != 'year'))
    row_sql = {'province': 'p.name', 'category': 't.category', 'source': 't.source',
               'method': 't.method', 'flow': 't.flow'}.get(row_dim, 'p.name')
    col_sql = {'year': 't.year', 'month': 't.month', 'method': 't.method', 'flow': 't.flow'}.get(col_dim, 't.year')
    met_sql = 'SUM(t.amount)' if metric == 'amount' else 'COUNT(*)'
    null_cond = ''
    if col_dim in ('year', 'month'):
        null_cond = f' AND {col_sql} IS NOT NULL'
    sql = (f'SELECT {row_sql} rlabel, {col_sql} clabel, {met_sql} val FROM transactions t '
           'LEFT JOIN provinces p ON p.id=t.province_id '
           + (W + ' AND t.category IS NOT NULL' + null_cond if W else 'WHERE t.category IS NOT NULL' + null_cond) +
           f' GROUP BY rlabel, clabel ORDER BY rlabel')
    data = rows_as_dicts(db.execute(sql, P))
    cols = sorted({str(r['clabel']) for r in data}, key=lambda x: (len(x), x))
    rows_map = {}
    for r in data:
        k = r['rlabel'] or 'نامشخص'
        rows_map.setdefault(k, {'label': k, 'cells': {}, 'total': 0})
        rows_map[k]['cells'][str(r['clabel'])] = r['val'] or 0
        rows_map[k]['total'] += r['val'] or 0
    rows = sorted(rows_map.values(), key=lambda r: -r['total'])
    grand = sum(r['total'] for r in rows)
    return jsonify({'cols': cols, 'rows': rows, 'grand_total': grand})


@app.route('/api/export/csv')
def api_export_csv():
    db = get_db()
    ds = request.args.get('dataset', 'transactions')
    if ds not in DATASETS:
        return jsonify({'error': 'dataset نامعتبر'}), 400
    d = DATASETS[ds]
    alias = {'transactions': 't', 'requests': 'r', 'needy': 'n', 'members': 'm', 'anomalies': 'a'}[ds]
    f = F(request.args)
    conds, params = [], []
    if ds in ('transactions', 'requests'):
        cy, cp = f_conds(f, alias, with_year=True, with_office=False)
        conds += cy
        params += cp
    elif ds != 'anomalies':
        if f['province'] != 'all':
            conds.append(('c.province_id = ?' if ds == 'members' else f'{alias}.province_id = ?'))
            params.append(int(f['province']))
    W = ('WHERE ' + ' AND '.join(conds)) if conds else ''
    limit = min(200000, int(request.args.get('limit', 50000)))
    cols = [c[0] for c in d['cols']]
    out = io.StringIO()
    out.write('\ufeff')  # BOM برای اکسل فارسی
    out.write(','.join(d['cols'][i][1] for i in range(len(cols))) + '\n')
    cur = db.execute(f'SELECT {d["select"]} FROM {d["table"]} {W} LIMIT {limit}', params)
    import csv as _csv
    writer = _csv.writer(out)
    count = 0
    for r in cur:
        writer.writerow([r[c] if r[c] is not None else '' for c in cols])
        count += 1
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={ds}_export.csv'})


# ─────────────────── narrative / insights / networks ────────────

@app.route('/api/narrative')
@cached()
def api_narrative():
    db = get_db()
    f = F(request.args)
    return jsonify(narrative.build_narrative(db, f))


@app.route('/api/insights')
@cached()
def api_insights():
    db = get_db()
    f = F(request.args)
    return jsonify({'insights': narrative.build_insights(db, f)})


@app.route('/api/networks')
@cached()
def api_networks():
    db = get_db()
    f = F(request.args)
    prov_f = ' AND n.province_id = ' + str(int(f['province'])) if f['province'] != 'all' else ''
    rows = rows_as_dicts(db.execute(
        'SELECT nw.network label, COUNT(DISTINCT nw.center_id) centers, SUM(nw.people) people, '
        ' (SELECT COUNT(*) FROM centers c2 WHERE 1=1' + prov_f.replace('n.', 'c2.') + ') total_centers '
        'FROM networks nw JOIN centers c ON c.id=nw.center_id '
        'WHERE 1=1' + prov_f.replace('n.', 'c.') + ' GROUP BY nw.network ORDER BY centers DESC'))
    for r in rows:
        r['coverage'] = round(r['centers'] / max(r['total_centers'], 1) * 100, 1)
    by_prov = rows_as_dicts(db.execute(
        'SELECT p.name prov, nw.network, SUM(nw.people) people FROM networks nw '
        'JOIN centers c ON c.id=nw.center_id JOIN provinces p ON p.id=c.province_id '
        'GROUP BY p.name, nw.network'))
    return jsonify({'rows': rows, 'by_prov': by_prov})


@app.route('/api/finance')
@cached()
def api_finance():
    db = get_db()
    cats = [r['category'] for r in db.execute(
        'SELECT DISTINCT category FROM finance_province ORDER BY id')]
    matrix = rows_as_dicts(db.execute(
        'SELECT p.name, fp.category, fp.amount FROM finance_province fp '
        'JOIN provinces p ON p.id=fp.province_id'))
    rows_map = {}
    for r in matrix:
        rows_map.setdefault(r['name'], {})[r['category']] = r['amount']
    rows = [{'province': k, **v} for k, v in rows_map.items()]
    comp = rows_as_dicts(db.execute(
        'SELECT p.name, cp.year, cp.month, cp.centers_ok, cp.centers_not_ok, cp.centers_review, '
        'cp.amount_ok, cp.amount_not_ok FROM compensation_province cp JOIN provinces p ON p.id=cp.province_id'))
    tx_totals = rows_as_dicts(db.execute(
        "SELECT flow || ' ' || method label, SUM(amount) s FROM transactions GROUP BY flow, method"))
    return jsonify({'categories': cats, 'rows': rows, 'compensation': comp, 'tx_totals': tx_totals})


@app.route('/api/quality')
@cached()
def api_quality():
    db = get_db()
    logs = rows_as_dicts(db.execute('SELECT * FROM import_log ORDER BY id DESC LIMIT 60'))
    tables = []
    checks = [
        ('مراکز', 'centers', 'SELECT COUNT(*) n, AVG(total_active) m FROM centers'),
        ('نیازمندان', 'needy', 'SELECT COUNT(*) n, ROUND(100.0*SUM(CASE WHEN decile IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) null_decile, ROUND(100.0*SUM(CASE WHEN mobile IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) null_mobile FROM needy'),
        ('درخواست‌ها', 'requests', 'SELECT COUNT(*) n, ROUND(100.0*SUM(CASE WHEN national_id IS NULL OR national_id="" THEN 1 ELSE 0 END)/COUNT(*),1) null_nat FROM requests'),
        ('تراکنش‌ها', 'transactions', 'SELECT COUNT(*) n, ROUND(100.0*SUM(CASE WHEN center_id IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) null_center FROM transactions'),
        ('اعضای کارتکس', 'members', 'SELECT COUNT(*) n, ROUND(100.0*SUM(CASE WHEN national_id IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) null_nat FROM members'),
        ('همیاران', 'hamyaran', 'SELECT COUNT(*) n, ROUND(100.0*SUM(CASE WHEN mobile IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) null_mobile FROM hamyaran'),
    ]
    for label, tname, sql in checks:
        r = db.execute(sql).fetchone()
        tables.append({'table': label, 'rows': r['n'],
                       'notes': {k: r[k] for k in r.keys() if k != 'n' and r[k] is not None}})
    anomalies = rows_as_dicts(db.execute('SELECT * FROM anomalies ORDER BY amount DESC LIMIT 30'))
    real_anchor = dict(C.REAL_FINANCE)
    tx_anchor = {
        'دریافت نقدی': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='دریافت' AND method='نقدی'").fetchone()['s'] or 0,
        'دریافت غیرنقدی': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='دریافت' AND method='غیرنقدی'").fetchone()['s'] or 0,
        'پرداخت نقدی': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='پرداخت' AND method='نقدی'").fetchone()['s'] or 0,
        'پرداخت غیرنقدی': db.execute("SELECT SUM(amount) s FROM transactions WHERE flow='پرداخت' AND method='غیرنقدی'").fetchone()['s'] or 0,
    }
    return jsonify({'logs': logs, 'tables': tables, 'anomalies': anomalies,
                    'real_anchor': real_anchor, 'tx_anchor': tx_anchor,
                    'agg_reports': db.execute('SELECT COUNT(*) n FROM agg_reports').fetchone()['n']})


# ─────────────────────────── import ─────────────────────────────

@app.route('/api/import', methods=['POST'])
def api_import():
    from importer import import_file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = get_db()
    ensure_schema(db)
    results = []
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'فایلی ارسال نشده است'}), 400
    for fs in files:
        path = os.path.join(UPLOAD_DIR, fs.filename)
        fs.save(path)
        try:
            results.append(import_file(db, path, extra_log=True))
        except Exception as e:  # noqa
            results.append({'filename': fs.filename, 'error': str(e)[:300]})
    cache_bump()  # داده تغییر کرد — کش همه داشبوردها باطل شود
    prewarm_async()  # کش داشبوردها با دادهٔ جدید دوباره گرم شود
    return jsonify({'results': results})


@app.route('/api/reset-db', methods=['POST'])
def api_reset_db():
    """پاک‌سازی کامل همه جدول‌ها برای شروع با داده واقعی (حذف داده نمونه و بارگذاری‌های قبلی)."""
    db = get_db()
    names = [r['name'] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in names:
        db.execute(f'DELETE FROM "{t}"')
    set_meta(db, 'data_mode', 'empty')
    db.commit()
    cache_bump()  # داده تغییر کرد — کش همه داشبوردها باطل شود
    prewarm_async()
    return jsonify({'ok': True, 'cleared': len(names)})


@app.route('/api/recompute', methods=['POST'])
def api_recompute():
    """بازمحاسبه امتیاز مرکب و مدال مراکز پس از بارگذاری داده واقعی."""
    from generator import score_centers
    db = get_db()
    ensure_schema(db)
    score_centers(db)
    set_meta(db, 'imported_at', str(int(time.time())))
    n = db.execute('SELECT COUNT(*) n FROM centers').fetchone()['n']
    cache_bump()  # داده تغییر کرد — کش همه داشبوردها باطل شود
    prewarm_async()
    return jsonify({'ok': True, 'centers_scored': n})


@app.route('/api/health')
def api_health():
    # نسخه برای اطمینان از اجرای آخرین کد (اگر نسخه قدیمی بود یعنی سرور ری‌استارت نشده)
    return jsonify({'ok': True, 'time': int(time.time()), 'version': SERVER_VERSION})


# ── گرم‌کردن کش در پس‌زمینه ──
# پس از استارت سرور و پس از هر تغییر داده، پرکاربردترین endpointها در نخِ پس‌زمینه
# گرم می‌شوند تا اولین لود داشبورد کاربر هم به‌جای چند ثانیه، در چند میلی‌ثانیه باز شود.
# نکتهٔ مهم: query string باید دقیقاً همان شکلی باشد که فرانت‌اند (buildQS) می‌سازد،
# وگرنه کلید کش یکی نمی‌شود و گرم‌کردن بی‌اثر است.
DEFAULT_QS = 'year=all&province=all&office=all'
# endpointهایی که فرانت‌اند بدون هیچ query string صدا می‌زند
PREWARM_NO_QUERY = ['/api/meta', '/api/payments/compare', '/api/finance', '/api/quality',
                    '/api/explore/tables', '/api/kpi21', '/api/performance']
# endpointهایی که با فیلترهای پیش‌فرض (همه «همه») صدا زده می‌شوند
PREWARM_DEFAULT_QS = ['/api/overview', '/api/demographics', '/api/payments/categories',
                      '/api/provinces', '/api/centers/summary', '/api/kpis', '/api/insights',
                      '/api/narrative', '/api/networks']
# endpointهای سنگین صفحهٔ خاص با پارامترهای پیش‌فرض همان صفحه
import urllib.parse as _up
PREWARM_SPECIAL = [
    f'/api/pivot?{DEFAULT_QS}&row=province&col=year&metric=amount',
    f'/api/records?{DEFAULT_QS}&dataset=transactions&page=1&per=15&dir=desc',
    # flow با فرم percent-encoded دقیقاً مانند URLSearchParams مرورگر — تا کلید کش یکی شود
    f'/api/payments/trend?{DEFAULT_QS}&flow={_up.quote("پرداخت")}',
]
# پرکاربردترین‌ها برای هر سال (وقتی کاربر سال را تغییر می‌دهد)
PREWARM_YEAR_PATHS = ['/api/overview', '/api/kpis', '/api/demographics', '/api/payments/trend',
                      '/api/payments/categories', '/api/provinces', '/api/centers/summary']


def prewarm_async():
    """گرم‌کردن کش در نخ جدا — استارت سرور و پاسخ درخواستِ import مسدود نمی‌شود."""
    import threading

    def _warm():
        try:
            years = []
            with app.test_client() as c:
                try:
                    r = c.get('/api/meta')
                    years = ((r.get_json() or {}).get('years') or [])[:3]
                except Exception:  # noqa
                    years = []
                latest = years[-1] if years else None
                paths = list(PREWARM_NO_QUERY)
                paths += [f'{p}?{DEFAULT_QS}' for p in PREWARM_DEFAULT_QS]
                paths += list(PREWARM_SPECIAL)
                if latest:
                    paths.append(f'/api/slide-report?year={latest}&province=all&office=all')
                    paths.append(f'/api/performance?year1={latest}&province=all&office=all')
                for y in years:
                    paths += [f'{p}?year={y}&province=all&office=all' for p in PREWARM_YEAR_PATHS]
                for p in paths:
                    try:
                        c.get(p)
                    except Exception:  # noqa
                        pass
                print(f'کش داشبوردها گرم شد ({len(paths)} مسیر) — اولین لود هم سریع است.', flush=True)
        except Exception:  # noqa
            pass

    threading.Thread(target=_warm, daemon=True, name='api-prewarm').start()


# ─────────────────────── static frontend ────────────────────────


def _no_cache(resp):
    """index.html باید همیشه تازه لود شود تا bundle جدید (با hash جدید) دیده شود"""
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp


# بایت‌های فشردهٔ assetهای بزرگ (باندل JS/CSS) در حافظه نگه داشته می‌شود
_ASSET_GZ_CACHE = {}


def _compressed_asset(path):
    """assetهای هش‌دار بزرگ (JS/CSS/SVG) را با gzip برمی‌گرداند — حجم سیم تا ~۷۵٪ کمتر"""
    full = os.path.join(FRONT_DIST, path)
    if not os.path.isfile(full):
        return None
    if not path.endswith(('.js', '.css', '.svg')) or os.path.getsize(full) < 10240:
        return None
    accept = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept.lower():
        return None
    mtime = os.path.getmtime(full)
    hit = _ASSET_GZ_CACHE.get(path)
    if hit and hit[0] == mtime:
        packed, raw_len = hit[1], hit[2]
    else:
        import gzip as _gzip
        with open(full, 'rb') as fh:
            raw = fh.read()
        packed = _gzip.compress(raw, compresslevel=6)
        raw_len = len(raw)
        if len(_ASSET_GZ_CACHE) > 32:
            _ASSET_GZ_CACHE.clear()
        _ASSET_GZ_CACHE[path] = (mtime, packed, raw_len)
    mime = 'application/javascript' if path.endswith('.js') else (
        'text/css' if path.endswith('.css') else 'image/svg+xml')
    resp = Response(packed, mimetype=mime)
    resp.headers['Content-Encoding'] = 'gzip'
    resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    resp.headers['Vary'] = 'Accept-Encoding'
    resp.headers['X-Original-Size'] = str(raw_len)
    return resp


@app.route('/')
def index():
    if os.path.exists(os.path.join(FRONT_DIST, 'index.html')):
        return _no_cache(send_from_directory(FRONT_DIST, 'index.html'))
    return Response('<h3>Frontend build not found — run: npm run build</h3>', mimetype='text/html')


@app.route('/<path:path>')
def static_files(path):
    # مسیرهای ناشناختهٔ API هرگز نباید index.html بگیرند — JSON خطا برگردانند
    if path == 'api' or path.startswith('api/'):
        return jsonify({'error': f'مسیر API یافت نشد: /{path}'}), 404
    full = os.path.join(FRONT_DIST, path)
    if os.path.isfile(full):
        if path.startswith('assets/'):
            gz = _compressed_asset(path)
            if gz is not None:
                return gz
            resp = send_from_directory(FRONT_DIST, path)
            # فایل‌های باندل هش‌دار — کش بلندمدت برای سرعت لود داشبوردها
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return resp
        resp = send_from_directory(FRONT_DIST, path)
        if path == 'index.html':
            return _no_cache(resp)
        return resp
    if os.path.exists(os.path.join(FRONT_DIST, 'index.html')):
        return _no_cache(send_from_directory(FRONT_DIST, 'index.html'))
    return Response('<h3>Frontend build not found — run: npm run build</h3>', mimetype='text/html')


@app.errorhandler(404)
def not_found(_e):
    """هر مسیر ناشناختهٔ API به‌جای HTML حتماً JSON برگرداند تا خطای JSON.parse رخ ندهد"""
    if request.path.startswith('/api/'):
        return jsonify({'error': f'مسیر API یافت نشد: {request.path}'}), 404
    return _no_cache(send_from_directory(FRONT_DIST, 'index.html'))


@app.errorhandler(500)
def server_error(_e):
    """خطای داخلی در مسیرهای API هم JSON برگرداند، نه صفحهٔ HTML"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'خطای داخلی سرور در پردازش درخواست'}), 500
    return 'Internal Server Error', 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    # اعمال اسکیما و شاخص‌های جدید روی پایگاه داده موجود (یک‌بار در هر اجرا)
    with app.app_context():
        _db = get_db()
        ensure_schema(_db)
    print(f'نیکوکاری {SERVER_VERSION} — سرور روی پورت {port}')
    prewarm_async()  # گرم‌کردن کش در پس‌زمینه تا اولین لود کاربر هم سریع باشد
    app.run(host='0.0.0.0', port=port, threaded=True)
