import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Loading, ErrorBox, faNum, faNum1, money, InsightCard,
} from '../components/ui.jsx'

// ─── گزارش عملکرد اداره کل امور اجرایی مشارکت‌های مردمی — بر پایه فصل ششم ───

const PROGRAMS_63 = [
  'تهیه نقشه پوشش مراکز به تفکیک استان، شهرستان و محله',
  'شناسایی مناطق فاقد مرکز مؤثر یا دارای دسترسی محدود',
  'بررسی ظرفیت مؤسسان، داوطلبان و خیرین محلی',
  'جلوگیری از ایجاد مراکز موازی بدون نیازسنجی',
  'تدوین برنامه پشتیبانی آغاز فعالیت برای مراکز جدید',
  'تعیین وضعیت مراکز موجود در چهار گروه ثبت‌شده، فعال، کم‌فعال و نیازمند اصلاح',
  'تفکیک آمار مجوزهای صادرشده از تعداد مراکز فعال',
]

const TABLE_61 = [
  ['اداره مرکز', 'تعیین مسئولیت‌ها، تنظیم برنامه و ثبت تصمیم‌ها'],
  ['مالی', 'ثبت منابع و مصارف، نگهداری اسناد و تطبیق حساب‌ها'],
  ['نیازسنجی', 'بررسی وضعیت و ارجاع نیازهای تخصصی به حوزه مربوط'],
  ['جذب خیر', 'آموزش مذاکره، معرفی پروژه و ارتباط محلی'],
  ['خدمت‌رسانی', 'رعایت اولویت نیاز و استاندارد خدمت'],
  ['داده', 'ثبت صحیح، به‌روز و بدون دوباره‌شماری'],
  ['پاسخ‌گویی', 'رسیدگی به درخواست‌ها و شکایات'],
  ['توانمندسازی', 'توسعه خدمات مهارتی، اشتغال و آموزشی'],
  ['حفاظت', 'رعایت محرمانگی و کرامت مددجویان'],
]

const AREA_ORDER = ['توسعه مراکز', 'توسعه جغرافیایی', 'کیفیت مراکز', 'شبکه‌سازی', 'جذب مشارکت',
  'خیرین', 'نگهداشت خیرین', 'مسئولیت اجتماعی', 'توانمندسازی', 'الگوسازی', 'فرهنگ‌سازی',
  'شفافیت', 'پاسخ‌گویی', 'داده‌محوری', 'ارزیابی']

const STATUS_BADGE = {
  ok: { label: 'محاسبه‌شده', cls: 'q' },
  proxy: { label: 'تقریبی از داده موجود', cls: 's' },
  no_data: { label: 'نیازمند داده تکمیلی', cls: 'w' },
}

