# -*- coding: utf-8 -*-
"""
APIهای توسعه‌یافته داشبورد نیکوکاری:
  ۱) /api/explore/*      — رصد هر جدول با فیلتر هر ستون، صفحه‌بندی، گروه‌بندی و خروجی CSV
  ۲) /api/kpi21          — شاخص‌های ارزیابی جدول ۶-۲ اداره کل امور اجرایی مشارکت‌های مردمی
  ۳) /api/performance    — عملکرد دوره‌ای: مقایسه دو سال به تفکیک ماه، استان، مرکز، نوع خدمت و نیازمندان
  ۴) /api/slide-report   — داده گزارش اسلایدی عملکرد برای بازه زمانی انتخابی
"""
import csv as _csv
import io
import json

from flask import Blueprint, Response, jsonify, request

from apicache import cached
from db import get_meta

bp = Blueprint('ext', __name__)

# ───────────────────────── فراداده جدول‌های رصد ─────────────────────────
# هر ستون: (کلید, عبارت SQL, برچسب فارسی, نوع: text|num)

EXPLORE = {
    'transactions': {
        'label': 'تراکنش‌ها — پرداخت و دریافت',
        'frm': 'transactions t LEFT JOIN provinces p ON p.id=t.province_id '
               'LEFT JOIN centers c ON c.id=t.center_id',
        'order': 't.id',
        'cols': [
            ('tracking_no', 't.tracking_no', 'شماره رهگیری', 'text'),
            ('date_j', 't.date_j', 'تاریخ', 'text'),
            ('year', 't.year', 'سال', 'num'),
            ('month', 't.month', 'ماه', 'num'),
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('flow', 't.flow', 'نوع (دریافت/پرداخت)', 'text'),
            ('method', 't.method', 'روش (نقدی/غیرنقدی)', 'text'),
            ('category', 't.category', 'فعالیت', 'text'),
            ('source', 't.source', 'منبع', 'text'),
            ('amount', 't.amount', 'مبلغ (ریال)', 'num'),
            ('beneficiaries', 't.beneficiaries', 'تعداد ذی‌نفع', 'num'),
            ('src_file', 't.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'requests': {
        'label': 'درخواست‌ها و گزارش خدمات',
        'frm': 'requests r LEFT JOIN provinces p ON p.id=r.province_id '
               'LEFT JOIN centers c ON c.id=r.center_id',
        'order': 'r.id',
        'cols': [
            ('tracking_no', 'r.tracking_no', 'شماره پیگیری', 'text'),
            ('date_j', 'r.date_j', 'تاریخ', 'text'),
            ('year', 'r.year', 'سال', 'num'),
            ('month', 'r.month', 'ماه', 'num'),
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('request_type', 'r.request_type', 'نوع درخواست', 'text'),
            ('category', 'r.category', 'دسته خدمت', 'text'),
            ('national_id', 'r.national_id', 'کد ملی', 'text'),
            ('creator', 'r.creator', 'ایجادکننده', 'text'),
            ('status', 'r.status', 'وضعیت درخواست', 'text'),
            ('process_status', 'r.process_status', 'وضعیت فرآیندی', 'text'),
            ('src_file', 'r.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'needy': {
        'label': 'نیازمندان (مددجویان)',
        'frm': 'needy n LEFT JOIN provinces p ON p.id=n.province_id '
               'LEFT JOIN centers c ON c.id=n.center_id',
        'order': 'n.id',
        'cols': [
            ('national_id', 'n.national_id', 'کد ملی', 'text'),
            ('name', 'n.name', 'نام', 'text'),
            ('family', 'n.family', 'نام خانوادگی', 'text'),
            ('gender', 'n.gender', 'جنسیت', 'text'),
            ('birth', 'n.birth', 'تاریخ تولد', 'text'),
            ('age', 'n.age', 'سن', 'num'),
            ('province', 'p.name', 'استان', 'text'),
            ('office', 'n.office', 'اداره', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('need_type', 'n.need_type', 'نوع نیازمند', 'text'),
            ('need_group', 'n.need_group', 'گروه نیازمندی', 'text'),
            ('vital', 'n.vital', 'وضعیت حیات', 'text'),
            ('decile', 'n.decile', 'دهک', 'num'),
            ('mobile', 'n.mobile', 'موبایل', 'text'),
            ('src_file', 'n.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'members': {
        'label': 'اعضا و ارکان مراکز (کارتکس اعضا)',
        'frm': 'members m LEFT JOIN centers c ON c.id=m.center_id '
               'LEFT JOIN provinces p ON p.id=c.province_id',
        'order': 'm.id',
        'cols': [
            ('national_id', 'm.national_id', 'کد ملی', 'text'),
            ('name', 'm.name', 'نام', 'text'),
            ('family', 'm.family', 'نام خانوادگی', 'text'),
            ('gender', 'm.gender', 'جنسیت', 'text'),
            ('birth', 'm.birth', 'تاریخ تولد', 'text'),
            ('age', 'm.age', 'سن', 'num'),
            ('role', 'm.role', 'مسئولیت', 'text'),
            ('status', 'm.status', 'وضعیت عضویت', 'text'),
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('education', 'm.education', 'تحصیلات', 'text'),
            ('job', 'm.job', 'شغل', 'text'),
            ('bank_debt', 'm.bank_debt', 'بدهکار بانکی', 'text'),
            ('tax_debt', 'm.tax_debt', 'بدهکار مالیاتی', 'text'),
            ('alive', 'm.alive', 'قید حیات', 'text'),
            ('criminal', 'm.criminal', 'سوء پیشینه', 'text'),
            ('src_file', 'm.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'hamyaran': {
        'label': 'همیاران و حامیان حقیقی',
        'frm': 'hamyaran h LEFT JOIN provinces p ON p.id=h.province_id '
               'LEFT JOIN centers c ON c.id=h.center_id',
        'order': 'h.id',
        'cols': [
            ('national_id', 'h.national_id', 'کد ملی', 'text'),
            ('name', 'h.name', 'نام', 'text'),
            ('family', 'h.family', 'نام خانوادگی', 'text'),
            ('father', 'h.father', 'نام پدر', 'text'),
            ('gender', 'h.gender', 'جنسیت', 'text'),
            ('birth', 'h.birth', 'تاریخ تولد', 'text'),
            ('age', 'h.age', 'سن', 'num'),
            ('mobile', 'h.mobile', 'موبایل', 'text'),
            ('province', 'p.name', 'استان', 'text'),
            ('office', 'h.office', 'اداره/شهرستان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('status', 'h.status', 'وضعیت', 'text'),
            ('src_file', 'h.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'centers': {
        'label': 'مراکز نیکوکاری',
        'frm': 'centers c LEFT JOIN provinces p ON p.id=c.province_id '
               'LEFT JOIN offices o ON o.id=c.office_id',
        'order': 'c.id',
        'cols': [
            ('license_no', 'c.license_no', 'شماره مجوز', 'text'),
            ('name', 'c.name', 'نام مرکز', 'text'),
            ('province', 'p.name', 'استان', 'text'),
            ('office', 'o.name', 'اداره', 'text'),
            ('status', 'c.status', 'وضعیت فعالیت', 'text'),
            ('center_type', 'c.center_type', 'نوع فعالیت', 'text'),
            ('urban_rural', 'c.urban_rural', 'شهری/روستایی', 'text'),
            ('ownership', 'c.ownership', 'مالکیت مکان', 'text'),
            ('area', 'c.area', 'متراژ', 'num'),
            ('chair', 'c.chair', 'رئیس هیئت امنا', 'num'),
            ('vice', 'c.vice', 'نايب رئيس', 'num'),
            ('exec_mgr', 'c.exec_mgr', 'مدیر اجرایی', 'num'),
            ('finance', 'c.finance', 'مسئول مالی', 'num'),
            ('inspector', 'c.inspector', 'بازرس', 'num'),
            ('total_active', 'c.total_active', 'اعضای فعال', 'num'),
            ('total_inactive', 'c.total_inactive', 'اعضای غیرفعال', 'num'),
            ('score', 'c.score', 'امتیاز', 'num'),
            ('medal', 'c.medal', 'مدال', 'text'),
            ('created_year', 'c.created_year', 'سال تأسیس', 'num'),
        ],
    },
    'networks': {
        'label': 'شبکه‌سازی و شبکه‌های تخصصی',
        'frm': 'networks nw LEFT JOIN centers c ON c.id=nw.center_id '
               'LEFT JOIN provinces p ON p.id=c.province_id',
        'order': 'nw.id',
        'cols': [
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('network', 'nw.network', 'شبکه تخصصی', 'text'),
            ('people', 'nw.people', 'ظرفیت (نفر)', 'num'),
            ('src_file', 'nw.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'packs': {
        'label': 'تعریف پک‌های کمک‌رسانی',
        'frm': 'packs pk',
        'order': 'pk.id',
        'cols': [
            ('pack_type', 'pk.pack_type', 'نوع پک', 'text'),
            ('activity', 'pk.activity', 'فعالیت', 'text'),
            ('source', 'pk.source', 'منبع', 'text'),
            ('items', 'pk.items', 'اقلام', 'text'),
        ],
    },
    'legal_donors': {
        'label': 'نیکوکاران حقوقی (شرکت‌ها و صنایع)',
        'frm': 'legal_donors ld LEFT JOIN provinces p ON p.id=ld.province_id '
               'LEFT JOIN centers c ON c.id=ld.center_id',
        'order': 'ld.id',
        'cols': [
            ('name', 'ld.name', 'نام حقوقی', 'text'),
            ('national_id', 'ld.national_id', 'شناسه ملی', 'text'),
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('amount', 'ld.amount', 'مبلغ (ریال)', 'num'),
            ('year', 'ld.year', 'سال', 'num'),
            ('src_file', 'ld.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'finance_province': {
        'label': 'دریافت و پرداخت به تفکیک استان',
        'frm': 'finance_province fp LEFT JOIN provinces p ON p.id=fp.province_id',
        'order': 'fp.id',
        'cols': [
            ('province', 'p.name', 'استان', 'text'),
            ('category', 'fp.category', 'ردیف مالی', 'text'),
            ('amount', 'fp.amount', 'مبلغ (ریال)', 'num'),
            ('src_file', 'fp.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'compensation_province': {
        'label': 'جبران خدمات به تفکیک استان',
        'frm': 'compensation_province cp LEFT JOIN provinces p ON p.id=cp.province_id',
        'order': 'cp.id',
        'cols': [
            ('province', 'p.name', 'استان', 'text'),
            ('year', 'cp.year', 'سال', 'num'),
            ('month', 'cp.month', 'ماه', 'num'),
            ('centers_ok', 'cp.centers_ok', 'مراکز تاییدشده', 'num'),
            ('centers_not_ok', 'cp.centers_not_ok', 'مراکز تاییدنشده', 'num'),
            ('centers_review', 'cp.centers_review', 'مراکز در بررسی', 'num'),
            ('amount_ok', 'cp.amount_ok', 'مبلغ تاییدشده', 'num'),
            ('amount_not_ok', 'cp.amount_not_ok', 'مبلغ تاییدنشده', 'num'),
            ('src_file', 'cp.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'anomalies': {
        'label': 'تراکنش‌های ثبت‌نشده (ناهنجاری‌ها)',
        'frm': 'anomalies a LEFT JOIN provinces p ON p.id=a.province_id '
               'LEFT JOIN centers c ON c.id=a.center_id',
        'order': 'a.id',
        'cols': [
            ('province', 'p.name', 'استان', 'text'),
            ('center', 'c.name', 'مرکز', 'text'),
            ('doc_no', 'a.doc_no', 'شماره سند', 'text'),
            ('date_j', 'a.date_j', 'تاریخ', 'text'),
            ('title', 'a.title', 'عنوان', 'text'),
            ('descr', 'a.descr', 'شرح', 'text'),
            ('flow', 'a.flow', 'نوع', 'text'),
            ('amount', 'a.amount', 'مبلغ (ریال)', 'num'),
            ('src_file', 'a.src_file', 'فایل مبدأ', 'text'),
        ],
    },
    'agg_reports': {
        'label': 'گزارش‌های عمومی (اسکیمای ناشناخته)',
        'frm': 'agg_reports ag',
        'order': 'ag.id',
        'cols': [
            ('source', 'ag.source', 'فایل مبدأ', 'text'),
            ('province', 'ag.province', 'استان', 'text'),
            ('city', 'ag.city', 'شهرستان', 'text'),
            ('center', 'ag.center', 'مرکز', 'text'),
            ('amount', 'ag.amount', 'مبلغ (ریال)', 'num'),
            ('extra', 'ag.extra', 'سایر ستون‌ها', 'text'),
        ],
    },
    'import_log': {
        'label': 'گزارش کیفیت بارگذاری فایل‌ها',
        'frm': 'import_log il',
        'order': 'il.id',
        'cols': [
            ('filename', 'il.filename', 'نام فایل', 'text'),
            ('schema_name', 'il.schema_name', 'اسکیما', 'text'),
            ('encoding', 'il.encoding', 'کدگذاری', 'text'),
            ('rows_read', 'il.rows_read', 'رکورد خوانده‌شده', 'num'),
            ('rows_inserted', 'il.rows_inserted', 'رکورد واردشده', 'num'),
            ('duplicates', 'il.duplicates', 'تکراری', 'num'),
            ('nulls_pct', 'il.nulls_pct', 'درصد خالی', 'num'),
            ('warnings', 'il.warnings', 'هشدارها', 'text'),
            ('imported_at', 'il.imported_at', 'زمان بارگذاری', 'text'),
        ],
    },
}

OPS = ('eq', 'ne', 'contains', 'ncontains', 'gt', 'ge', 'lt', 'le', 'between', 'empty', 'nempty')


def _table(key):
    return EXPLORE.get(key)


def _colmeta(t, col_key):
    for c in t['cols']:
        if c[0] == col_key:
            return c
    return None


def build_where(t, filters, search=''):
    """ساخت WHERE امن از فیلترهای ستونی + جستجوی سراسری"""
    conds, params = [], []
    for ft in filters or []:
        cm = _colmeta(t, str(ft.get('col', '')))
        op = str(ft.get('op', ''))
        if not cm or op not in OPS:
            continue
        expr, typ = cm[1], cm[3]
        val = ft.get('val')
        val2 = ft.get('val2')
        if op == 'empty':
            conds.append(f'({expr} IS NULL OR CAST({expr} AS TEXT) = \'\')')
        elif op == 'nempty':
            conds.append(f'({expr} IS NOT NULL AND CAST({expr} AS TEXT) != \'\')')
        elif op == 'contains':
            conds.append(f'CAST({expr} AS TEXT) LIKE ?')
            params.append(f'%{val}%')
        elif op == 'ncontains':
            conds.append(f'(CAST({expr} AS TEXT) NOT LIKE ? OR {expr} IS NULL)')
            params.append(f'%{val}%')
        elif op == 'between':
            if typ == 'num':
                try:
                    a, b = float(val), float(val2)
                    conds.append(f'{expr} BETWEEN ? AND ?')
                    params += [a, b]
                except (TypeError, ValueError):
                    pass
            else:
                conds.append(f'CAST({expr} AS TEXT) BETWEEN ? AND ?')
                params += [str(val or ''), str(val2 or '')]
        else:
            if typ == 'num':
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    continue
            else:
                v = str(val if val is not None else '')
            sym = {'eq': '=', 'ne': '!=', 'gt': '>', 'ge': '>=', 'lt': '<', 'le': '<='}[op]
            conds.append(f'{expr} {sym} ?')
            params.append(v)
    if search:
        text_cols = [c[1] for c in t['cols'] if c[3] == 'text'][:8]
        if text_cols:
            like = ' OR '.join(f'CAST({x} AS TEXT) LIKE ?' for x in text_cols)
            conds.append(f'({like})')
            params += [f'%{search}%'] * len(text_cols)
    return ('WHERE ' + ' AND '.join(conds)) if conds else '', params


@bp.route('/api/explore/tables')
@cached()
def explore_tables():
    db = get_db_ext()
    out = []
    for key, t in EXPLORE.items():
        try:
            n = db.execute(f'SELECT COUNT(*) n FROM {t["frm"]}').fetchone()['n']
        except Exception:  # noqa
            n = 0
        out.append({'key': key, 'label': t['label'], 'count': n,
                    'cols': [{'key': c[0], 'label': c[2], 'type': c[3]} for c in t['cols']]})
    return jsonify({'tables': out})


def get_db_ext():
    """اتصال دیتابیس مشترک با app اصلی (بسته شدن در teardown همان request)"""
    from flask import g
    from db import connect
    if 'db' not in g:
        g.db = connect()
    return g.db


@bp.route('/api/explore')
@cached()
def explore_data():
    """رصد جدول: فیلتر هر ستون + مرتب‌سازی + صفحه‌بندی + جمع کل"""
    db = get_db_ext()
    t = _table(request.args.get('table', 'transactions'))
    if not t:
        return jsonify({'error': 'جدول نامعتبر'}), 400
    try:
        filters = json.loads(request.args.get('filters', '[]'))
    except ValueError:
        filters = []
    search = request.args.get('search', '')
    W, P = build_where(t, filters, search)
    page = max(1, int(request.args.get('page', 1)))
    per = min(100, max(5, int(request.args.get('per', 15))))
    sort_key = request.args.get('sort', '')
    dir_ = 'DESC' if request.args.get('dir', 'desc') == 'desc' else 'ASC'
    order_expr = t['order']
    if sort_key:
        cm = _colmeta(t, sort_key)
        if cm:
            order_expr = f'{cm[1]} {dir_}, {t["order"]} DESC'
    total = db.execute(f'SELECT COUNT(*) n FROM {t["frm"]} {W}', P).fetchone()['n']
    sel = ', '.join(f'{c[1]} AS "{c[0]}"' for c in t['cols'])
    rows = [dict(r) for r in db.execute(
        f'SELECT {sel} FROM {t["frm"]} {W} ORDER BY {order_expr} LIMIT ? OFFSET ?',
        P + [per, (page - 1) * per])]
    num_cols = [c for c in t['cols'] if c[3] == 'num']
    aggs = {}
    for c in num_cols[:4]:
        r = db.execute(f'SELECT SUM({c[1]}) s, AVG({c[1]}) a FROM {t["frm"]} {W}', P).fetchone()
        aggs[c[0]] = {'sum': r['s'], 'avg': round(r['a'], 1) if r['a'] is not None else None}
    return jsonify({'rows': rows, 'total': total, 'page': page, 'per': per,
                    'cols': [{'key': c[0], 'label': c[2], 'type': c[3]} for c in t['cols']],
                    'aggs': aggs})


@bp.route('/api/explore/group')
@cached()
def explore_group():
    """گروه‌بندی: GROUP BY یک ستون با تابع تجمیعی"""
    db = get_db_ext()
    t = _table(request.args.get('table', 'transactions'))
    if not t:
        return jsonify({'error': 'جدول نامعتبر'}), 400
    cm = _colmeta(t, request.args.get('group', ''))
    if not cm:
        return jsonify({'error': 'ستون گروه‌بندی نامعتبر'}), 400
    agg = request.args.get('agg', 'count')
    agg_col = _colmeta(t, request.args.get('agg_col', ''))
    agg_sql = 'COUNT(*)'
    if agg in ('sum', 'avg', 'min', 'max') and agg_col and agg_col[3] == 'num':
        agg_sql = f'{agg.upper()}({agg_col[1]})'
    try:
        filters = json.loads(request.args.get('filters', '[]'))
    except ValueError:
        filters = []
    W, P = build_where(t, filters, request.args.get('search', ''))
    null_cond = f' AND {cm[1]} IS NOT NULL AND CAST({cm[1]} AS TEXT) != \'\''
    Wn = (W or 'WHERE 1=1') + null_cond
    sql = (f'SELECT CAST({cm[1]} AS TEXT) lbl, {agg_sql} val, COUNT(*) cnt '
           f'FROM {t["frm"]} {Wn} GROUP BY lbl ORDER BY val DESC LIMIT 60')
    rows = [dict(r) for r in db.execute(sql, P)]
    total = db.execute(f'SELECT COUNT(*) n FROM {t["frm"]} {Wn}', P).fetchone()['n']
    return jsonify({'rows': rows, 'total': total, 'agg': agg,
                    'group_label': cm[2],
                    'value_label': 'تعداد رکورد' if agg == 'count' else
                    f'{agg.upper()} {agg_col[2] if agg_col else ""}'})


@bp.route('/api/explore/export')
def explore_export():
    """خروجی CSV نتایج فیلترشده (حداکثر ۱۰۰ هزار ردیف)"""
    db = get_db_ext()
    t = _table(request.args.get('table', 'transactions'))
    if not t:
        return jsonify({'error': 'جدول نامعتبر'}), 400
    try:
        filters = json.loads(request.args.get('filters', '[]'))
    except ValueError:
        filters = []
    W, P = build_where(t, filters, request.args.get('search', ''))
    sel = ', '.join(f'{c[1]} AS "{c[0]}"' for c in t['cols'])
    limit = min(100000, int(request.args.get('limit', 50000)))
    out = io.StringIO()
    out.write('\ufeff')
    w = _csv.writer(out)
    w.writerow([c[2] for c in t['cols']])
    for r in db.execute(f'SELECT {sel} FROM {t["frm"]} {W} LIMIT {limit}', P):
        w.writerow(['' if v is None else v for v in r])
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=explore_{t["frm"].split()[0]}.csv'})


# ───────────────────── شاخص‌های جدول ۶-۲ (آیتم ۷) ─────────────────────

@bp.route('/api/kpi21')
@cached()
def kpi21():
    db = get_db_ext()
    c = db

    def one(sql, params=()):
        r = c.execute(sql, params).fetchone()
        if r is None:
            return 0
        v = r[0]
        return v if v is not None else 0

    def pct(a, b):
        return round(a / b * 100, 1) if b else None

    total_centers = one('SELECT COUNT(*) FROM centers')
    licensed = one("SELECT COUNT(*) FROM centers WHERE license_no IS NOT NULL AND license_no != ''")
    active_centers = one("SELECT COUNT(*) FROM centers WHERE status = 'فعال'")
    active_real = one("SELECT COUNT(*) FROM centers WHERE status='فعال' AND id IN "
                      '(SELECT DISTINCT center_id FROM transactions)')
    prov_total = one('SELECT COUNT(*) FROM provinces')
    prov_covered = one('SELECT COUNT(DISTINCT province_id) FROM transactions')
    ranked = one('SELECT COUNT(*) FROM centers WHERE score IS NOT NULL')
    medaled = one("SELECT COUNT(*) FROM centers WHERE medal IS NOT NULL AND medal != ''")
    full_board = one('SELECT COUNT(*) FROM centers WHERE chair > 0 AND vice > 0 AND finance > 0 '
                     'AND (inspector > 0 OR alt_inspector > 0)')
    orgs = one('SELECT COUNT(DISTINCT center_id) FROM networks')
    networks_n = one('SELECT COUNT(DISTINCT network) FROM networks WHERE network IS NOT NULL')
    multi_net = one('SELECT COUNT(*) FROM (SELECT center_id FROM networks '
                    'GROUP BY center_id HAVING COUNT(DISTINCT network) >= 2)')
    cash = one("SELECT SUM(amount) FROM transactions WHERE flow='دریافت' AND method='نقدی'")
    inkind = one("SELECT SUM(amount) FROM transactions WHERE flow='دریافت' AND method='غیرنقدی'")
    donors = one("SELECT COUNT(DISTINCT source) FROM transactions WHERE flow='دریافت' "
                 "AND source IS NOT NULL AND source != ''")
    donors_repeat = one("SELECT COUNT(*) FROM (SELECT source FROM transactions WHERE flow='دریافت' "
                        'AND source IS NOT NULL AND source != \'\' '
                        'GROUP BY source HAVING COUNT(DISTINCT year) >= 2)')
    csr = one('SELECT SUM(amount) FROM legal_donors')
    leaders = one("SELECT COUNT(*) FROM members WHERE role IS NOT NULL AND role != '' AND role != 'عضو'")
    members_all = one('SELECT COUNT(*) FROM members')
    models = one("SELECT COUNT(*) FROM centers WHERE medal IN ('پلاتین', 'طلا')")
    culture = one("SELECT COUNT(*) FROM transactions WHERE category LIKE '%جشن%' OR category LIKE '%نذر%' "
                  "OR category LIKE '%عاطفه%' OR category LIKE '%همایش%' OR category LIKE '%محرم%' "
                  "OR category LIKE '%رمضان%' OR category LIKE '%صدقات%'")
    fin_centers = one('SELECT COUNT(DISTINCT center_id) FROM transactions')
    req_total = one('SELECT COUNT(*) FROM requests')
    req_done = one("SELECT COUNT(*) FROM requests WHERE (process_status IS NOT NULL AND process_status != '') "
                   "OR (status IS NOT NULL AND status != '' AND status != 'در انتظار')")

    # درصد تکمیل اطلاعات مراکز و اعضا
    center_fields = ['license_no', 'name', 'province_id', 'office_id', 'chair', 'vice',
                     'exec_mgr', 'finance', 'inspector', 'center_type']
    member_fields = ['national_id', 'name', 'family', 'gender', 'role', 'status']
    fills = []
    for fld in center_fields:
        fills.append(one(f'SELECT COUNT(*) FROM centers WHERE [{fld}] IS NOT NULL '
                         f'AND CAST([{fld}] AS TEXT) != \'\'') / max(total_centers, 1))
    for fld in member_fields:
        fills.append(one(f'SELECT COUNT(*) FROM members WHERE [{fld}] IS NOT NULL '
                         f'AND CAST([{fld}] AS TEXT) != \'\'') / max(members_all, 1))
    completeness = round(sum(fills) / len(fills) * 100, 1) if fills else None

    years = [r[0] for r in c.execute('SELECT DISTINCT year FROM transactions '
                                     'WHERE year IS NOT NULL ORDER BY year')]

    def ind(key, area, label, value, unit, status='ok', source='', desc=''):
        return {'key': key, 'area': area, 'label': label, 'value': value, 'unit': unit,
                'status': status, 'source': source, 'desc': desc}

    indicators = [
        ind('licensed', 'توسعه مراکز', 'تعداد مراکز دارای مجوز معتبر', licensed, 'count',
            'ok', 'جدول مراکز', 'مراکز دارای شماره مجوز ثبت‌شده'),
        ind('active_real', 'توسعه مراکز', 'تعداد مراکز فعال واقعی', active_real, 'count',
            'ok', 'مراکز ∩ تراکنش‌ها',
            f"از {active_centers} مرکز با وضعیت «فعال»، {active_real} مرکز تراکنش ثبت‌شده دارند"),
        ind('geo_coverage', 'توسعه جغرافیایی', 'درصد پوشش مناطق هدف', pct(prov_covered, prov_total),
            'percent', 'proxy', 'تراکنش‌ها ÷ استان‌ها',
            f'{prov_covered} استان از {prov_total} استان دارای فعالیت ثبت‌شده'),
        ind('ranked', 'کیفیت مراکز', 'درصد مراکز دارای رتبه معتبر', pct(ranked, total_centers),
            'percent', 'proxy', 'جدول مراکز (امتیاز مرکب)', 'مراکزی که امتیاز اعتبارسنجی برای آن‌ها محاسبه شده است'),
        ind('full_board', 'کیفیت مراکز', 'درصد مراکز دارای ارکان مدیریتی کامل',
            pct(full_board, total_centers), 'percent', 'ok', 'جدول مراکز',
            'دارای رئیس، نایب‌رئیس، مسئول مالی و بازرس هم‌زمان'),
        ind('orgs', 'شبکه‌سازی', 'تعداد تشکل‌های شناسایی و ساماندهی‌شده', orgs, 'count',
            'ok', 'جدول شبکه‌سازی', 'مراکزی که در فایل شبکه‌سازی ثبت شده‌اند'),
        ind('networks_active', 'شبکه‌سازی', 'تعداد شبکه‌های تخصصی فعال', networks_n, 'count',
            'ok', 'جدول شبکه‌سازی', 'شبکه‌های تخصصی دارای عضو'),
        ind('net_projects', 'شبکه‌سازی', 'تعداد پروژه‌های مشترک شبکه‌ای', multi_net, 'count',
            'proxy', 'شبکه‌سازی', 'مراکز عضو حداقل دو شبکه تخصصی — ظرفیت همکاری بین‌شبکه‌ای'),
        ind('cash', 'جذب مشارکت', 'میزان منابع نقدی جذب‌شده', cash or 0, 'rial',
            'ok', 'تراکنش‌ها (دریافت نقدی)', 'جمع دریافت‌های نقدی ثبت‌شده در مراکز'),
        ind('inkind', 'جذب مشارکت', 'ارزش منابع غیرنقدی و خدمات', inkind or 0, 'rial',
            'ok', 'تراکنش‌ها (دریافت غیرنقدی)', 'جمع ارزش دریافت‌های غیرنقدی'),
        ind('donors', 'خیرین', 'تعداد نیکوکاران فعال و یکتا', donors, 'count',
            'proxy', 'ستون «منبع» دریافت‌ها', 'مقادیر یکتای منبع کمک در دریافت‌های ثبت‌شده'),
        ind('retention', 'نگهداشت خیرین', 'درصد تداوم مشارکت خیرین',
            pct(donors_repeat, donors), 'percent', 'proxy', 'دریافت‌ها در دو سال مختلف',
            'خیرینی که در حداقل دو سال دارای مشارکت بوده‌اند'),
        ind('csr', 'مسئولیت اجتماعی', 'میزان منابع جذب‌شده از شرکت‌ها و صنایع', csr or 0, 'rial',
            'proxy', 'جدول نیکوکاران حقوقی', 'جمع مشارکت‌های ثبت‌شده اشخاص حقوقی'),
        ind('leaders', 'توانمندسازی', 'تعداد مدیران و اعضای آموزش‌دیده', leaders, 'count',
            'proxy', 'کارتکس اعضا', f'مدیران دارای مسئولیت از {members_all} عضو؛ سوابق دوره‌های آموزشی ثبت نشده است'),
        ind('trained_centers', 'توانمندسازی', 'درصد مراکز برخوردار از آموزش‌های تخصصی', None,
            'percent', 'no_data', '—', 'نیازمند ثبت داده دوره‌های آموزشی مراکز در فایل‌های ورودی'),
        ind('models', 'الگوسازی', 'تعداد الگوهای موفق شناسایی و معرفی‌شده', models, 'count',
            'proxy', 'مدال‌های اعتبارسنجی', 'مراکز دارای مدال پلاتین یا طلا'),
        ind('culture', 'فرهنگ‌سازی', 'تعداد رویدادها و محصولات رسانه‌ای', culture, 'count',
            'proxy', 'فعالیت‌های ثبت‌شده', 'رکوردهای فعالیت‌های فرهنگی (جشن عاطفه‌ها، نذر و قربانی، صدقات و …)'),
        ind('fin_transparency', 'شفافیت', 'درصد مراکز دارای گزارش مالی تأییدشده',
            pct(fin_centers, total_centers), 'percent', 'proxy', 'تراکنش‌ها ÷ مراکز',
            'مراکزی که حداقل یک تراکنش مالی ثبت‌شده دارند'),
        ind('complaints', 'پاسخ‌گویی', 'درصد درخواست‌ها و شکایات رسیدگی‌شده',
            pct(req_done, req_total), 'percent', 'proxy', 'جدول درخواست‌ها',
            'درخواست‌های دارای وضعیت یا وضعیت فرآیندی مشخص'),
        ind('completeness', 'داده‌محوری', 'درصد تکمیل اطلاعات مراکز و اعضا', completeness,
            'percent', 'ok', 'فیلدهای کلیدی مراکز و اعضا', 'میانگین نسبت پر بودن فیلدهای اصلی'),
        ind('evaluated', 'ارزیابی', 'درصد مراکز ارزیابی‌شده در دوره مشخص',
            pct(medaled, total_centers), 'percent', 'proxy', 'مدال‌های اعتبارسنجی',
            'مراکزی که در نظام اعتبارسنجی مدال گرفته‌اند'),
    ]
    return jsonify({'indicators': indicators, 'years': years,
                    'computed_at': get_meta(c, 'imported_at') or ''})


# ───────────── عملکرد دوره‌ای: مقایسه دو سال (آیتم ۳) ─────────────

@bp.route('/api/performance')
@cached()
def performance():
    db = get_db_ext()
    args = request.args
    f_year = args.get('year', 'all')
    years = [r[0] for r in db.execute('SELECT DISTINCT year FROM transactions '
                                      'WHERE year IS NOT NULL ORDER BY year')]
    year1 = int(args.get('year1') or (f_year if f_year != 'all' else (years[-1] if years else 1404)))
    year2 = int(args['year2']) if args.get('year2') else None
    prov = args.get('province', 'all')
    office = args.get('office', 'all')

    # شرط پایه بدون سال (فیلتر استان/اداره) — برای همه پرس‌ها مشترک
    # مقادیر غیرعددی (مانند 'all') نادیده گرفته می‌شوند تا هرگز 500 ندهند
    base = ''
    base_p = []
    try:
        prov_id = int(prov)
    except (TypeError, ValueError):
        prov_id = None
    try:
        office_id = int(office)
    except (TypeError, ValueError):
        office_id = None
    if prov_id is not None:
        base += ' AND t.province_id = ?'
        base_p.append(prov_id)
    if office_id is not None:
        base += ' AND t.center_id IN (SELECT id FROM centers WHERE office_id = ?)'
        base_p.append(office_id)

    def scope(year):
        """WHERE کامل با سال برای سال مشخص"""
        return 't.year = ?' + base, [year] + base_p

    # ── بهینه‌سازی: همه تجمیع‌های دوساله با چند پرس GROUP BY unit-year انجام می‌شود
    # (قبلاً به‌ازای هر ماه × هر سال یک پرس جداگانه اجرا می‌شد) ──
    yl = [y for y in (year1, year2) if y is not None]
    year_tags = {year1: ['1']}
    if year2 is not None:
        year_tags.setdefault(year2, []).append('2')
    if yl:
        ph = ','.join('?' * len(yl))
        WY = f'WHERE t.year IN ({ph})' + base
        PY = list(yl) + base_p

        # روند ماهانه هر دو سال — یک پرس واحد
        mrows = {}
        for r in db.execute(
                'SELECT t.year y, t.month m, '
                "SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
                "SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec, "
                'SUM(t.beneficiaries) ben FROM transactions t '
                + WY + ' GROUP BY t.year, t.month', PY):
            mrows[(r['y'], r['m'])] = r
        months = []
        for m in range(1, 13):
            row = {'month': m}
            for tag, y in (('1', year1), ('2', year2)):
                r = mrows.get((y, m)) if y is not None else None
                if y is None:
                    row[f'pay{tag}'] = row[f'rec{tag}'] = row[f'ben{tag}'] = None
                else:
                    row[f'pay{tag}'] = (r['pay'] or 0) if r else 0
                    row[f'rec{tag}'] = (r['rec'] or 0) if r else 0
                    row[f'ben{tag}'] = (r['ben'] or 0) if r else 0
            months.append(row)

        # استان‌ها — یک پرس واحد
        prov_rows = {}
        for r in db.execute(
                "SELECT t.year y, p.name name, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
                "SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec, COUNT(*) cnt "
                'FROM transactions t LEFT JOIN provinces p ON p.id=t.province_id '
                + WY + ' GROUP BY t.year, p.name', PY):
            d = prov_rows.setdefault(r['name'] or 'نامشخص', {'name': r['name'] or 'نامشخص'})
            for tag in year_tags.get(r['y'], []):
                d[f'pay{tag}'] = r['pay'] or 0
                d[f'rec{tag}'] = r['rec'] or 0
                d[f'cnt{tag}'] = r['cnt']
        provinces = sorted(prov_rows.values(),
                           key=lambda d: -(d.get('pay1') or 0) - (d.get('pay2') or 0))[:15]

        # مراکز برتر — یک پرس واحد
        center_rows = {}
        for r in db.execute(
                "SELECT t.year y, c.name name, COALESCE(pp.name,'') prov, "
                "SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, COUNT(*) cnt "
                'FROM transactions t LEFT JOIN centers c ON c.id=t.center_id '
                'LEFT JOIN provinces pp ON pp.id=t.province_id '
                + WY + ' GROUP BY t.year, c.name, pp.name', PY):
            d = center_rows.setdefault(r['name'] or 'نامشخص',
                                       {'name': r['name'] or 'نامشخص', 'prov': r['prov']})
            for tag in year_tags.get(r['y'], []):
                d[f'pay{tag}'] = r['pay'] or 0
                d[f'cnt{tag}'] = r['cnt']
        centers = sorted(center_rows.values(),
                         key=lambda d: -(d.get('pay1') or 0) - (d.get('pay2') or 0))[:15]

        # نوع خدمت (فعالیت) — یک پرس واحد
        svc_rows = {}
        for r in db.execute(
                "SELECT t.year y, t.category label, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
                'COUNT(*) cnt FROM transactions t '
                + WY + ' AND t.category IS NOT NULL '
                'GROUP BY t.year, t.category', PY):
            d = svc_rows.setdefault(r['label'], {'label': r['label']})
            for tag in year_tags.get(r['y'], []):
                d[f'pay{tag}'] = r['pay'] or 0
                d[f'cnt{tag}'] = r['cnt']
        services = sorted(svc_rows.values(),
                          key=lambda d: -(d.get('pay1') or 0) - (d.get('pay2') or 0))[:12]

        # عملکرد حوزه‌ها (ادارات) — یک پرس واحد
        off_rows = {}
        for r in db.execute(
                "SELECT t.year y, COALESCE(o.name,'نامشخص') name, "
                "SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
                "SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec, "
                'COUNT(DISTINCT t.center_id) cnt '
                'FROM transactions t LEFT JOIN centers c ON c.id=t.center_id '
                'LEFT JOIN offices o ON o.id=c.office_id '
                + WY + ' GROUP BY t.year, o.name', PY):
            d = off_rows.setdefault(r['name'], {'name': r['name']})
            for tag in year_tags.get(r['y'], []):
                d[f'pay{tag}'] = r['pay'] or 0
                d[f'rec{tag}'] = r['rec'] or 0
                d[f'cnt{tag}'] = r['cnt']
        offices = sorted(off_rows.values(),
                         key=lambda d: -(d.get('pay1') or 0) - (d.get('pay2') or 0))[:40]
    else:
        months = [{'month': m, **{f'{k}{tag}': None for tag in ('1', '2') for k in ('pay', 'rec', 'ben')}}
                  for m in range(1, 13)]
        provinces, centers, services, offices = [], [], [], []

    # نیازمندان (برای سال‌وار نبودن داده نیازمندان، مقادیر کل با فیلتر استان گزارش می‌شود)
    # شرط استان یک‌بار و به‌صورت پارامتری ساخته می‌شود تا WHERE دوبله رخ ندهد
    try:
        prov_id = int(prov)
    except (TypeError, ValueError):
        prov_id = None
    prov_cond = 'n.province_id = ?' if prov_id is not None else '1=1'
    prov_params = (prov_id,) if prov_id is not None else ()
    needy_total = db.execute(
        f'SELECT COUNT(*) n FROM needy n WHERE {prov_cond}', prov_params).fetchone()['n']
    needy_by_prov = [dict(r) for r in db.execute(
        'SELECT p.name name, COUNT(*) cnt FROM needy n LEFT JOIN provinces p ON p.id=n.province_id '
        f'WHERE {prov_cond} GROUP BY p.name ORDER BY cnt DESC LIMIT 12', prov_params)]
    needy_by_type = [dict(r) for r in db.execute(
        f"SELECT COALESCE(n.need_type,'نامشخص') name, COUNT(*) cnt FROM needy n "
        f'WHERE {prov_cond} GROUP BY 1 ORDER BY cnt DESC LIMIT 8', prov_params)]
    needy_deciles = [dict(r) for r in db.execute(
        f'SELECT n.decile d, COUNT(*) cnt FROM needy n '
        f'WHERE {prov_cond} AND n.decile IS NOT NULL '
        'GROUP BY n.decile ORDER BY n.decile', prov_params)]

    # جمع کل هر سال
    def totals_for(y):
        if y is None:
            return {'pay': 0, 'rec': 0, 'ben': 0, 'cnt': 0}
        W, P = scope(y)
        r = db.execute(
            "SELECT SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
            "SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec, "
            'SUM(t.beneficiaries) ben, COUNT(*) cnt '
            f'FROM transactions t WHERE {W}', P).fetchone()
        return {'pay': r['pay'] or 0, 'rec': r['rec'] or 0,
                'ben': r['ben'] or 0, 'cnt': r['cnt']}

    t1, t2 = totals_for(year1), totals_for(year2)
    growth = round((t2['pay'] - t1['pay']) / t1['pay'] * 100, 1) if (year2 and t1['pay']) else None

    # رشد هر استان پس از تجمیع واحد محاسبه می‌شود
    for d in provinces:
        p1, p2 = d.get('pay1'), d.get('pay2')
        d['growth'] = round((p2 - p1) / p1 * 100, 1) if (p1 and p2 is not None) else None

    return jsonify({
        'years': years, 'year1': year1, 'year2': year2,
        'months': months, 'provinces': provinces, 'centers': centers,
        'services': services, 'offices': offices,
        'needy': {'total': needy_total, 'by_prov': needy_by_prov,
                  'by_type': needy_by_type, 'by_decile': needy_deciles},
        'totals': {'y1': t1, 'y2': t2, 'growth_pay': growth},
    })


# ───────────── گزارش اسلایدی عملکرد (آیتم ۶) ─────────────

@bp.route('/api/slide-report')
@cached()
def slide_report():
    db = get_db_ext()
    args = request.args
    years = [r[0] for r in db.execute('SELECT DISTINCT year FROM transactions '
                                      'WHERE year IS NOT NULL ORDER BY year')]
    latest_year = years[-1] if years else 1404
    year_raw = args.get('year', '')
    all_years_mode = (not year_raw) or year_raw == 'all'
    year = latest_year
    if not all_years_mode:
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            year = latest_year
            all_years_mode = True
    prov = args.get('province', 'all')
    office = args.get('office', 'all')
    scope_sql = ''
    try:
        prov_id = int(prov)
    except (TypeError, ValueError):
        prov_id = None
    try:
        office_id = int(office)
    except (TypeError, ValueError):
        office_id = None
    if prov_id is not None:
        scope_sql += f' AND t.province_id = {prov_id}'
    if office_id is not None:
        scope_sql += f' AND t.center_id IN (SELECT id FROM centers WHERE office_id = {office_id})'
    year_sql = '1=1' if all_years_mode else f't.year = {year}'
    W = f' WHERE {year_sql}' + scope_sql

    def one(sql):
        r = db.execute(sql).fetchone()
        return r[0] if r and r[0] is not None else 0

    # بهینه‌سازی: همهٔ اسکالرها در «یک» اسکن جدول تراکنش‌ها (به‌جای ۶ اسکن کامل)
    r0 = db.execute(
        'SELECT'
        " SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay,"
        " SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec,"
        ' COUNT(*) cnt_tx,'
        ' SUM(COALESCE(t.beneficiaries,0)) ben,'
        ' COUNT(DISTINCT t.center_id) centers_n,'
        " COUNT(DISTINCT CASE WHEN t.flow='دریافت' AND t.source IS NOT NULL AND t.source != '' THEN t.source END) donors_n"
        ' FROM transactions t' + W).fetchone()
    pay = r0['pay'] or 0
    rec = r0['rec'] or 0
    cnt_tx = r0['cnt_tx'] or 0
    ben = r0['ben'] or 0
    centers_n = r0['centers_n'] or 0
    donors_n = r0['donors_n'] or 0
    months = [dict(r) for r in db.execute(
        'SELECT t.month m, SUM(CASE WHEN t.flow=\'پرداخت\' THEN t.amount ELSE 0 END) pay, '
        "SUM(CASE WHEN t.flow='دریافت' THEN t.amount ELSE 0 END) rec "
        'FROM transactions t' + W + ' GROUP BY t.month ORDER BY t.month')]
    top_prov = [dict(r) for r in db.execute(
        "SELECT p.name name, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay "
        'FROM transactions t LEFT JOIN provinces p ON p.id=t.province_id' + W +
        ' GROUP BY p.name ORDER BY pay DESC LIMIT 8')]
    top_centers = [dict(r) for r in db.execute(
        "SELECT c.name name, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay, "
        'COUNT(*) cnt FROM transactions t LEFT JOIN centers c ON c.id=t.center_id' + W +
        ' GROUP BY c.name ORDER BY pay DESC LIMIT 10')]
    svc = [dict(r) for r in db.execute(
        "SELECT t.category name, SUM(CASE WHEN t.flow='پرداخت' THEN t.amount ELSE 0 END) pay "
        'FROM transactions t' + W + ' AND t.category IS NOT NULL GROUP BY t.category '
        'ORDER BY pay DESC LIMIT 8')]
    method_split = [dict(r) for r in db.execute(
        "SELECT t.method name, SUM(t.amount) pay FROM transactions t" + W +
        " AND t.flow='پرداخت' GROUP BY t.method ORDER BY pay DESC")]
    needy_n = one('SELECT COUNT(*) FROM needy WHERE ' +
                  (f'province_id = {prov_id}' if prov_id is not None else '1=1'))
    networks_n = one('SELECT COUNT(DISTINCT network) FROM networks')
    orgs_n = one('SELECT COUNT(DISTINCT center_id) FROM networks')
    prev_year = year - 1
    if all_years_mode:
        growth = None  # برای بازهٔ همه‌ساله، مقایسه با یک سال معنا ندارد
    else:
        prev_pay = one(f"SELECT SUM(amount) FROM transactions t WHERE t.year = {prev_year} AND t.flow='پرداخت'" + scope_sql)
        growth = round((pay - prev_pay) / prev_pay * 100, 1) if prev_pay else None

    # بهترین و ضعیف‌ترین ماه
    best_m = max(months, key=lambda r: r['pay'])['m'] if months else None
    weak_m = min(months, key=lambda r: r['pay'])['m'] if months else None
    MON = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
           'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']

    slides = []
    prov_name = ''
    if prov_id is not None:
        r = db.execute('SELECT name FROM provinces WHERE id = ?', (prov_id,)).fetchone()
        prov_name = r['name'] if r else ''
    off_name = ''
    if office_id is not None:
        r = db.execute('SELECT name FROM offices WHERE id = ?', (office_id,)).fetchone()
        off_name = r['name'] if r else ''
    scope_txt = ' — '.join(x for x in (prov_name, off_name) if x) or 'کل کشور'
    period_txt = 'همه سال‌ها' if all_years_mode else f'سال {year}'

    slides.append({'type': 'title', 'title': 'گزارش عملکرد شبکه مراکز نیکوکاری و توانمندسازی',
                   'subtitle': f'{period_txt} — {scope_txt}',
                   'badges': [f'{centers_n} مرکز فعال در دوره', f'{needy_n} نیازمند ثبت‌شده',
                              f'{cnt_tx} تراکنش']})
    slides.append({'type': 'kpi', 'title': 'اعداد کلیدی دوره',
                   'items': [
                       {'label': 'جمع پرداخت‌ها', 'value': pay, 'unit': 'rial'},
                       {'label': 'جمع دریافت‌ها', 'value': rec, 'unit': 'rial'},
                       {'label': 'ذی‌نفعان تحت پوشش', 'value': ben, 'unit': 'count'},
                       {'label': 'نیکوکاران فعال یکتا', 'value': donors_n, 'unit': 'count'},
                       {'label': 'مراکز دارای فعالیت', 'value': centers_n, 'unit': 'count'},
                       {'label': 'رشد نسبت به سال قبل', 'value': growth, 'unit': 'percent'},
                   ]})
    if months:
        slides.append({'type': 'chart', 'chart': 'line', 'title': 'روند ماهانه پرداخت و دریافت',
                       'labels': [MON[(r['m'] or 1) - 1] for r in months],
                       'series': [{'name': 'پرداخت', 'data': [r['pay'] for r in months]},
                                  {'name': 'دریافت', 'data': [r['rec'] for r in months]}],
                       'note': f'بیشترین پرداخت: {MON[(best_m or 1) - 1]} — کمترین: {MON[(weak_m or 1) - 1]}'})
    if top_prov:
        slides.append({'type': 'chart', 'chart': 'bar', 'title': 'استان‌های برتر (جمع پرداخت)',
                       'labels': [r['name'] or 'نامشخص' for r in top_prov],
                       'series': [{'name': 'پرداخت', 'data': [r['pay'] for r in top_prov]}]})
    if svc:
        slides.append({'type': 'chart', 'chart': 'donut', 'title': 'ترکیب نوع خدمت',
                       'data': [{'name': r['name'] or 'نامشخص', 'value': r['pay']} for r in svc]})
    if method_split:
        slides.append({'type': 'chart', 'chart': 'donut', 'title': 'سهم نقدی و غیرنقدی پرداخت‌ها',
                       'data': [{'name': r['name'] or 'نامشخص', 'value': r['pay']} for r in method_split]})
    if top_centers:
        slides.append({'type': 'table', 'title': 'مراکز برتر دوره',
                       'head': ['مرکز', 'جمع پرداخت (ریال)', 'تعداد تراکنش'],
                       'rows': [[r['name'] or 'نامشخص', r['pay'], r['cnt']] for r in top_centers]})
    # شاخص‌های جدول ۶-۲ برای همین دوره
    kpi_rows = []
    for r in db.execute("SELECT COUNT(*) n FROM centers WHERE license_no IS NOT NULL AND license_no != ''"):
        kpi_rows.append(['مراکز دارای مجوز معتبر', r['n']])
    kpi_rows.append(['مراکز فعال دارای تراکنش', centers_n])
    kpi_rows.append(['شبکه‌های تخصصی فعال', networks_n])
    kpi_rows.append(['تشکل‌های ساماندهی‌شده', orgs_n])
    kpi_rows.append(['نیکوکاران فعال یکتا', donors_n])
    slides.append({'type': 'table', 'title': 'شاخص‌های کلیدی ارزیابی (جدول ۶-۲)',
                   'head': ['شاخص', 'مقدار'], 'rows': kpi_rows})
    bullets = []
    if growth is not None:
        bullets.append(f"پرداخت‌های سال {year} نسبت به {prev_year} {'٪' + str(abs(growth)) + ' ' + ('رشد' if growth >= 0 else 'افت')} داشته است.")
    if best_m:
        bullets.append(f'اوج فعالیت مالی در {MON[(best_m or 1) - 1]} ثبت شده است؛ برنامه‌ریزی کمپین‌های فصلی بر همین الگو پیشنهاد می‌شود.')
    if top_prov:
        bullets.append(f"تمرکز جغرافیایی: {top_prov[0]['name']} با سهم قابل توجه از جمع پرداخت‌ها در صدر است؛ توصیه می‌شود مناطق کم‌برخوردار با پکیج حمایتی هدفمند پوشش داده شوند.")
    bullets.append('ادامه ثبت نظام‌مند داده‌ها (آموزش اعضا، پروژه‌های شبکه‌ای و گزارش مالی مراکز) برای تکمیل شاخص‌های ارزیابی ضروری است.')
    slides.append({'type': 'text', 'title': 'جمع‌بندی و پیشنهادها', 'bullets': bullets})

    return jsonify({'year': year, 'scope': scope_txt, 'slides': slides,
                    'generated_at': get_meta(db, 'imported_at') or ''})
