# -*- coding: utf-8 -*-
"""
واردکننده فایل‌های CSV واقعی سامانه نیکوکاری
- تشخیص خودکار کدگذاری (utf-8 / cp1256)
- نگاشت ستون‌ها با نام‌های مستعار برای ۲۵ اسکیمای شناخته‌شده
- نرمال‌سازی متن فارسی و ثبت گزارش کیفیت در import_log
"""
import io
import os
import re
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import constants as C
from db import connect, ensure_schema, set_meta
from norm import norm, norm_key, to_int, to_float, parse_jalali

AGG_DDL = """
CREATE TABLE IF NOT EXISTS agg_reports(
  id INTEGER PRIMARY KEY, source TEXT, province TEXT, city TEXT, center TEXT,
  flow TEXT, method TEXT, category TEXT, amount REAL, extra TEXT);
"""

# نام‌های مستعار ستون‌ها (پس از norm_key: بدون فاصله)
AL = {
    'province': ['استان'],
    'office': ['اداره', 'شهرستان', 'شهرستان', 'شهر ستان', 'ادارهشهرستان'],
    'center': ['مرکزنیکوکاریوتوانمندسازی', 'ناممرکزنیکوکاریوتوانمندسازی', 'مرکز', 'ناممرکز',
               'ناممرکزنیکوکاری', 'مرکزنیکوکاری', 'مرکزنیکوکاریتوانمندسازی'],
    'license': ['شمارهمجوز', 'شمارهمجوزمرکزنیکوکاریوتوانمندسازی', 'شناسهمرکز', 'کدمرکز',
                'شمارهمجوزمرکزنیکوکاریتوانمندسازی'],
    'national': ['کدملی', 'کدملي'],
    'mobile': ['شماره موبايل', 'موبايل', 'موبایل'],
    'name': ['نام'],
    'family': ['نام خانوادگی', 'نامخانوادگی'],
    'father': ['نام پدر'],
    'birth': ['تاریخ تولد', 'تاريخ تولد'],
    'gender': ['جنسيت', 'جنسیت'],
    'age': ['سن'],
    'decile': ['دهک'],
    'need_group': ['گروه نیازمندی', 'گروهنیازمندی'],
    'need_type': ['نوع نیازمند', 'نوعنیازمند'],
    'vital': ['وضعیت حیات', 'وضعيتحيات'],
    'status': ['وضعیت', 'وضعيتمرکزنیکوکاریتوانمندسازی', 'وضعیتمرکزنیکوکاریتوانمندسازی',
               'وضعیت عضو', 'وضعیتعضو'],
    'request_type': ['نوع درخواست', 'نوعدرخواست'],
    'tracking': ['شماره پیگیری', 'شمارهپیگیری', 'کد رهگیری', 'کدرهگیری', 'شناسه سند'],
    'creator': ['ایجادکننده', 'ایجادکننده', 'ثبت کننده', 'ثبتکننده'],
    'date': ['تاریخ ایجاد', 'تاریخثبت', 'تاریخ ثبت سند', 'تاریخ ثبت', 'تاريخ آخرين تغيير',
             'تاریخ ثبتسند'],
    'req_status': ['وضعیت درخواست', 'وضعیتدرخواست'],
    'process_status': ['وضعیت فرآیندی', 'وضعیتفرآیندی'],
    'amount': ['مبلغ', 'مبلغ کل', 'مبلغکل', 'جمع مبالغ تایید شده', 'جمعمبالغتاييده'],
    'flow': ['دریافت/پرداخت', 'دریافتپرداخت'],
    'method': ['کالا/نقدی', 'کالانقدي', 'کالا/نقدى'],
    'category': ['نام فعالیت', 'نامفعاليت', 'گروه فعالیت', 'گروهفعاليت', 'فعالیت'],
    'source': ['منبع', 'منبع مالی', 'منبعمالي'],
    'role': ['مسئولیت', 'مسئوليت'],
    'year': ['سال'],
    'month': ['ماه'],
    'pack_type': ['نوع پک', 'نوعپک'],
    'items': ['اقلام'],
    'donor': ['نام مرکز', 'نامنگهدارنده', 'نام نیکوکار'],
    'center_ok': ['تعداد مرکز نیکوکاری و توانمندسازی تایید شده'],
    'center_not': ['تعداد مرکز نیکوکاری و توانمندسازی تایید نشده'],
    'center_rev': ['تعداد مرکز نیکوکاری و توانمندسازی در دست بررسی'],
    'amount_not': ['جمع مبالغ تایید نشده'],
}