export default function Chapter6() {
  const { filters } = useFilters()
  const [kpi, setKpi] = useState(null)
  const [perf, setPerf] = useState(null)
  const [ins, setIns] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.kpi21().then(setKpi).catch(setErr)
    api.performance({ year1: filters.year !== 'all' ? filters.year : '' })
      .then(setPerf).catch(() => {})
    api.insights(filters).then(setIns).catch(() => {})
  }, [filters])

  if (err && !kpi) return <ErrorBox err={err} />
  if (!kpi) return <Loading />

  const inds = kpi.indicators || []
  const byArea = {}
  for (const a of AREA_ORDER) byArea[a] = inds.filter((x) => x.area === a)
  const remaining = inds.filter((x) => !AREA_ORDER.includes(x.area))
  if (remaining.length) byArea['سایر'] = remaining

  const yearLabel = perf?.year1 || '—'
  const pay = perf?.totals?.y1?.pay
  const rec = perf?.totals?.y1?.rec
  const ben = perf?.totals?.y1?.ben
  const needyTotal = perf?.needy?.total

  const fmtVal = (i) => {
    if (i.value === null || i.value === undefined) return '—'
    if (i.unit === 'rial') return money(i.value)
    if (i.unit === 'percent') return `${faNum1(i.value)}٪`
    return faNum(i.value)
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ color: 'var(--acc)', marginBottom: 10 }}>
          گزارش عملکرد اداره کل امور اجرایی مشارکت‌های مردمی
        </h3>
        <p style={{ lineHeight: 2.1, fontSize: '.95rem', color: 'var(--text2)' }}>
          <b>مأموریت:</b> راهبری توسعه کمی و کیفی مراکز نیکوکاری و ساماندهی تعامل با تشکل‌های مردمی،
          به‌منظور گسترش شبکه‌ای مستقل، مسئولیت‌پذیر، توانمند و پاسخ‌گو در خدمت‌رسانی به نیازمندان.
          بر اساس تعریف برنامه هفتم، مرکز نیکوکاری تشکل مردمی مستقلی است که با مجوز کمیته امداد و در
          چارچوب قوانین و نظارت عالیه آن فعالیت می‌کند؛ بنابراین توسعه مراکز باید بر تقویت ظرفیت
          مردمی استوار باشد، نه تبدیل آن‌ها به واحدهای اداری وابسته.
        </p>
        <div className="row-flex" style={{ flexWrap: 'wrap', marginTop: 8 }}>
          <span className="badge">مستندهای برنامه‌ای: احکام ۲۱، ۲۲، ۲۳، ۳۱، ۳۲، ۳۵، ۳۸ و ۴۵</span>
          <span className="badge">سیاست‌های ۵، ۷ و ۸</span>
          <span className="badge">دوره گزارش: سال {faNum(yearLabel)}</span>
        </div>
      </div>

      <div className="grid g2">
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 8 }}>هدف اول — توسعه کمی و کیفی مراکز</h4>
          <p style={{ fontSize: '.88rem', lineHeight: 2, color: 'var(--text2)' }}>
            توسعه کمی باید بر نیاز منطقه و ظرفیت اجتماعی استوار باشد و توسعه کیفی توان مرکز در
            شناسایی نیاز، جذب منابع، ارائه خدمت، ثبت اطلاعات و پاسخ‌گویی را افزایش دهد.
          </p>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 8 }}>هدف دوم — تعامل نظام‌مند با تشکل‌های مردمی</h4>
          <p style={{ fontSize: '.88rem', lineHeight: 2, color: 'var(--text2)' }}>
            تبدیل ارتباط موردی با خیریه‌ها، گروه‌های جهادی، تشکل‌های محلی، هیئت‌ها، سازمان‌های
            مردم‌نهاد و گروه‌های حرفه‌ای به همکاریِ دارای برنامه، مسئولیت و نتیجه.
          </p>
        </div>
      </div>

      <div className="grid g4" style={{ marginTop: 16 }}>
        <div className="card kpi">
          <div className="k-label"><span>پرداخت‌های شبکه (سال {faNum(yearLabel)})</span></div>
          <div className="k-value">{pay != null ? money(pay) : '—'}</div>
          <div className="k-note">از داده تراکنش‌های ثبت‌شده</div>
        </div>
        <div className="card kpi">
          <div className="k-label"><span>دریافت‌های شبکه</span></div>
          <div className="k-value">{rec != null ? money(rec) : '—'}</div>
          <div className="k-note">پایداری مالی شبکه مردمی</div>
        </div>
        <div className="card kpi">
          <div className="k-label"><span>ذی‌نفعان تحت پوشش</span></div>
          <div className="k-value">{ben != null ? faNum(ben) : '—'}</div>
          <div className="k-note">جمع ذی‌نفع تراکنش‌های دوره</div>
        </div>
        <div className="card kpi">
          <div className="k-label"><span>نیازمندان ثبت‌شده</span></div>
          <div className="k-value">{needyTotal != null ? faNum(needyTotal) : '—'}</div>
          <div className="k-note">کل مددجویان بانک نیازمندان</div>
        </div>
      </div>

      <div className="grid g23" style={{ marginTop: 16 }}>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 10 }}>۶-۳ — برنامه توسعه کمی مراکز (هفت‌گانه)</h4>
          <ol style={{ paddingRight: 22, lineHeight: 2.2, fontSize: '.9rem', color: 'var(--text2)' }}>
            {PROGRAMS_63.map((p, i) => <li key={i}>{p}</li>)}
          </ol>
          <div className="hint">
            هدف کمی حکم ۲۳: افزایش مجوزهای صادرشده از ۱۰٬۵۰۰ مورد در سال پایه به ۱۶٬۹۰۰ مورد در ۱۴۰۷ —
            این عدد نباید «مرکز فعال» گزارش شود مگر داده فعالیت آن را تأیید کند.
          </div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 10 }}>۶-۴ — حوزه‌های توسعه کیفی (جدول ۶-۱)</h4>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>حوزه</th><th>اقدامات اجرایی</th></tr></thead>
              <tbody>
                {TABLE_61.map((r, i) => (
                  <tr key={i}><td><b>{r[0]}</b></td><td style={{ fontSize: '.82rem' }}>{r[1]}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="grid g3" style={{ marginTop: 16 }}>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 8 }}>۶-۵ — جذب منابع مالی از خیرین</h4>
          <ul style={{ paddingRight: 18, fontSize: '.85rem', lineHeight: 2.1, color: 'var(--text2)' }}>
            <li>نقشه ظرفیت خیرین محلی در شش گروه (حقیقی، اصناف، بنگاه‌ها، متخصصان، گروه‌های داوطلب، پروژه‌محور)</li>
            <li>بسته مشارکت مشخص: نیاز تأییدشده + هزینه برآوردی + زمان اجرا + مسئول خدمت + گزارش نتیجه</li>
            <li>منابع پایدار: مشارکت دوره‌ای، قرارداد پروژه‌ای با بنگاه‌ها (حکم ۲۲)، مشارکت گروهی اصناف</li>
            <li>تفکیک سپرده قرض‌الحسنه از کمک بلاعوض</li>
          </ul>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 8 }}>۶-۶ — تعامل و نگهداشت خیرین</h4>
          <ul style={{ paddingRight: 18, fontSize: '.85rem', lineHeight: 2.1, color: 'var(--text2)' }}>
            <li>تعیین رابط پاسخ‌گو برای همکاری‌های مهم</li>
            <li>رسید یا تأیید مشارکت + گزارش پیشرفت پروژه</li>
            <li>دعوت داوطلبانه به نشست‌های مشورتی (حکم ۴۵)</li>
            <li>تکریم با رضایت خیر و حفظ حق ناشناس‌ماندن</li>
            <li>قاعده: ارزش خیر فقط مبلغ نیست؛ تخصص، زمان و شبکه ارتباطی نیز ارزشمند است</li>
          </ul>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 8 }}>۶-۷ و ۶-۸ — فرهنگ خیر و اطلاع‌رسانی</h4>
          <ul style={{ paddingRight: 18, fontSize: '.85rem', lineHeight: 2.1, color: 'var(--text2)' }}>
            <li>معرفی نمونه‌های همکاری جمعی و محله‌محور؛ ترویج کمک‌های کوچک و مستمر</li>
            <li>آموزش تفاوت حمایت فوری و توانمندسازی</li>
            <li>شناسنامه اطلاع‌رسانی هر مرکز: هویت، مجوز، مسیر مشارکت، تماس پاسخ‌گو، پروژه‌های جاری</li>
            <li>استفاده از سامانه rahnikan.ir برای ثبت و گزارش فعالیت و کاهش گزارش‌های پراکنده</li>
          </ul>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16, padding: 20 }}>
        <h4 style={{ color: 'var(--acc)', marginBottom: 4 }}>
          ۶-۹ — شاخص‌های ارزیابی (جدول ۶-۲) با مقادیر زنده داده‌ها
        </h4>
        <div className="hint" style={{ marginBottom: 12 }}>
          «محاسبه‌شده» یعنی مستقیم از داده‌ها؛ «تقریبی» یعنی نزدیک‌ترین سنجه در دسترس؛ «نیازمند داده» یعنی تا فیلد مربوط در فایل‌های ورودی ثبت نشود قابل محاسبه نیست.
        </div>
        {Object.entries(byArea).map(([area, list]) => (
          list.length > 0 && (
            <div key={area} style={{ marginBottom: 16 }}>
              <div className="row-flex" style={{ marginBottom: 6 }}>
                <span className="chip on">{area}</span>
              </div>
              <div className="tbl-wrap">
                <table className="tbl">
                  <thead><tr>
                    <th>شاخص</th><th>مقدار</th><th>وضعیت</th><th>مبدأ داده</th><th>توضیح</th>
                  </tr></thead>
                  <tbody>
                    {list.map((x) => {
                      const b = STATUS_BADGE[x.status] || STATUS_BADGE.proxy
                      return (
                        <tr key={x.key}>
                          <td><b>{x.label}</b></td>
                          <td className="num" style={{ fontWeight: 800, color: 'var(--acc)' }}>{fmtVal(x)}</td>
                          <td><span className={`tag ${b.cls}`}>{b.label}</span></td>
                          <td className="tile" style={{ fontSize: '.78rem' }}>{x.source}</td>
                          <td style={{ fontSize: '.8rem', color: 'var(--muted)' }}>{x.desc}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ))}
      </div>

      {ins?.insights?.length > 0 && (
        <div className="card" style={{ marginTop: 16, padding: 20 }}>
          <h4 style={{ color: 'var(--acc)', marginBottom: 12 }}>تحلیل خودکار و اقدام‌های پیشنهادی دوره</h4>
          {ins.insights.slice(0, 4).map((x, i) => <InsightCard key={i} ins={x} d={i} />)}
        </div>
      )}
    </>
  )
}
