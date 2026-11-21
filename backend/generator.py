# -*- coding: utf-8 -*-
"""
مولد داده نمونه وفادار به آمار واقعی گزارش تحلیل ۲۵ فایل CSV
همه توزیع‌ها (استان، سن، دهک، نوع نیازمند، درخواست‌ها، مبالغ مالی) از گزارش واقعی کالیبره شده‌اند.
"""
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import constants as C
from db import connect, ensure_schema, set_meta
from norm import norm

rng = np.random.default_rng(1405)
rnd = random.Random(1405)


def alloc_counts(total, fixed, weights):
    """تخصیص تعداد به گروه‌ها: مقادیر ثابت + بزرگترین باقیمانده برای بقیه"""
    out = dict(fixed)
    rest = total - sum(fixed.values())
    keys = [k for k in weights if k not in fixed]
    w = np.array([weights[k] for k in keys], dtype=float)
    w = w / w.sum()
    raw = w * rest
    base = np.floor(raw).astype(int)
    rem = rest - base.sum()
    order = np.argsort(-(raw - base))
    for i in order[:rem]:
        base[i] += 1
    for k, v in zip(keys, base):
        out[k] = int(v)
    return out


def pick_cat(probs):
    """نمونه‌برداری دسته‌ای با numpy"""
    keys = list(probs.keys())
    p = np.array([probs[k] for k in keys], dtype=float)
    p = p / p.sum()
    return keys, p


def sample_n(probs, n):
    keys, p = pick_cat(probs)
    return rng.choice(len(keys), size=n, p=p), keys


def date_str(y, m, d):
    return f'{y:04d}/{m:02d}/{d:02d}'


def month_len(y, m):
    if m <= 6:
        return 31
    if m <= 11:
        return 30
    return 30 if (y % 4 in (1, 2)) else 29


def person_names(genders):
    """نام و نام خانوادگی متناسب با جنسیت"""
    names = []
    for g in genders:
        pool = C.FEMALE_NAMES if g in ('خانم', 'مونث') else C.MALE_NAMES
        names.append((rnd.choice(pool), rnd.choice(C.FAMILY_NAMES)))
    return names


def gen_offices(conn):
    """ادارات: الگوهای واقعی «اداره ي شهر» / «اداره منطقه يک شهر» / «اداره شرق تهران...»"""
    offices = []
    for prov in C.PROVINCES:
        pid = conn.execute('SELECT id FROM provinces WHERE name=?', (prov,)).fetchone()['id']
        cities = C.CITIES.get(prov, [prov])
        n_off = min(len(cities) + 2, 10 if prov in ('تهران', 'خراسان رضوی') else 6)
        used = set()
        for city in cities[:n_off]:
            if prov == 'تهران' and city == 'تهران':
                variants = ['اداره غرب تهران (2-5-9-21-22)', 'اداره جنوب شرق تهران (12 و 13 و 14و 15)',
                            'اداره شرق تهران (6و7 و8)', 'اداره منطقه يک تهران', 'اداره منطقه دو تهران',
                            'اداره ي  ري', 'اداره شمال تهران (1و2 و3)']
            elif prov == 'البرز' and city == 'کرج':
                variants = ['اداره منطقه يک کرج', 'اداره منطقه دو کرج', 'اداره منطقه سه کرج']
            elif prov == 'خراسان رضوی' and city == 'مشهد':
                variants = ['اداره منطقه يک مشهد', 'اداره منطقه دو مشهد', 'اداره منطقه سه مشهد', 'اداره سبزوار']
            else:
                style = rnd.choice(['اداره ي %s', 'اداره %s', 'اداره منطقه يک %s', 'اداره ي  %s'])
                variants = [style % city]
            for v in variants:
                v = norm(v)
                if v not in used:
                    used.add(v)
                    offices.append((pid, v))
    conn.executemany('INSERT INTO offices(province_id, name) VALUES(?,?)', offices)
    return offices