def col(df, key):
    """پیدا کردن ستون بر اساس نام‌های مستعار"""
    wanted = {norm_key(a) for a in AL[key]}
    for c in df.columns:
        if norm_key(c) in wanted:
            return c
    return None


def detect_encoding(path):
    raw = open(path, 'rb').read(60000)
    for enc in ('utf-8-sig', 'utf-8'):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return 'cp1256'


def read_csv(path):
    enc = detect_encoding(path)
    df = pd.read_csv(path, encoding=enc, dtype=str, keep_default_na=False,
                     encoding_errors='replace')
    df.columns = [norm(c) for c in df.columns]
    for c in df.columns:
        df[c] = df[c].map(norm)
    return df, enc


def get_or_create_province(conn, name):
    name = norm(name) or 'نامشخص'
    row = conn.execute('SELECT id FROM provinces WHERE name=?', (name,)).fetchone()
    if row:
        return row['id']
    conn.execute('INSERT INTO provinces(name) VALUES(?)', (name,))
    return conn.execute('SELECT id FROM provinces WHERE name=?', (name,)).fetchone()['id']


def get_or_create_office(conn, pid, name):
    name = norm(name) or 'اداره نامشخص'
    row = conn.execute('SELECT id FROM offices WHERE province_id=? AND name=?', (pid, name)).fetchone()
    if row:
        return row['id']
    conn.execute('INSERT INTO offices(province_id, name) VALUES(?,?)', (pid, name))
    return conn.execute('SELECT id FROM offices WHERE province_id=? AND name=?', (pid, name)).fetchone()['id']


def find_center(conn, license_no=None, name=None, pid=None):
    if license_no:
        row = conn.execute('SELECT id FROM centers WHERE license_no=?', (norm(license_no),)).fetchone()
        if row:
            return row['id']
    if name and pid:
        row = conn.execute('SELECT id FROM centers WHERE name=? AND province_id=?', (norm(name), pid)).fetchone()
        if row:
            return row['id']
    if name:
        row = conn.execute('SELECT id FROM centers WHERE name=? LIMIT 1', (norm(name),)).fetchone()
        if row:
            return row['id']
    return None


REQ_CATS = ('ثبت', 'دریافت', 'پرداخت', 'اداری')


def req_category(t):
    t = norm(t)
    if 'دریافت' in t:
        return 'دریافت'
    if 'پرداخت' in t or 'خرید کالا' in t:
        return 'پرداخت'
    if t.startswith('ثبت'):
        return 'ثبت'
    return 'اداری'


# ─────────────────────── handlers ───────────────────────

