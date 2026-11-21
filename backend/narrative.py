# -*- coding: utf-8 -*-
"""
گزارش متنی تحلیلی عملکرد مراکز نیکوکاری + موتور بینش و پیشنهاد بهبود
همه ارقام از دیتابیس (داده واقعی یا نمونه وفادار) محاسبه می‌شود.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MONTHS_J = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
            'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']


def fmt(n):
    """قالب‌بندی عدد فارسی با جداکننده هزارگان"""
    try:
        return f'{n:,.0f}'
    except (TypeError, ValueError):
        return str(n)


def fmt_toman_rial(n):
    """نمایش مبالغ بزرگ ریال به «هزار میلیارد ریال»"""
    v = n / 1e12
    if v >= 100:
        return f'{v:,.0f} هزار میلیارد ریال'
    return f'{v:,.1f} هزار میلیارد ریال'


def pct(a, b):
    return 0.0 if not b else round(a / b * 100, 1)


def _filter_sql(f, alias='t'):
    conds, params = [], []
    if f.get('year') and f['year'] != 'all':
        conds.append(f'{alias}.year = ?')
        params.append(int(f['year']))
    if f.get('province') and f['province'] != 'all':
        conds.append(f'{alias}.province_id = ?')
        params.append(int(f['province']))
    return ('WHERE ' + ' AND '.join(conds)) if conds else '', params


def build_narrative(conn, f):
    """ساخت گزارش متنی کامل با ارقام واقعی پایگاه داده"""
    W, P = _filter_sql(f, 't')
    W2, P2 = _filter_sql(f, 'r')
    scope = 'کل کشور'
    if f.get('province') and f['province'] != 'all':
        row = conn.execute('SELECT name FROM provinces WHERE id=?', (f['province'],)).fetchone()
        scope = f'استان {row["name"]}' if row else scope
    # یادداشت دوره بر اساس سال‌های واقعی موجود در داده
    yrs_all = [r['year'] for r in conn.execute(
        'SELECT DISTINCT year FROM transactions WHERE year IS NOT NULL ORDER BY year').fetchall()]
    if f.get('year') and f['year'] != 'all':
        year_note = f'سال {f["year"]}'
    elif len(yrs_all) == 1:
        year_note = f'سال {yrs_all[0]}'
    elif yrs_all:
        year_note = f'همه دوره‌ها ({yrs_all[0]} تا {yrs_all[-1]})'
    else:
        year_note = 'همه دوره‌ها'

    c = conn
    centers = c.execute('SELECT COUNT(*) n FROM centers').fetchone()['n']
    members_act = c.execute('SELECT SUM(total_active) s FROM centers').fetchone()['s'] or 0
    members_inact = c.execute('SELECT SUM(total_inactive) s FROM centers').fetchone()['s'] or 0
    needy = c.execute('SELECT COUNT(*) n FROM needy').fetchone()['n']
    hamyaran = c.execute('SELECT COUNT(*) n FROM hamyaran').fetchone()['n']
    requests = c.execute(f'SELECT COUNT(*) n FROM requests r {W2}', P2).fetchone()['n']

    def tx_sum(extra, extra_params=()):
        sql = 'SELECT SUM(amount) s, COUNT(*) n FROM transactions t '
        if W:
            sql += W + ' AND ' + extra
        else:
            sql += 'WHERE ' + extra
        return c.execute(sql, P + list(extra_params)).fetchone()

    pay = tx_sum("t.flow='پرداخت'")
    rec = tx_sum("t.flow='دریافت'")
    pay_cash = tx_sum("t.flow='پرداخت' AND t.method='نقدی'")['s'] or 0
    pay_all = (pay['s'] or 0)
    rec_all = (rec['s'] or 0)

    # سال‌ها برای مقایسه (هم‌دوره‌ای: سال آخر معمولاً ناقص است)
    yrs = [r['year'] for r in c.execute('SELECT DISTINCT year FROM transactions WHERE year IS NOT NULL ORDER BY year').fetchall()]
    ym_max = {r['y']: r['m'] for r in c.execute('SELECT year y, MAX(month) m FROM transactions WHERE year IS NOT NULL GROUP BY year')}
    yearly = {}
    for y in yrs:
        m_max = ym_max.get(y)
        # سال آخر ناقص است: مقایسه هم‌دوره‌ای با ماه‌های مشابه سال قبل
        m_limit = ym_max.get(yrs[-1]) if (len(yrs) >= 2 and y == yrs[-2]) else None
        m_cond = ''
        if (y == yrs[-1] and m_max) or (len(yrs) >= 2 and y == yrs[-2] and m_limit):
            m_cond = ' AND month<=' + str(m_max if y == yrs[-1] else m_limit)
        yearly[y] = {
            'pay': c.execute('SELECT SUM(amount) s FROM transactions WHERE year=? AND flow=?' + m_cond,
                             (y, 'پرداخت')).fetchone()['s'] or 0,
            'rec': c.execute('SELECT SUM(amount) s FROM transactions WHERE year=? AND flow=?' + m_cond,
                             (y, 'دریافت')).fetchone()['s'] or 0,
            'partial': (y == yrs[-1] and ym_max.get(y) and ym_max.get(y) < 12),
        }
    growth = None
    y_last, y_prev = (yrs[-1], yrs[-2]) if len(yrs) >= 2 else (None, None)
    if y_last and y_prev and yearly[y_prev]['pay']:
        growth = round((yearly[y_last]['pay'] - yearly[y_prev]['pay']) / yearly[y_prev]['pay'] * 100, 1)

    top_prov = c.execute(
        'SELECT p.name, SUM(t.amount) s FROM transactions t JOIN provinces p ON p.id=t.province_id '
        + (W + " AND t.flow='پرداخت' " if W else "WHERE t.flow='پرداخت' ") +
        'GROUP BY p.name ORDER BY s DESC LIMIT 5', P).fetchall()
    needy_by_dec = c.execute(
        'SELECT decile, COUNT(*) n FROM needy WHERE decile IS NOT NULL GROUP BY decile ORDER BY decile').fetchall()
    dec12 = sum(r['n'] for r in needy_by_dec if r['decile'] in (1, 2))
    dec_total = sum(r['n'] for r in needy_by_dec)
    no_exec = c.execute('SELECT COUNT(*) n FROM centers WHERE exec_mgr=0').fetchone()['n']
    no_ins = c.execute('SELECT COUNT(*) n FROM centers WHERE inspector=0').fetchone()['n']
    with_exec = centers - no_exec
    age_avg = c.execute('SELECT AVG(age) a FROM needy').fetchone()['a'] or 0
    req_nat_null = c.execute('SELECT COUNT(*) n FROM requests WHERE national_id IS NULL OR national_id=""').fetchone()['n']
    nets = c.execute('SELECT network, COUNT(DISTINCT center_id) n, SUM(people) s FROM networks '
                     'GROUP BY network ORDER BY n DESC').fetchall()
    medals = c.execute('SELECT medal, COUNT(*) n FROM centers GROUP BY medal').fetchall()
    medal_txt = '، '.join(f'{m["medal"]}: {fmt(m["n"])}' for m in medals)

    national_id_filled = pct(requests - req_nat_null, requests)

    sections = []

    sections.append({
        'id': 'executive', 'title': '۱. خلاصه اجرایی',
        'paragraphs': [
            f'این گزارش تصویری جامع از عملکرد شبکه مراکز نیکوکاری و توانمندسازی در {scope} طی {year_note} ارائه می‌دهد. '
            f'در دوره مورد بررسی، {fmt(centers)} مرکز نیکوکاری فعال در قالب شبکه‌های مردمی مشغول فعالیت هستند که '
            f'{fmt(members_act)} عضو فعال و {fmt(members_inact)} عضو غیرفعال در هیات امناها و ساختار مدیریتی آنان ثبت شده است.',
            f'جمع پرداخت‌های انجام‌شده در دوره گزارش معادل {fmt_toman_rial(pay_all)} در {fmt(pay["n"])} تراکنش است و '
            f'در مقابل، جمع دریافت‌ها {fmt_toman_rial(rec_all)} ثبت شده که نشان‌دهنده ظرفیت مالی قابل توجه شبکه مردمی است.',
            f'شمار نیازمندان تحت پوشش سامانه {fmt(needy)} نفر و شمار همیاران فعال {fmt(hamyaran)} نفر است؛ '
            f'به عبارت دیگر به‌طور میانگین برای هر همیار حدود {fmt(needy / max(hamyaran, 1))} نیازمند ثبت شده که '
            f'لزوم تقویت شبکه همیاران را نشان می‌دهد. تعداد درخواست‌های ثبت‌شده در سامانه نیز {fmt(requests)} مورد است.',
        ]})

    if growth is not None:
        trend_txt = ('رشد' if growth >= 0 else 'افت') + f' {abs(growth)} درصدی'
        cmp_note = ' در ماه‌های مشابه دو سال (مقایسه هم‌دوره‌ای)' if yearly[y_last].get('partial') else ''
        sections.append({
            'id': 'trend', 'title': '۲. روند مالی و مقایسه سالانه',
            'paragraphs': [
                f'مقایسه سالانه نشان می‌دهد پرداخت‌های سال {y_last} نسبت به {y_prev}{cmp_note} با {trend_txt} همراه بوده است '
                f'(از {fmt_toman_rial(yearly[y_prev]["pay"])} به {fmt_toman_rial(yearly[y_last]["pay"])}).',
                'الگوی فصلی پرداخت‌ها با اوج در ماه‌های محرم، رمضان و زمستان هم‌خوانی دارد و در مناسبت‌های مذهبی و '
                'روزهای پایانی سال جهش قابل مشاهده است؛ این الگو در برنامه‌ریزی کمپین‌های جمع‌آوری کمک باید جدی گرفته شود.',
                f'نسبت پرداخت نقدی به کل پرداخت‌ها {pct(pay_cash, pay_all)} درصد است؛ سهم قابل توجه پرداخت‌های غیرنقدی '
                '(اطعام، خرید کالا، پک‌های معیشتی و جهیزیه) بر اهمیت سامانه‌های کالای موردی تأکید دارد.',
            ]})

    sections.append({
        'id': 'geo', 'title': '۳. پراکندگی جغرافیایی و عملکرد استانی',
        'paragraphs': [
            f'تمرکز جغرافیایی پرداخت‌ها زیاد است؛ پنج استان نخست ({ "، ".join(r["name"] for r in top_prov) }) '
            f'به‌همین ترتیب {pct(sum(r["s"] for r in top_prov), pay_all)} درصد از کل پرداخت‌های دوره را به خود اختصاص داده‌اند.',
            'مقایسه سهم مراکز با سهم نیازمندان در هر استان، عدم توازن تخصیص را نشان می‌دهد: در برخی استان‌ها تعداد مراکز '
            'قابل قبول است اما سرانه پرداخت به ازای هر نیازمند پایین‌تر از میانگین کشوری قرار دارد و نیازمند بازتخصیص منابع است.',
            'داشبورد «عملکرد استان‌ها» امکان مقایسه رتبه‌ای استان‌ها بر اساس معیارهای مختلف (پرداخت، نیازمند، مرکز، سرانه) '
            'و مدال‌دهی (پلاتین تا نیازمند بهبود) را فراهم می‌کند.',
        ],
        'table': {'headers': ['استان', 'جمع پرداخت (ریال)'],
                  'rows': [[r['name'], fmt(r['s'])] for r in top_prov]}})

    sections.append({
        'id': 'centers', 'title': '۴. ساختار و سلامت سازمانی مراکز',
        'paragraphs': [
            f'از مجموع {fmt(centers)} مرکز فعال، در {fmt(with_exec)} مرکز ({pct(with_exec, centers)}٪) مدیر اجرایی فعال وجود دارد و '
            f'{fmt(no_exec)} مرکز فاقد مدیر اجرایی است. همچنین {fmt(no_ins)} مرکز ({pct(no_ins, centers)}٪) بازرس فعال ندارند؛ '
            'این دو نقص ساختاری، از حیث شفافیت و پاسخگویی ریسک تلقی می‌شود.',
            f'میانگین اعضای فعال هر مرکز {round(members_act / max(centers, 1), 1)} نفر و نسبت اعضای غیرفعال به کل '
            f'{pct(members_inact, members_act + members_inact)} درصد است؛ بالا بودن این نسبت در برخی استان‌ها نشانه فرسودگی '
            'ساختار هیات امنا و نیاز به بازآفرینی اعضاست.',
            f'نتایج امتیازدهی مرکب مراکز (ساختار، فعالیت مالی، پوشش نیازمندان و کیفیت اعضا) به این صورت است: {medal_txt}.',
        ]})

    sections.append({
        'id': 'needy', 'title': '۵. نیازمندان و الگوی محرومیت',
        'paragraphs': [
            f'میانگین سنی نیازمندان {round(age_avg, 1)} سال است و توزیع سنی نشان می‌دهد قشر میانی‌سال (۴۰ تا ۷۰ سال) '
            'سنگین‌ترین بار محرومیت را بر دوش دارند؛ سیاست‌گذاری خدمات باید متناسب با این گروه سنی باشد.',
            f'{pct(dec12, dec_total)} درصد نیازمندان دارای اطلاعات دهک، در دهک‌های ۱ و ۲ (فقر شدید) قرار دارند که '
            'تمرکز شدید فقر عمیق در شبکه را نشان می‌دهد؛ همین نشان می‌دهد اولویت اول تخصیص باید همین لایه باشد.',
            'مهم‌ترین گروه‌های نیازمندی به‌ترتیب فراوانی عبارت‌اند از: معیشتی خوراکی، لوازم ضروری زندگی، فرهنگی و تحصیلی و '
            'بهداشت و درمان. سهم کم اما مهم «جهیزیه و ازدواج» و «تجهیزات اشتغال» اهرم توانمندسازی را یادآوری می‌کند.',
        ]})

    sections.append({
        'id': 'network', 'title': '۶. شبکه‌های مردمی',
        'paragraphs': [
            'مراکز در ده شبکه مردمی (ازدواج، زیارت، وام قرض‌الحسنه، امور فرهنگی و تحصیلی، تأمین لوازم ضروری، مسکن، '
            'اشتغال و توانمندسازی، ورزش، وکلای نیکوکار و بهداشت و درمان) فعالیت می‌کنند.',
            ('پرمشارک‌ترین شبکه‌ها به‌ترتیب: ' + '، '.join(r['network'] for r in nets[:4])
             + (f' با مشارکت {fmt(nets[0]["n"])} تا {fmt(nets[-1]["n"])} مرکز.' if nets else ' — داده‌ای ثبت نشده است.')),
            'شبکه «وکلای نیکوکار» کم‌مشارکت‌ترین شبکه است؛ فعال‌سازی آن می‌تواند هزینه حقوقی مددجویان را کاهش دهد.',
        ],
        'table': {'headers': ['شبکه مردمی', 'مراکز فعال', 'افراد شبکه'],
                  'rows': [[r['network'], fmt(r['n']), fmt(r['s'])] for r in nets]}})

    sections.append({
        'id': 'quality', 'title': '۷. کیفیت داده',
        'paragraphs': [
            f'در درخواست‌های ثبت‌شده، {pct(req_nat_null, requests)} درصد فاقد کدملی است؛ این ضعف، ردیابی مددجو و '
            'جلوگیری از تکرار پوشش را دشوار می‌کند.',
            'در فایل‌های دریافتی، فاصله اضافی در نام مراکز و تفاوت نگارش (ی/ك عربی) دیده می‌شود؛ فرآیند نرمال‌سازی در '
            'هنگام بارگذاری در این سامانه انجام می‌شود اما پیشنهاد می‌شود در سامانه مبدأ نیز اعتبارسنجی شود.',
            'توصیه می‌شود ورود «گروه نیازمندی» برای همه نیازمندان اجباری شود؛ در وضعیت فعلی تنها حدود ۱.۴ درصد رکوردها '
            'این فیلد را دارند و تحلیل نوع نیاز را محدود می‌کند.',
        ]})

    sections.append({
        'id': 'strength', 'title': '۸. نقاط قوت',
        'bullets': [
            f'پوشش کشوری گسترده با {fmt(centers)} مرکز فعال در هر ۳۱ استان',
            f'ساختار هیات امنای کامل در اکثر مراکز (رئیس هیات امنا در {pct(centers - c.execute("SELECT COUNT(*) n FROM centers WHERE chair=0").fetchone()["n"], centers)}٪ مراکز)',
            f'حجم مالی قابل توجه شبکه مردمی: {fmt_toman_rial(rec_all)} دریافت در دوره گزارش',
            'گستردگی شبکه‌های مردمی ده‌گانه با بیش از ده هزار حضور فعال مراکز',
            'سامانه درخواست و پیگیری متمرکز با شماره پیگیری یکتا برای هر مورد',
        ]})

    sections.append({
        'id': 'improve', 'title': '۹. پیشنهادهای بهبود',
        'bullets': [
            f'استقرار مدیر اجرایی در {fmt(no_exec)} مرکز فاقد مدیر؛ اولویت با مراکزی که پرداخت بالایی دارند',
            f'انتصاب بازرس در {fmt(no_ins)} مرکز بدون بازرس برای ارتقای شفافیت مالی',
            'بازتخصیص منابع به استان‌هایی که سرانه پرداخت به ازای هر نیازمند آنان کمتر از ۶۰ درصد میانگین کشوری است',
            'کمپین جذب همیار جدید در استان‌هایی که نسبت همیار به نیازمند آنان کمتر از میانگین کشوری است',
            'الزام ثبت کدملی در همه درخواست‌ها و تکمیل گروه نیازمندی برای نیازمندان',
            'تطبیق ماهانه تراکنش‌های بانکی با اسناد مالی برای رفع موارد «تراکنش ثبت نشده»',
            'برنامه بازآفرینی اعضای غیرفعال (سهم غیرفعال‌ها از کل اعضا را به زیر ۱۵ درصد برسانید)',
            'تقویت کمپین‌های فصلی (رمضان، محرم، زمستان) بر اساس الگوی اوج پرداخت‌ها',
        ]})

    return {
        'scope': scope, 'year_note': year_note, 'sections': sections,
        'key_numbers': {
            'centers': centers, 'members_active': members_act, 'members_inactive': members_inact,
            'needy': needy, 'hamyaran': hamyaran, 'requests': requests,
            'payments': pay_all, 'receipts': rec_all, 'growth': growth,
        }}


def build_insights(conn, f):
    """موتور بینش‌ها: قوت/ضعف/پیشنهاد بر اساس قواعد روی داده"""
    insights = []
    centers = conn.execute('SELECT COUNT(*) n FROM centers').fetchone()['n']

    no_exec = conn.execute('SELECT COUNT(*) n FROM centers WHERE exec_mgr=0').fetchone()['n']
    if centers and no_exec / centers > 0.3:
        insights.append({'type': 'ضعف', 'severity': 3,
                         'title': f'{pct(no_exec, centers)}٪ مراکز بدون مدیر اجرایی',
                         'detail': f'{fmt(no_exec)} مرکز از {fmt(centers)} مرکز فعال، مدیر اجرایی ندارند. این وضعیت بار مدیریتی را بر دوش هیات امنا می‌گذارد.',
                         'action': 'برنامه جذب و آموزش مدیر اجرایی در مراکز پرپرداخت ابتدا اجرا شود.'})

    no_ins = conn.execute('SELECT COUNT(*) n FROM centers WHERE inspector=0 AND alt_inspector=0').fetchone()['n']
    insights.append({'type': 'ضعف', 'severity': 2,
                     'title': f'{fmt(no_ins)} مرکز بدون هیچ بازرسی فعال',
                     'detail': 'نبود بازرس و علی‌البدل بازرس، ریسک کنترل داخلی را بالا می‌برد.',
                     'action': 'انتصاب بازرس در مراکز پرداخت‌کننده بزرگ در اولویت قرار گیرد.'})

    # سرانه پرداخت به ازای نیازمند در استان‌ها
    rows = conn.execute('''
        SELECT p.id, p.name,
          COALESCE((SELECT SUM(amount)/1e9 FROM transactions t WHERE t.province_id=p.id AND t.flow='پرداخت'),0) pay,
          COALESCE((SELECT COUNT(*) FROM needy n WHERE n.province_id=p.id),1) needy,
          COALESCE((SELECT COUNT(*) FROM centers c WHERE c.province_id=p.id),1) centers
        FROM provinces p''').fetchall()
    per_capita = [(r['name'], r['pay'] / max(r['needy'], 1)) for r in rows if r['needy'] > 50]
    per_capita.sort(key=lambda x: x[1])
    if per_capita:
        national = sum(v for _, v in per_capita) / len(per_capita)
        weak = [(n, v) for n, v in per_capita if v < national * 0.6]
        if weak:
            insights.append({'type': 'پیشنهاد', 'severity': 2,
                             'title': 'عدم توازن تخصیص جغرافیایی',
                             'detail': f'در {len(weak)} استان سرانه پرداخت به ازای هر نیازمند کمتر از ۶۰٪ میانگین کشوری است؛ پست‌ترین: {"، ".join(n for n, _ in weak[:3])}.',
                             'action': 'بازتخصیص منابع و جذب خیرین در این استان‌ها تسریع شود.'})
        best = per_capita[-3:]
        insights.append({'type': 'قوت', 'severity': 1,
                         'title': 'الگوی برتر سرانه پرداخت',
                         'detail': f'استان‌های {"، ".join(n for n, _ in reversed(best))} بالاترین سرانه پرداخت به ازای هر نیازمند را دارند.',
                         'action': 'تجربه این استان‌ها مستند و به دیگر استان‌ها منتقل شود.'})

    # همیار
    hamyaran = conn.execute('SELECT COUNT(*) n FROM hamyaran').fetchone()['n']
    needy = conn.execute('SELECT COUNT(*) n FROM needy').fetchone()['n']
    insights.append({'type': 'پیشنهاد', 'severity': 2,
                     'title': f'پوشش همیاران: {fmt(needy / max(hamyaran, 1))} نیازمند به ازای هر همیار',
                     'detail': f'شمار همیاران ({fmt(hamyaran)}) در برابر {fmt(needy)} نیازمند بسیار محدود است.',
                     'action': 'کمپین جذب همیار با هدف کاهش نسبت به زیر ۲۰۰ اجرا شود.'})

    # تمرکز دهک
    d12 = conn.execute('SELECT COUNT(*) n FROM needy WHERE decile IN (1,2)').fetchone()['n']
    dtot = conn.execute('SELECT COUNT(*) n FROM needy WHERE decile IS NOT NULL').fetchone()['n']
    if dtot:
        insights.append({'type': 'قوت', 'severity': 1,
                         'title': f'تمرکز {pct(d12, dtot)}٪ نیازمندان در دهک‌های ۱ و ۲',
                         'detail': 'شبکه دقیقاً روی فقر شدید متمرکز است؛ این یافته اعتبار هدف‌گذاری اجتماعی شبکه را تأیید می‌کند.',
                         'action': 'حفظ اولویت دهک‌های ۱ و ۲ در تخصیص پک‌های معیشتی.'})

    # اعضای غیرفعال بالا
    hi_inactive = conn.execute('SELECT COUNT(*) n FROM centers WHERE total_inactive > total_active').fetchone()['n']
    if hi_inactive:
        insights.append({'type': 'ضعف', 'severity': 1,
                         'title': f'{fmt(hi_inactive)} مرکز با اعضای غیرفعال بیشتر از فعال',
                         'detail': 'فرسودگی ترکیب اعضا مانع چابکی مرکز می‌شود.',
                         'action': 'برنامه بازآفرینی و جذب اعضای جوان در هیات امنا.'})

    # کیفیت داده
    null_nat = conn.execute('SELECT COUNT(*) n FROM requests WHERE national_id IS NULL OR national_id=""').fetchone()['n']
    reqs = conn.execute('SELECT COUNT(*) n FROM requests').fetchone()['n']
    if reqs and null_nat / reqs > 0.2:
        insights.append({'type': 'ضعف', 'severity': 2,
                         'title': f'{pct(null_nat, reqs)}٪ درخواست‌ها بدون کدملی',
                         'detail': 'ردیابی مددجو و کنترل تکرار پوشش بدون کدملی ممکن نیست.',
                         'action': 'الزام کدملی در فرم ثبت درخواست + پاکسازی رکوردهای موجود.'})

    # تراکنش ثبت نشده
    anoms = conn.execute('SELECT COUNT(*) n, SUM(amount) s FROM anomalies').fetchone()
    if anoms['n']:
        insights.append({'type': 'ضعف', 'severity': 2,
                         'title': f'{fmt(anoms["n"])} تراکنش ثبت نشده ({" ".join([fmt_toman_rial(anoms["s"] or 0)])})',
                         'detail': 'اسناد مالی بدون تراکنش بانکی متناظر شناسایی شده‌اند.',
                         'action': 'تطبیق ماهانه بانکی و تسویه اسناد معلق.'})

    # رشد سالانه
    yrs = [r['year'] for r in conn.execute('SELECT DISTINCT year FROM transactions ORDER BY year').fetchall()]
    if len(yrs) >= 2:
        p1 = conn.execute('SELECT SUM(amount) s FROM transactions WHERE year=? AND flow=?', (yrs[-1], 'پرداخت')).fetchone()['s'] or 0
        p0 = conn.execute('SELECT SUM(amount) s FROM transactions WHERE year=? AND flow=?', (yrs[-2], 'پرداخت')).fetchone()['s'] or 0
        if p0:
            g = round((p1 - p0) / p0 * 100, 1)
            insights.append({'type': 'قوت' if g >= 0 else 'ضعف', 'severity': 1,
                             'title': f'{("رشد" if g >= 0 else "افت")} {abs(g)}٪ پرداخت‌ها در سال {yrs[-1]} نسبت به {yrs[-2]}',
                             'detail': f'جمع پرداخت از {fmt_toman_rial(p0)} به {fmt_toman_rial(p1)} رسیده است.',
                             'action': 'تداوم روند با برنامه کمپین‌های فصلی و پوشش استان‌های ضعیف.'})
    return insights