def gen_centers(conn):
    counts = alloc_counts(C.TOTAL_CENTERS, C.CENTER_PROV_FIXED, C.CENTER_PROV_WEIGHTS)
    prov_rows = conn.execute('SELECT id, name FROM provinces').fetchall()
    pid_of = {r['name']: r['id'] for r in prov_rows}
    off_rows = conn.execute('SELECT id, province_id FROM offices').fetchall()
    offs_by_prov = {}
    for r in off_rows:
        offs_by_prov.setdefault(r['province_id'], []).append(r['id'])
    city_of_office = {}
    for r in conn.execute('SELECT id, name FROM offices').fetchall():
        city_of_office[r['id']] = r['name'].replace('اداره', '').replace('منطقه يک', '').replace(
            'منطقه دو', '').replace('منطقه سه', '').replace('ي', '').replace(' و ', ' ').strip()

    centers, license_no, seq = [], {}, {p: 1 for p in pid_of.values()}
    for prov, cnt in counts.items():
        pid = pid_of[prov]
        offs = offs_by_prov.get(pid, [])
        for _ in range(cnt):
            office_id = rnd.choice(offs)
            base = rnd.choice(C.CENTER_NAMES)
            if rnd.random() < 0.35:
                city = city_of_office.get(office_id, '')
                if city and rnd.random() < 0.5:
                    base = f'{base} {city}'
                else:
                    base = f'{base} ({rnd.randint(1, 5)})'
            chair = 1 if rng.random() < C.ROLE_FILL['رئیس هیات امنا'] else 0
            vice = int(rng.choice([0, 1, 1, 1, 2], p=[0.038, 0.92, 0.02, 0.02, 0.002]))
            execm = 1 if rng.random() < C.ROLE_FILL['مدیر اجرایی'] else 0
            fin = int(rng.choice([0, 1, 1, 1, 2], p=[0.019, 0.93, 0.03, 0.02, 0.001]))
            memb = int(rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                                  p=[0.198, 0.276, 0.373, 0.058, 0.011, 0.002, 0.016, 0.025, 0.005, 0.036]))
            insp = 1 if rng.random() < C.ROLE_FILL['بازرس'] else 0
            alt = 1 if rng.random() < C.ROLE_FILL['علی‌البدل بازرس'] else 0
            # مجموع اعضای فعال: میانگین 5.86 و میانه 7 (واقعی)
            extra = max(0, int(rng.normal(2.5, 1.2)))
            total_active = min(14, max(0, chair + vice + execm + fin + memb + insp + alt + extra))
            total_inactive = int(max(0, rng.gamma(1.6, 1.3)))
            lic = f'{pid % 90 + 10:02d}{seq[pid]:08d}'
            seq[pid] += 1
            centers.append((lic, base, pid, office_id, 'فعال', chair, vice, execm, fin, memb,
                            insp, alt, total_active, total_inactive,
                            rng.choice(['معیشتی', 'توانمندسازی', 'ترکیبی'], p=[0.45, 0.25, 0.30]),
                            rng.choice(['شهری', 'روستایی'], p=[0.72, 0.28]),
                            rng.choice(['استیجاری', 'ملکی', 'وقفی', 'دولتی'], p=[0.35, 0.4, 0.18, 0.07]),
                            int(rng.gamma(2.2, 60)), 0, '', 0))
            license_no[lic] = len(centers)
    conn.executemany(
        'INSERT INTO centers(license_no, name, province_id, office_id, status, chair, vice, exec_mgr,'
        ' finance, members, inspector, alt_inspector, total_active, total_inactive, center_type,'
        ' urban_rural, ownership, area, score, medal, created_year) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        [(c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9], c[10], c[11], c[12], c[13],
          c[14], c[15], c[16], c[17], c[18], c[19], c[20]) for c in centers])
    return counts