def imp_centers_new(conn, df, log):
    pc, oc, cc, lc = col(df, 'province'), col(df, 'office'), col(df, 'center'), col(df, 'license')
    role_cols = {}
    for key, label in [('chair', 'رئیس هیات امنا فعال'), ('vice', 'نایب رئیس فعال'),
                       ('exec_mgr', 'مدیر اجرایی فعال'), ('finance', 'مسئول مالی فعال'),
                       ('members', 'عضو فعال'), ('inspector', 'بازرس فعال'),
                       ('alt_inspector', 'علی البدل بازرس فعال'),
                       ('total_active', 'مجموع اعضای فعال'), ('total_inactive', 'مجموع اعضای غیر فعال')]:
        wanted = norm_key(label)
        for c in df.columns:
            if norm_key(c) == wanted:
                role_cols[key] = c
                break
    status_c = None
    for c in df.columns:
        if norm(c).startswith('وضعیت مرکز'):
            status_c = c
            break
    n, ins, upd = 0, 0, 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(pc, ''))
        oid = get_or_create_office(conn, pid, row.get(oc, ''))
        lic = norm(row.get(lc, '')) or None
        vals = {k: to_int(row.get(c, '0'), 0) for k, c in role_cols.items()}
        status = norm(row.get(status_c, '')) if status_c else 'فعال'
        existing = conn.execute('SELECT id FROM centers WHERE license_no=?', (lic,)).fetchone() if lic else None
        if existing:
            conn.execute('UPDATE centers SET name=?, province_id=?, office_id=?, status=?, chair=?, vice=?, '
                         'exec_mgr=?, finance=?, members=?, inspector=?, alt_inspector=?, total_active=?, '
                         'total_inactive=? WHERE id=?',
                         (norm(row.get(cc, '')), pid, oid, status,
                          vals.get('chair', 0), vals.get('vice', 0), vals.get('exec_mgr', 0),
                          vals.get('finance', 0), vals.get('members', 0), vals.get('inspector', 0),
                          vals.get('alt_inspector', 0), vals.get('total_active', 0),
                          vals.get('total_inactive', 0), existing['id']))
            upd += 1
        else:
            conn.execute('INSERT INTO centers(license_no, name, province_id, office_id, status, chair, vice, '
                         'exec_mgr, finance, members, inspector, alt_inspector, total_active, total_inactive) '
                         'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                         (lic, norm(row.get(cc, '')), pid, oid, status,
                          vals.get('chair', 0), vals.get('vice', 0), vals.get('exec_mgr', 0),
                          vals.get('finance', 0), vals.get('members', 0), vals.get('inspector', 0),
                          vals.get('alt_inspector', 0), vals.get('total_active', 0),
                          vals.get('total_inactive', 0)))
            ins += 1
        n += 1
    conn.commit()
    log['inserted'] = ins
    log['duplicates'] = upd
    return n


def imp_hamyaran(conn, df, log):
    keys = ['province', 'office', 'center', 'national', 'mobile', 'name', 'family', 'father',
            'gender', 'birth', 'status', 'license']
    cols = {k: col(df, k) for k in keys}
    n = 0
    rows = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        b = parse_jalali(row.get(cols['birth'], ''))
        age = 1405 - b[0] if b else None
        rows.append((norm(row.get(cols['national'], '')), norm(row.get(cols['mobile'], '')) or None,
                     norm(row.get(cols['name'], '')), norm(row.get(cols['family'], '')),
                     norm(row.get(cols['father'], '')) or None, norm(row.get(cols['gender'], '')) or None,
                     norm(row.get(cols['birth'], '')) or None, age, pid,
                     norm(row.get(cols['office'], '')), cid,
                     norm(row.get(cols['status'], '')) or None))
        n += 1
    conn.executemany('INSERT INTO hamyaran(national_id, mobile, name, family, father, gender, birth, age,'
                     ' province_id, office, center_id, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', rows)
    conn.commit()
    log['inserted'] = n
    return n