def gen_members(conn):
    """کارتکس اعضا: ۶۶٬۳۸۲ نفر با نقش‌ها و استعلامات"""
    centers = conn.execute(
        'SELECT id, chair, vice, exec_mgr, finance, members, inspector, alt_inspector, '
        'total_active, total_inactive FROM centers').fetchall()
    rows = []
    n = 0
    for c in centers:
        roles = ([('رئیس هیات امنا')] * c['chair'] + [('نایب رئیس')] * c['vice'] +
                 [('مدیر اجرایی')] * c['exec_mgr'] + [('مسئول مالی')] * c['finance'] +
                 [('عضو')] * c['members'] + [('بازرس')] * c['inspector'] +
                 [('علی‌البدل بازرس')] * c['alt_inspector'])
        extra_members = max(0, c['total_active'] - len(roles))
        roles += [('عضو')] * extra_members
        for role in roles:
            rows.append((c['id'], role, 'فعال'))
        for _ in range(c['total_inactive']):
            rows.append((c['id'], rnd.choice(['عضو', 'نایب رئیس', 'مسئول مالی', 'بازرس']), 'غير فعال'))
    edu_keys, edu_p = pick_cat(dict(C.EDUCATION))
    job_keys, job_p = pick_cat(dict(C.JOBS))
    ins_flags = ['ندارد', 'دارد']
    out = []
    for cid, role, status in rows:
        g = 'مذکر' if rng.random() < 0.58 else 'مونث'
        name, fam = person_names([g])[0]
        by = int(rng.integers(1338, 1380))
        age = 1405 - by
        out.append((cid, str(int(rng.integers(10 ** 8, 10 ** 10))).zfill(10), name, fam, g,
                    date_str(by, int(rng.integers(1, 13)), int(rng.integers(1, 29))),
                    age, edu_keys[int(rng.choice(len(edu_keys), p=edu_p))],
                    job_keys[int(rng.choice(len(job_keys), p=job_p))],
                    role, status,
                    ins_flags[0] if rng.random() < 0.93 else ins_flags[1],
                    ins_flags[0] if rng.random() < 0.96 else ins_flags[1],
                    ins_flags[0] if rng.random() < 0.99 else ins_flags[1],
                    ins_flags[0] if rng.random() < 0.95 else ins_flags[1],
                    'دارد' if rng.random() < 0.7 else 'ندارد',
                    ins_flags[0] if rng.random() < 0.94 else ins_flags[1],
                    'زنده' if rng.random() < 0.995 else 'فوت شده',
                    ins_flags[0] if rng.random() < 0.97 else ins_flags[1]))
    conn.executemany(
        'INSERT INTO members(center_id, national_id, name, family, gender, birth, age, education,'
        ' job, role, status, bank_debt, tax_debt, welfare, bounced_cheque, military, gov_emp,'
        ' alive, criminal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', out)
    return len(out)


def gen_hamyaran(conn):
    counts = alloc_counts(C.HAMYARAN_TOTAL, C.HAMYARAN_PROV_FIXED,
                          {p: 30 for p in C.PROVINCES})
    prov_rows = {r['name']: r['id'] for r in conn.execute('SELECT id, name FROM provinces')}
    offs = conn.execute('SELECT id, province_id, name FROM offices').fetchall()
    offs_by_prov = {}
    for r in offs:
        offs_by_prov.setdefault(r['province_id'], []).append(r)
    centers = conn.execute('SELECT id, province_id FROM centers').fetchall()
    c_by_prov = {}
    for r in centers:
        c_by_prov.setdefault(r['province_id'], []).append(r['id'])
    out = []
    for prov, cnt in counts.items():
        pid = prov_rows[prov]
        for _ in range(cnt):
            g = 'مذکر' if rng.random() < 0.58845 else 'مونث'
            name, fam = person_names([g])[0]
            off = rnd.choice(offs_by_prov[pid])
            by = int(rng.integers(1352, 1375))
            out.append((str(int(rng.integers(10 ** 8, 10 ** 10))).zfill(10),
                        '09' + str(int(rng.integers(10 ** 9, 10 ** 10)))[:9],
                        name, fam, rnd.choice(C.MALE_NAMES),
                        g, date_str(by, int(rng.integers(1, 13)), int(rng.integers(1, 29))),
                        1405 - by, pid, off['name'],
                        rnd.choice(c_by_prov[pid]) if c_by_prov[pid] else None,
                        'زنده' if rng.random() < C.HAMYARAN_ALIVE / 100 else 'فوت شده'))
    conn.executemany(
        'INSERT INTO hamyaran(national_id, mobile, name, family, father, gender, birth, age,'
        ' province_id, office, center_id, status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', out)
    return len(out)


def center_weights(conn):
    """وزن نیازمندی/تراکنش هر مرکز (دامنه طولانی - تمرکز واقعی)"""
    rows = conn.execute('SELECT id, province_id FROM centers').fetchall()
    cap = rng.lognormal(mean=0.4, sigma=1.15, size=len(rows))
    cap = np.maximum(cap, 0.05)
    w = {}
    for r, c in zip(rows, cap):
        w[r['id']] = (r['province_id'], float(c))
    return w


def assign_center(prov, weights_by_prov):
    ids, ws = weights_by_prov[prov]
    return int(rng.choice(ids, p=ws)) if len(ids) else None


def gen_needy(conn, scale=1.0):
    total = int(C.NEEDY_TOTAL * scale)
    counts = alloc_counts(total, {k: int(v * scale) for k, v in C.NEEDY_PROV_FIXED.items()},
                          {k: v for k, v in C.NEEDY_PROV_WEIGHTS.items() if v})
    prov_rows = {r['name']: r['id'] for r in conn.execute('SELECT id, name FROM provinces')}
    offs = conn.execute('SELECT province_id, name FROM offices').fetchall()
    offs_by_prov = {}
    for r in offs:
        offs_by_prov.setdefault(r['province_id'], []).append(r['name'])
    cw = center_weights(conn)
    w_by_prov = {}
    for cid, (pid, w) in cw.items():
        w_by_prov.setdefault(pid, [[], []])
        w_by_prov[pid][0].append(cid)
        w_by_prov[pid][1].append(w)
    for pid in w_by_prov:
        ws = np.array(w_by_prov[pid][1])
        w_by_prov[pid][1] = ws / ws.sum()
    ntype_idx, ntype_keys = sample_n(C.NEEDY_TYPE_DIST, total)
    gidx, gkeys = sample_n(C.NEEDY_GENDER, total)
    vidx, vkeys = sample_n(C.NEEDY_VITAL, total)
    didx, dkeys = sample_n(C.NEEDY_DECILE_DIST, total)
    ages = np.clip(rng.normal(C.NEEDY_AGE_MEAN, C.NEEDY_AGE_SD, total), 0, 110).round().astype(int)
    has_group = rng.random(total) < (C.NEEDY_GROUP_COVERAGE_PCT / 100)
    gr_idx, gr_keys = sample_n(C.NEEDY_GROUP_DIST, total)
    prov_list = [(prov_rows[p], p) for p in counts for _ in range(counts[p])]
    rng.shuffle(prov_list)
    genders = [gkeys[i] for i in gidx]
    names = person_names(genders)
    out = []
    for i in range(total):
        pid, prov = prov_list[i]
        g = genders[i]
        by = 1405 - int(ages[i])
        vital = vkeys[vidx[i]]
        decile = int(dkeys[didx[i]]) if rng.random() > C.NEEDY_DECILE_NULL_PCT / 100 else None
        group = gr_keys[gr_idx[i]] if has_group[i] else None
        mobile = '09' + str(int(rng.integers(10 ** 9, 10 ** 10)))[:9] if rng.random() > C.NEEDY_MOBILE_NULL_PCT / 100 else None
        out.append((str(int(rng.integers(10 ** 8, 10 ** 10))).zfill(10),
                    names[i][0], names[i][1], g,
                    date_str(by, int(rng.integers(1, 13)), int(rng.integers(1, 29))),
                    int(ages[i]), pid, rnd.choice(offs_by_prov[pid]),
                    assign_center(pid, w_by_prov), group, ntype_keys[ntype_idx[i]],
                    vital, decile, mobile))
    for chunk_start in range(0, total, 50000):
        conn.executemany(
            'INSERT INTO needy(national_id, name, family, gender, birth, age, province_id, office,'
            ' center_id, need_group, need_type, vital, decile, mobile) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            out[chunk_start:chunk_start + 50000])
    return total


def gen_transactions(conn, scale=1.0):
    """تراکنش‌های مالی نقدی/غیرنقدی + مجموع کل کالیبره‌شده به مبالغ واقعی"""
    cw = center_weights(conn)
    for cid in cw:
        pid, w = cw[cid]
        cw[cid] = (pid, float(w ** 1.9 + 0.02))
    w_by_prov = {}
    for cid, (pid, w) in cw.items():
        w_by_prov.setdefault(pid, [[], []])
        w_by_prov[pid][0].append(cid)
        w_by_prov[pid][1].append(w)
    # جرم هر استان از وزن خام (قبل از نرمال‌سازی درون‌استانی) محاسبه می‌شود
    prov_mass = {}
    for pid in w_by_prov:
        ws = np.array(w_by_prov[pid][1])
        prov_mass[pid] = float(ws.sum())
        w_by_prov[pid][1] = ws / ws.sum()
    offs = conn.execute('SELECT province_id, name FROM offices').fetchall()
    offs_by_prov = {}
    for r in offs:
        offs_by_prov.setdefault(r['province_id'], []).append(r['name'])

    specs = [
        ('پرداخت', 'نقدی', C.REAL_FINANCE['پرداخت نقدی'], C.CASH_PAY_ROWS, C.PAY_CASH_CATS, 82e6, 0.9),
        ('پرداخت', 'غیرنقدی', C.REAL_FINANCE['پرداخت غیرنقدی'], C.INKIND_PAY_ROWS, C.PAY_INKIND_CATS, 460e6, 1.3),
        ('دریافت', 'نقدی', C.REAL_FINANCE['دریافت نقدی'], C.CASH_RECV_ROWS, C.RECV_CASH_CATS, 319e6, 1.0),
        ('دریافت', 'غیرنقدی', C.REAL_FINANCE['دریافت غیرنقدی'], C.INKIND_RECV_ROWS, C.RECV_INKIND_CATS, 833e6, 1.5),
    ]
    year_list = ['1403', '1404', '1405']
    ys = np.array([C.YEAR_SHARES[y] for y in year_list])
    ys = ys / ys.sum()
    src_keys, src_p = pick_cat(dict(C.SOURCES))
    cov_keys, cov_p = pick_cat(C.NEEDY_TYPE_DIST)

    all_rows = []
    t0 = time.time()
    for flow, method, target_amount, n_rows, cats, med_amt, sigma in specs:
        n_rows = int(n_rows * scale)
        cat_keys, cat_p = pick_cat(dict(cats))
        rows_per_year = (ys * n_rows).astype(int)
        rows_per_year[-1] = n_rows - rows_per_year[:-1].sum()
        for yi, year in enumerate(year_list):
            ny = rows_per_year[yi]
            if ny <= 0:
                continue
            max_m = C.CURRENT_MONTH if year == '1405' else 12
            mw = np.array(C.MONTH_SEASON[:max_m])
            mw = mw / mw.sum()
            months = rng.choice(max_m, size=ny, p=mw) + 1
            amounts = rng.lognormal(mean=np.log(med_amt), sigma=sigma, size=ny)
            # مقیاس برای رسیدن دقیق به مبلغ هدف سال
            scale_f = (target_amount * C.YEAR_SHARES[year]) / amounts.sum()
            amounts = amounts * scale_f
            cat_s = rng.choice(len(cat_keys), size=ny, p=cat_p)
            src_s = rng.choice(len(src_keys), size=ny, p=src_p)
            cov_s = rng.choice(len(cov_keys), size=ny, p=cov_p)
            bens = np.maximum(1, np.round(amounts / (med_amt * 1.8) + rng.random(ny) * 2)).astype(int)
            # تخصیص استان متناسب با جرم مراکز همان استان (نامتوازن و واقع‌گرایانه)
            pids = sorted(prov_mass.keys())
            pw = np.array([prov_mass[p] for p in pids])
            pw = pw / pw.sum()
            provs = rng.choice(pids, size=ny, p=pw)
            for i in range(ny):
                y, m = int(year), int(months[i])
                d = int(rng.integers(1, month_len(y, m) + 1))
                pid = int(provs[i])
                all_rows.append((
                    '1' + str(int(rng.integers(10 ** 10, 10 ** 11))),
                    assign_center(pid, w_by_prov), pid, date_str(y, m, d), y, m,
                    flow, method, cat_keys[cat_s[i]], src_keys[src_s[i]],
                    float(amounts[i]), int(bens[i]) if method == 'غیرنقدی' or rng.random() < 0.5 else 1,
                    cov_keys[cov_s[i]]))
        print(f'  {flow} {method}: {n_rows:,} rows  ({time.time()-t0:.0f}s)')
    rng.shuffle(all_rows)
    for s in range(0, len(all_rows), 50000):
        conn.executemany(
            'INSERT INTO transactions(tracking_no, center_id, province_id, date_j, year, month,'
            ' flow, method, category, source, amount, beneficiaries, coverage)'
            ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', all_rows[s:s + 50000])
    return len(all_rows)


def gen_requests(conn, scale=1.0):
    total = int(C.REQUESTS_TOTAL * scale)
    counts = alloc_counts(total, {k: int(v * scale) for k, v in C.REQ_PROV_FIXED.items()},
                          {p: 60 for p in C.PROVINCES})
    prov_rows = {r['name']: r['id'] for r in conn.execute('SELECT id, name FROM provinces')}
    cw = center_weights(conn)
    w_by_prov = {}
    for cid, (pid, w) in cw.items():
        w_by_prov.setdefault(pid, [[], []])
        w_by_prov[pid][0].append(cid)
        w_by_prov[pid][1].append(w)
    for pid in w_by_prov:
        ws = np.array(w_by_prov[pid][1])
        w_by_prov[pid][1] = ws / ws.sum()
    cat_map = {}
    for t, cnt in C.REQ_TYPES:
        if 'دریافت' in t:
            cat_map[t] = ('دریافت', cnt)
        elif 'پرداخت' in t or t == 'خرید کالا':
            cat_map[t] = ('پرداخت', cnt)
        elif t.startswith('ثبت'):
            cat_map[t] = ('ثبت', cnt)
        else:
            cat_map[t] = ('اداری', cnt)
    t_keys = [t for t, _ in C.REQ_TYPES]
    t_p = np.array([cnt for _, cnt in C.REQ_TYPES], dtype=float)
    t_p = t_p / t_p.sum()
    st_keys, st_p = pick_cat(C.REQ_STATUS)
    ps_keys, ps_p = pick_cat(C.REQ_PROCESS)
    prov_list = []
    for p, cnt in counts.items():
        prov_list += [prov_rows[p]] * cnt
    rng.shuffle(prov_list)
    years = rng.choice([1404, 1405], size=total, p=[0.42, 0.58])
    out = []
    for i in range(total):
        t = t_keys[int(rng.choice(len(t_keys), p=t_p))]
        flow, _ = cat_map[t]
        y = int(years[i])
        m = int(rng.integers(1, (C.CURRENT_MONTH + 1) if y == 1405 else 13))
        d = int(rng.integers(1, month_len(y, m) + 1))
        pid = prov_list[i]
        amount = 0.0
        if flow == 'پرداخت':
            amount = float(rng.lognormal(np.log(120e6), 1.2))
        elif flow == 'دریافت':
            amount = float(rng.lognormal(np.log(200e6), 1.3))
        out.append((
            '1' + f'{14030 + i:09d}',
            assign_center(pid, w_by_prov), pid, t, flow,
            None if rng.random() < C.REQ_NATIONAL_NULL_PCT / 100 else str(int(rng.integers(10 ** 8, 10 ** 10))).zfill(10),
            str(int(rng.integers(10 ** 8, 10 ** 10))).zfill(10),
            date_str(y, m, d), y, m,
            st_keys[int(rng.choice(len(st_keys), p=st_p))],
            ps_keys[int(rng.choice(len(ps_keys), p=ps_p))],
            amount, flow))
    for s in range(0, total, 50000):
        conn.executemany(
            'INSERT INTO requests(tracking_no, center_id, province_id, request_type, category,'
            ' national_id, creator, date_j, year, month, status, process_status, amount, flow)'
            ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)', out[s:s + 50000])
    return total


def gen_networks(conn):
    centers = conn.execute('SELECT id FROM centers').fetchall()
    rows = []
    for c in centers:
        for net, p in C.NETWORKS:
            if rng.random() < p:
                rows.append((c['id'], net, int(rng.poisson(3) + 1)))
    conn.executemany('INSERT INTO networks(center_id, network, people) VALUES(?,?,?)', rows)
    return len(rows)


def gen_finance_province(conn):
    """جمع‌بندی مالی استانی با مجموع دقیق برابر ارقام واقعی فایل"""
    counts = dict(conn.execute(
        'SELECT p.name, COUNT(*) c FROM centers ce JOIN provinces p ON p.id=ce.province_id '
        'GROUP BY p.name').fetchall())
    weights = np.array([counts.get(n, 1) ** 0.92 for n in C.PROVINCES], dtype=float)
    intensity = rng.uniform(0.72, 1.32, 31)
    weights = weights * intensity
    weights = weights / weights.sum()
    rows = []
    for cat, total in C.REAL_FINANCE.items():
        if cat in ('جمع دریافت', 'جمع پرداخت', 'باقی مانده'):
            continue
        raw = weights * total
        base = np.floor(raw).astype(np.int64)
        rem = int(total - base.sum())
        frac = raw - base
        for i in np.argsort(-frac)[:rem]:
            base[i] += 1
        for prov, amt in zip(C.PROVINCES, base):
            pid = conn.execute('SELECT id FROM provinces WHERE name=?', (prov,)).fetchone()['id']
            rows.append((pid, cat, int(amt)))
    conn.executemany('INSERT INTO finance_province(province_id, category, amount) VALUES(?,?,?)', rows)
    return len(rows)


def gen_compensation(conn):
    """جبران خدمات به تفکیک استان (الگوی فایل واقعی: سال ۱۴۰۵ ماه ۶، مجموع ۴٬۱۱۲ مرکز تاییدشده)"""
    counts = dict(conn.execute(
        'SELECT province_id, COUNT(*) c FROM centers GROUP BY province_id').fetchall())
    rows = []
    total_ok, total_not, total_rev = 4112, 1640, 910
    w = np.array([counts.get(pid, 1) for pid in range(1, 32)], dtype=float)
    w = w / w.sum()
    ok = (w * total_ok).astype(int)
    ok[int(np.argmax(ok))] = 911
    not_ok = (w * total_not).astype(int)
    rev = (w * total_rev).astype(int)
    amount_ok = (w * 2.1e12).astype(np.int64)
    amount_not = (w * 0.42e12).astype(np.int64)
    for pid in range(1, 32):
        rows.append((pid, 1405, 6, int(ok[pid - 1]), int(not_ok[pid - 1]), int(rev[pid - 1]),
                     int(amount_ok[pid - 1]), int(amount_not[pid - 1])))
    conn.executemany(
        'INSERT INTO compensation_province(province_id, year, month, centers_ok, centers_not_ok,'
        ' centers_review, amount_ok, amount_not_ok) VALUES(?,?,?,?,?,?,?,?)', rows)
    return len(rows)


def gen_anomalies(conn):
    rows = []
    for i in range(22):
        pid = int(rng.integers(1, 32))
        rows.append((pid, None, f'90{i:04d}{int(rng.integers(100000, 999999))}',
                     date_str(1405, int(rng.integers(1, 9)), int(rng.integers(1, 29))),
                     'تراکنش ثبت نشده در سامانه', 'پرداخت' if i % 2 == 0 else 'دریافت',
                     float(rng.uniform(5e7, 2e9)),
                     'سند مالی بدون تراکنش بانکی متناظر'))
    conn.executemany(
        'INSERT INTO anomalies(province_id, center_id, doc_no, date_j, descr, flow, amount, title)'
        ' VALUES(?,?,?,?,?,?,?,?)', rows)
    return len(rows)


def gen_packs_and_donors(conn):
    conn.executemany('INSERT INTO packs(pack_type, activity, source, items) VALUES(?,?,?,?)', C.PACKS)
    centers = conn.execute(
        "SELECT id, province_id FROM centers WHERE province_id IN (SELECT id FROM provinces WHERE name IN ('آذربایجان شرقی','تهران','اصفهان','فارس','کرمان'))").fetchall()
    rows = []
    for i in range(110):
        c = centers[int(rng.integers(0, len(centers)))]
        rows.append((c['province_id'], c['id'], C.LEGAL_DONOR_NAMES[i % len(C.LEGAL_DONOR_NAMES)] +
                     f' ({i+1})', str(int(rng.integers(10 ** 9, 10 ** 10))).zfill(11)[:10],
                     float(rng.lognormal(np.log(8e9), 1.0)),
                     int(rng.choice([1403, 1404, 1405], p=[0.15, 0.45, 0.4]))))
    conn.executemany(
        'INSERT INTO legal_donors(province_id, center_id, name, national_id, amount, year)'
        ' VALUES(?,?,?,?,?,?)', rows)
    return len(C.PACKS), 110


def score_centers(conn):
    """امتیاز مرکب و مدال هر مرکز (پلاتین/طلا/نقره/برنز)"""
    centers = conn.execute('SELECT id, province_id, exec_mgr, finance, inspector, total_active, '
                           'total_inactive, members FROM centers').fetchall()
    pay = {r['center_id']: r['amt'] for r in conn.execute(
        "SELECT center_id, SUM(amount) amt FROM transactions WHERE flow='پرداخت' AND center_id IS NOT NULL GROUP BY center_id")}
    prov_avg = {}
    prov_n = {}
    for r in conn.execute("SELECT province_id, AVG(amount) a, COUNT(*) n FROM ("
                          "SELECT province_id, SUM(amount) amount FROM transactions WHERE flow='پرداخت' "
                          "GROUP BY center_id, province_id) GROUP BY province_id").fetchall():
        prov_avg[r['province_id']] = r['a']
    needy_prov = {r['province_id']: r['n'] for r in conn.execute(
        'SELECT province_id, COUNT(*) n FROM needy GROUP BY province_id').fetchall()}
    centers_prov = {r['province_id']: r['n'] for r in conn.execute(
        'SELECT province_id, COUNT(*) n FROM centers GROUP BY province_id').fetchall()}
    for r in centers:
        cid = r['id']
        structure = (r['exec_mgr'] + r['finance'] + r['inspector']) / 3
        activity = min(1.0, np.log1p(pay.get(cid, 0)) / np.log1p(max(prov_avg.get(r['province_id'], 1), 1)))
        burden = needy_prov.get(r['province_id'], 1) / max(centers_prov.get(r['province_id'], 1), 1)
        coverage = min(1.0, np.log1p(max(pay.get(cid, 0), 0)) / np.log1p(burden * 1.1e9))
        quality = 1 - min(1.0, r['total_inactive'] / max(r['total_active'] + r['total_inactive'], 1))
        score = round(100 * (0.22 * structure + 0.30 * activity + 0.28 * coverage + 0.10 * quality + 0.10 * min(1.0, r['total_active'] / 7)))
        medal = ('پلاتین' if score >= 90 else 'طلا' if score >= 80 else
                 'نقره' if score >= 70 else 'برنز' if score >= 60 else 'نیازمند بهبود')
        conn.execute('UPDATE centers SET score=?, medal=? WHERE id=?', (score, medal, cid))
    conn.commit()


def run(scale=1.0, db_path=None):
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(data_dir, exist_ok=True)
    t0 = time.time()
    conn = connect(db_path)
    ensure_schema(conn)
    conn.executescript('DELETE FROM provinces; DELETE FROM offices; DELETE FROM centers; '
                       'DELETE FROM members; DELETE FROM hamyaran; DELETE FROM needy; '
                       'DELETE FROM requests; DELETE FROM transactions; DELETE FROM networks; '
                       'DELETE FROM packs; DELETE FROM legal_donors; DELETE FROM finance_province; '
                       'DELETE FROM compensation_province; DELETE FROM anomalies; DELETE FROM import_log;')
    conn.execute('PRAGMA synchronous=OFF')
    for p in C.PROVINCES:
        conn.execute('INSERT INTO provinces(name) VALUES(?)', (p,))
    print('offices...');   offices = gen_offices(conn); conn.commit()
    print('centers...');   gen_centers(conn); conn.commit()
    print('members...');   n_m = gen_members(conn); conn.commit()
    print('hamyaran...');  gen_hamyaran(conn); conn.commit()
    print('needy...');     n_n = gen_needy(conn, scale); conn.commit()
    print('transactions...'); n_t = gen_transactions(conn, scale); conn.commit()
    print('requests...');  n_r = gen_requests(conn, scale); conn.commit()
    print('networks...');  gen_networks(conn); conn.commit()
    print('finance_prov...'); gen_finance_province(conn); conn.commit()
    print('compensation...'); gen_compensation(conn); conn.commit()
    print('anomalies...'); gen_anomalies(conn); conn.commit()
    print('packs/donors...'); gen_packs_and_donors(conn); conn.commit()
    print('scoring...');   score_centers(conn)
    set_meta(conn, 'generated_at', str(int(time.time())))
    set_meta(conn, 'data_mode', 'demo')
    set_meta(conn, 'scale', str(scale))
    set_meta(conn, 'rows', f'{n_m} members, {n_n} needy, {n_t} transactions, {n_r} requests')
    conn.commit()
    conn.close()
    print(f'DONE in {time.time()-t0:.1f}s  (scale={scale})')


if __name__ == '__main__':
    sc = 1.0
    if '--fast' in sys.argv:
        sc = 0.35
    run(scale=sc)