def imp_needy(conn, df, log, batch=20000):
    keys = ['province', 'office', 'center', 'license', 'national', 'name', 'family', 'birth',
            'need_group', 'mobile', 'vital', 'gender', 'age', 'decile', 'need_type']
    cols = {k: col(df, k) for k in keys}
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        dec = to_int(row.get(cols['decile'], ''))
        buf.append((norm(row.get(cols['national'], '')), norm(row.get(cols['name'], '')),
                    norm(row.get(cols['family'], '')), norm(row.get(cols['gender'], '')) or None,
                    norm(row.get(cols['birth'], '')) or None,
                    to_int(row.get(cols['age'], '')), pid, norm(row.get(cols['office'], '')),
                    cid, norm(row.get(cols['need_group'], '')) or None,
                    norm(row.get(cols['need_type'], '')) or None,
                    norm(row.get(cols['vital'], '')) or None, dec,
                    norm(row.get(cols['mobile'], '')) or None))
        n += 1
        if len(buf) >= batch:
            conn.executemany('INSERT INTO needy(national_id, name, family, gender, birth, age, province_id,'
                             ' office, center_id, need_group, need_type, vital, decile, mobile)'
                             ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
            buf = []
            conn.commit()
    if buf:
        conn.executemany('INSERT INTO needy(national_id, name, family, gender, birth, age, province_id,'
                         ' office, center_id, need_group, need_type, vital, decile, mobile)'
                         ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_requests(conn, df, log):
    keys = ['tracking', 'center', 'office', 'province', 'request_type', 'national', 'creator',
            'date', 'req_status', 'process_status']
    cols = {k: col(df, k) for k in keys}
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, None, row.get(cols['center']), pid)
        ym = parse_jalali(row.get(cols['date'], ''))
        t = norm(row.get(cols['request_type'], ''))
        buf.append((norm(row.get(cols['tracking'], '')) or str(int(time.time() * 1000) + n),
                    cid, pid, t, req_category(t), norm(row.get(cols['national'], '')) or None,
                    norm(row.get(cols['creator'], '')) or None,
                    norm(row.get(cols['date'], '')) or None,
                    ym[0] if ym else None, ym[1] if ym else None,
                    norm(row.get(cols['req_status'], '')) or None,
                    norm(row.get(cols['process_status'], '')) or None,
                    0.0, req_category(t)))
        n += 1
        if len(buf) >= 10000:
            conn.executemany('INSERT INTO requests(tracking_no, center_id, province_id, request_type,'
                             ' category, national_id, creator, date_j, year, month, status,'
                             ' process_status, amount, flow) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
            buf = []
            conn.commit()
    if buf:
        conn.executemany('INSERT INTO requests(tracking_no, center_id, province_id, request_type,'
                         ' category, national_id, creator, date_j, year, month, status,'
                         ' process_status, amount, flow) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_transactions(conn, df, log, flow=None, method=None, amount_col_key='amount'):
    """عمومی برای فایل‌های تراکنشی: پرداخت های نقدی/گروهی، دریافت ها، فعالیت و مرکز"""
    keys = ['tracking', 'province', 'office', 'center', 'license', 'amount', 'category',
            'source', 'national', 'name', 'family', 'flow', 'method', 'date']
    cols = {k: col(df, k) for k in keys}
    fc, mc = cols.get('flow'), cols.get('method')
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        f = flow or (norm(row.get(fc, '')) if fc else 'پرداخت')
        m = method or (norm(row.get(mc, '')) if mc else ('نقدی' if 'نقدی' in os.path.basename(log['filename']) else 'غیرنقدی'))
        cat = norm(row.get(cols['category'], '')) or None if cols['category'] else None
        src = norm(row.get(cols['source'], '')) or None if cols['source'] else None
        ym = parse_jalali(row.get(cols['date'], '')) if cols['date'] else None
        buf.append((norm(row.get(cols['tracking'], '')) or None, cid, pid, None,
                    ym[0] if ym else None, ym[1] if ym else None, f, m, cat, src,
                    to_float(row.get(cols['amount'], '0'), 0.0), None, None))
        n += 1
        if len(buf) >= 10000:
            conn.executemany('INSERT INTO transactions(tracking_no, center_id, province_id, date_j, year,'
                             ' month, flow, method, category, source, amount, beneficiaries, coverage)'
                             ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
            buf = []
            conn.commit()
    if buf:
        conn.executemany('INSERT INTO transactions(tracking_no, center_id, province_id, date_j, year,'
                         ' month, flow, method, category, source, amount, beneficiaries, coverage)'
                         ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_members_kartex(conn, df, log):
    keys = ['province', 'office', 'center', 'status', 'license', 'national', 'name', 'family',
            'role', 'mobile', 'gender', 'birth', 'age']
    cols = {k: col(df, k) for k in keys}
    inquiry = {}
    for c in df.columns:
        k = norm_key(c)
        mapping = {'بدهکار بانک': 'bank_debt', 'بدهکار مالیاتی': 'tax_debt', 'مددجوی بهزیستی': 'welfare',
                   'چک برگشتی': 'bounced_cheque', 'کارت پایان خدمت': 'military',
                   'استخدام دستگاه های دولتی': 'gov_emp', 'در قید حیات': 'alive', 'سوء پیشینه': 'criminal'}
        for src, dst in mapping.items():
            if k == norm_key(src):
                inquiry[dst] = c
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        b = parse_jalali(row.get(cols['birth'], ''))
        buf.append((cid, norm(row.get(cols['national'], '')) or None, norm(row.get(cols['name'], '')),
                    norm(row.get(cols['family'], '')), norm(row.get(cols['gender'], '')) or None,
                    norm(row.get(cols['birth'], '')) or None, to_int(row.get(cols['age'], '')),
                    None, None, norm(row.get(cols['role'], '')) or 'عضو',
                    norm(row.get(cols['status'], '')) or 'فعال',
                    *[norm(row.get(inquiry[d], '')) or None for d in
                      ('bank_debt', 'tax_debt', 'welfare', 'bounced_cheque', 'military', 'gov_emp', 'alive', 'criminal')]))
        n += 1
        if len(buf) >= 10000:
            conn.executemany('INSERT INTO members(center_id, national_id, name, family, gender, birth, age,'
                             ' education, job, role, status, bank_debt, tax_debt, welfare, bounced_cheque,'
                             ' military, gov_emp, alive, criminal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
            buf = []
            conn.commit()
    if buf:
        conn.executemany('INSERT INTO members(center_id, national_id, name, family, gender, birth, age,'
                         ' education, job, role, status, bank_debt, tax_debt, welfare, bounced_cheque,'
                         ' military, gov_emp, alive, criminal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_centers_kartex(conn, df, log):
    """کارتکس مراکز: به‌روزرسانی ویژگی‌های مرکز موجود"""
    keys = ['province', 'office', 'center', 'license']
    cols = {k: col(df, k) for k in keys}
    type_c = next((c for c in df.columns if norm_key(c) == norm_key('نوع فعالیت')), None)
    ur_c = next((c for c in df.columns if norm_key(c) == norm_key('شهری/روستایی')), None)
    own_c = next((c for c in df.columns if norm_key(c) == norm_key('مالکیت مکان')), None)
    area_c = next((c for c in df.columns if norm_key(c) == norm_key('متراژ')), None)
    st_c = next((c for c in df.columns if norm_key(c).startswith('وضعیت')), None)
    n, upd = 0, 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        if cid:
            conn.execute('UPDATE centers SET center_type=COALESCE(?, center_type), '
                         'urban_rural=COALESCE(?, urban_rural), ownership=COALESCE(?, ownership), '
                         'area=COALESCE(?, area), status=COALESCE(?, status) WHERE id=?',
                         (norm(row.get(type_c, '')) or None, norm(row.get(ur_c, '')) or None,
                          norm(row.get(own_c, '')) or None, to_int(row.get(area_c, '')),
                          norm(row.get(st_c, '')) or None, cid))
            upd += 1
        n += 1
    conn.commit()
    log['inserted'] = upd
    return n


NET_COLS = ['شبکه مردمی امر ازدواج', 'شبکه مردمی زیارت', 'شبکه مردمی وام قرض الحسنه',
            'شبکه مردمی امور فرهنگی و تحصیلی', 'شبکه مردمی تأمین لوازم ضروری زندگی',
            'شبکه مردمی تأمین مسکن', 'شبکه مردمی اشتغال و توانمندسازی',
            'شبکه مردمی ورزش و اوقات فراغت', 'شبکه مردمی وکلای نیکوکار', 'بهداشت و درمان']


def imp_networks(conn, df, log):
    keys = ['province', 'office', 'center', 'license']
    cols = {k: col(df, k) for k in keys}
    net_cols = {}
    for nc in NET_COLS:
        for c in df.columns:
            if norm_key(c) == norm_key(nc):
                net_cols[nc] = c
                break
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        if cid is None:
            continue
        for nc, c in net_cols.items():
            v = to_int(row.get(c, '0'), 0)
            if v:
                buf.append((cid, nc, v))
        n += 1
    if buf:
        conn.executemany('INSERT INTO networks(center_id, network, people) VALUES(?,?,?)', buf)
    conn.commit()
    log['inserted'] = len(buf)
    return n


def imp_packs(conn, df, log):
    ptc = col(df, 'pack_type')
    ac = col(df, 'category') or col(df, 'activity')
    sc = col(df, 'source')
    ic = col(df, 'items')
    conn.execute('DELETE FROM packs')
    n = 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        conn.execute('INSERT INTO packs(pack_type, activity, source, items) VALUES(?,?,?,?)',
                     (norm(row.get(ptc, '')), norm(row.get(ac, '')) if ac else '',
                      norm(row.get(sc, '')) if sc else '', norm(row.get(ic, '')) if ic else ''))
        n += 1
    conn.commit()
    log['inserted'] = n
    return n


def imp_legal_donors(conn, df, log):
    keys = ['province', 'center', 'name', 'national', 'amount']
    cols = {k: col(df, k) for k in keys}
    name_c = cols['name']
    for c in df.columns:
        if norm_key(c) not in ('استان', 'شهرستان') and 'مرکز' in norm_key(c) and not name_c:
            name_c = c
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, None, row.get(cols['center']), pid)
        buf.append((pid, cid, norm(row.get(name_c, '')) or 'نیکوکار حقوقی',
                    norm(row.get(cols['national'], '')) or None,
                    to_float(row.get(cols['amount'], '0'), 0.0), None))
        n += 1
    conn.executemany('INSERT INTO legal_donors(province_id, center_id, name, national_id, amount, year)'
                     ' VALUES(?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_finance_province(conn, df, log):
    """گزارش دریافت و پرداخت به تفکیک استان: ارقام واقعی به finance_province"""
    pc = col(df, 'province')
    conn.execute('DELETE FROM finance_province')
    n = 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(pc, ''))
        for c in df.columns:
            if c == pc:
                continue
            amt = to_float(row.get(c, ''), None)
            if amt is None:
                continue
            cat = norm(c)
            conn.execute('INSERT INTO finance_province(province_id, category, amount) VALUES(?,?,?)',
                         (pid, cat, amt))
            n += 1
    conn.commit()
    log['inserted'] = n
    return n


def imp_compensation(conn, df, log):
    pc = col(df, 'province')
    yc, mc = col(df, 'year'), col(df, 'month')
    okc, notc, revc = col(df, 'center_ok'), col(df, 'center_not'), col(df, 'center_rev')
    amokc, amnotc = col(df, 'amount'), col(df, 'amount_not')
    conn.execute('DELETE FROM compensation_province')
    n = 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(pc, ''))
        conn.execute('INSERT INTO compensation_province(province_id, year, month, centers_ok,'
                     ' centers_not_ok, centers_review, amount_ok, amount_not_ok) VALUES(?,?,?,?,?,?,?,?)',
                     (pid, to_int(row.get(yc, '0'), 0), to_int(row.get(mc, '0'), 0),
                      to_int(row.get(okc, '0'), 0), to_int(row.get(notc, '0'), 0),
                      to_int(row.get(revc, '0'), 0), to_float(row.get(amokc, '0'), 0.0),
                      to_float(row.get(amnotc, '0'), 0.0)))
        n += 1
    conn.commit()
    log['inserted'] = n
    return n


def imp_anomalies(conn, df, log, title):
    keys = ['province', 'center', 'tracking', 'date', 'amount', 'flow']
    cols = {k: col(df, k) for k in keys}
    desc_c = next((c for c in df.columns if norm_key(c) == norm_key('شرح سند')), None)
    n = 0
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid) if cols.get('license') else None
        conn.execute('INSERT INTO anomalies(province_id, center_id, doc_no, date_j, descr, flow, amount, title)'
                     ' VALUES(?,?,?,?,?,?,?,?)',
                     (pid, cid, norm(row.get(cols['tracking'], '')) or None,
                      norm(row.get(cols['date'], '')) or None,
                      norm(row.get(desc_c, '')) or None,
                      norm(row.get(cols['flow'], '')) or 'نامشخص',
                      to_float(row.get(cols['amount'], '0'), 0.0), title))
        n += 1
    conn.commit()
    log['inserted'] = n
    return n


def imp_agg(conn, df, log, source_name):
    """فایل‌های تجمیعی شناخته‌نشده دقیق → ذخیره عمومی"""
    pc, oc, cc = col(df, 'province'), col(df, 'office'), col(df, 'center')
    amount_c = col(df, 'amount')
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        buf.append((source_name, norm(row.get(pc, '')) if pc else None,
                    norm(row.get(oc, '')) if oc else None,
                    norm(row.get(cc, '')) if cc else None,
                    to_float(row.get(amount_c, ''), 0.0) if amount_c else None,
                    ' | '.join(f'{c}={norm(row.get(c, ""))}' for c in df.columns[:6])))
        n += 1
    if buf:
        conn.executemany('INSERT INTO agg_reports(source, province, city, center, amount, extra)'
                         ' VALUES(?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


def imp_general_report(conn, df, log):
    """گزارش کلی: اعضا با مسئولیت و کد مرکز"""
    keys = ['province', 'office', 'center', 'national', 'role', 'date', 'license']
    cols = {k: col(df, k) for k in keys}
    n = 0
    buf = []
    for r in df.itertuples(index=False):
        row = dict(zip(df.columns, r))
        pid = get_or_create_province(conn, row.get(cols['province'], ''))
        cid = find_center(conn, row.get(cols['license']), row.get(cols['center']), pid)
        b = parse_jalali(row.get(cols['date'], ''))
        buf.append((cid, norm(row.get(cols['national'], '')) or None, '', '', None,
                    norm(row.get(cols['date'], '')) or None,
                    (1405 - b[0]) if b else None, None, None,
                    norm(row.get(cols['role'], '')) or 'عضو', 'فعال',
                    None, None, None, None, None, None, None, None))
        n += 1
    conn.executemany('INSERT INTO members(center_id, national_id, name, family, gender, birth, age,'
                     ' education, job, role, status, bank_debt, tax_debt, welfare, bounced_cheque,'
                     ' military, gov_emp, alive, criminal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', buf)
    conn.commit()
    log['inserted'] = n
    return n


# ───────────── schema detection ─────────────

SCHEMA_RULES = [
    # (نام اسکیما, ستون‌های کلیدی الزامی, handler, kwargs)
    ('centers_new', ['province', 'office', 'center', 'license'] + [],
     imp_centers_new, {}),
    ('hamyaran', ['national', 'name', 'family', 'province'], imp_hamyaran, {}),
    ('needy', ['national', 'name', 'family', 'need_type', 'age'], imp_needy, {}),
    ('requests_report', ['tracking', 'request_type', 'province'], imp_requests, {}),
    ('payments_cash', ['amount', 'province', 'center'], imp_transactions,
     {'flow': 'پرداخت', 'method': 'نقدی'}),
    ('receipts', ['amount', 'province', 'center'], imp_transactions, None),
    ('activity_center', ['amount', 'center', 'flow'], imp_transactions, None),
    ('members_kartex', ['national', 'role', 'center'], imp_members_kartex, {}),
    ('centers_kartex', ['center', 'license', 'status'], imp_centers_kartex, {}),
    ('networks', ['center'], imp_networks, {}),
    ('packs', ['pack_type', 'items'], imp_packs, {}),
    ('legal_donors', ['province', 'center'], imp_legal_donors, {}),
    ('finance_province', ['province', 'amount'], imp_finance_province, {}),
    ('compensation', ['province', 'year', 'month', 'center_ok'], imp_compensation, {}),
    ('general_report', ['center', 'role', 'date'], imp_general_report, {}),
]


def classify(df, filename):
    """تشخیص اسکیما بر اساس نام فایل و ستون‌ها؛ خروجی (schema_name, handler, kwargs)"""
    fn = norm_key(os.path.basename(filename))
    name_hints = [
        ('new', 'centers_new', imp_centers_new, {}),
        ('hamyaran', 'hamyaran', imp_hamyaran, {}),
        ('niazmandan', 'needy', imp_needy, {}),
        ('پرداخت های نقدی', 'payments_cash', imp_transactions, {'flow': 'پرداخت', 'method': 'نقدی'}),
        ('پرداخت های گروهی نقدی', 'payments_group', imp_transactions, {'flow': 'پرداخت', 'method': 'نقدی'}),
        ('دریافت های غیر نقدی', 'receipts_inkind', imp_transactions, {'flow': 'دریافت', 'method': 'غیرنقدی'}),
        ('دریافت های نقدی', 'receipts_cash', imp_transactions, {'flow': 'دریافت', 'method': 'نقدی'}),
        ('فعالیت و مرکز', 'activity_center', imp_transactions, None),
        ('اعضای مراکز', 'members_kartex', imp_members_kartex, {}),
        ('کارتکس مراکز', 'centers_kartex', imp_centers_kartex, {}),
        ('شبکه سازی', 'networks', imp_networks, {}),
        ('تعریف پک', 'packs', imp_packs, {}),
        ('نیکوکاران حقوقی', 'legal_donors', imp_legal_donors, {}),
        ('به تفکیک استان', 'finance_province', imp_finance_province, {}),
        ('جبران خدمات به تفکیک', 'compensation', imp_compensation, {}),
        ('ثبت نشده', 'anomalies', imp_anomalies, {'title': 'تراکنش ثبت نشده'}),
        ('گزارش کلی', 'general_report', imp_general_report, {}),
        ('گزارش', 'requests_report', imp_requests, {}),
        ('report', 'requests_report', imp_requests, {}),
    ]
    for hint, schema, handler, kw in name_hints:
        if norm_key(hint) in fn:
            return schema, handler, (kw or {})
    # تشخیص بر اساس ستون‌ها
    best = (0, None, None, {})
    for schema, required, handler, kw in SCHEMA_RULES:
        present = sum(1 for k in required if col(df, k))
        if present > best[0]:
            best = (present, schema, handler, kw or {})
    if best[0] >= 2:
        return best[1], best[2], best[3]
    return None, None, {}


def import_file(conn, path, extra_log=None):
    """وارد کردن یک فایل CSV؛ خروجی: رکورد گزارش کیفیت"""
    t0 = time.time()
    df, enc = read_csv(path)
    schema, handler, kw = classify(df, os.path.basename(path))
    log = {'filename': os.path.basename(path), 'schema_name': schema or 'ناشناخته', 'encoding': enc,
           'rows_read': len(df), 'rows_inserted': 0, 'duplicates': 0,
           'nulls_pct': round(float(df.isin(['']).mean().mean()) * 100, 2),
           'warnings': '', 'imported_at': time.strftime('%Y-%m-%d %H:%M:%S')}
    if schema is None:
        imp_agg(conn, df, log, log['filename'])
        log['warnings'] = 'اسکیمای شناخته‌شده پیدا نشد؛ در جدول گزارش‌های عمومی ذخیره شد'
    else:
        if kw:
            handler(conn, df, log, **kw)
        else:
            handler(conn, df, log)
    conn.execute('INSERT INTO import_log(filename, schema_name, encoding, rows_read, rows_inserted,'
                 ' duplicates, nulls_pct, warnings, imported_at) VALUES(?,?,?,?,?,?,?,?,?)',
                 (log['filename'], log['schema_name'], log['encoding'], log['rows_read'],
                  log['inserted'], log['duplicates'], log['nulls_pct'], log['warnings'],
                  log['imported_at']))
    conn.commit()
    log['elapsed'] = round(time.time() - t0, 1)
    if extra_log:
        print(f"  {log['filename']} → {log['schema_name']} ({log['rows_read']:,} rows, {log['elapsed']}s)")
    return log


def import_directory(conn, dirpath, recompute_scores=True):
    """وارد کردن همه CSVهای یک پوشه"""
    ensure_schema(conn)
    conn.executescript(AGG_DDL)
    conn.execute('DELETE FROM import_log')
    conn.commit()
    logs = []
    files = sorted([f for f in os.listdir(dirpath) if f.lower().endswith('.csv')])
    print(f'Importing {len(files)} CSV files from {dirpath}')
    for f in files:
        try:
            logs.append(import_file(conn, os.path.join(dirpath, f), extra_log=True))
        except Exception as e:  # noqa
            conn.rollback()
            print(f'  ERROR in {f}: {e}')
            conn.execute('INSERT INTO import_log(filename, schema_name, encoding, rows_read,'
                         ' rows_inserted, duplicates, nulls_pct, warnings, imported_at)'
                         ' VALUES(?,?,?,?,?,?,?,?,?)',
                         (f, 'خطا', '-', 0, 0, 0, 0, str(e)[:300],
                          time.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    if recompute_scores:
        from generator import score_centers
        score_centers(conn)
    set_meta(conn, 'imported_at', str(int(time.time())))
    set_meta(conn, 'data_mode', 'real')
    return logs


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'upload')
    conn = connect()
    import_directory(conn, target)
    conn.close()
    print('Import finished.')
