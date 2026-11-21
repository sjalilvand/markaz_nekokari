import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Loading, ErrorBox, Icons, faNum, shortMoney, barOption, Chart, ChartCard,
} from '../components/ui.jsx'

export default function Admin() {
  const { meta } = useFilters()
  const [q, setQ] = useState(null)
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.quality().then(setQ).catch(setErr)
  }, [results])

  const upload = async (e) => {
    const files = [...e.target.files]
    if (!files.length) return
    setBusy(true)
    try {
      const r = await api.importFiles(files)
      setResults(r.results)
    } catch (x) {
      setErr(x)
    }
    setBusy(false)
    e.target.value = ''
  }

  if (err && !q) return <ErrorBox err={err} />
  if (!q) return <Loading />

  return (
    <>
      <div className="grid g2">
        <ChartCard title="بارگذاری فایل‌های CSV" d={0}
          sub="کدگذاری خودکار (UTF-8 / Windows-1256) — نگاشت خودکار ۲۵ اسکیمای شناخته‌شده سامانه نیکوکاری">
          <label className="btn primary" style={{ padding: '12px 20px', fontSize: 14 }}>
            <Icons.upload /> انتخاب فایل‌های CSV و بارگذاری
            <input type="file" multiple accept=".csv" onChange={upload} style={{ display: 'none' }} disabled={busy} />
          </label>
          {busy && <div className="loading">در حال پردازش و وارد کردن…</div>}
          <div className="hint">
            فایل‌های شناخته‌شده: New.csv (مراکز)، NK_HAMYARAN REPORT (همیاران)، NK_NIAZMANDAN REP (نیازمندان)،
            Report.csv (درخواست‌ها)، گزارش‌های پرداخت/دریافت، کارتکس مراکز و اعضا، شبکه‌سازی، تعریف پک،
            جبران خدمات، گزارش کلی، نیکوکاران حقوقی و…
            پس از بارگذاری، امتیازدهی و مدال مراکز بازمحاسبه می‌شود و شعایص سامانه به «داده واقعی» تغییر می‌کند.
          </div>
          {results && (
            <div className="tbl-wrap" style={{ marginTop: 10 }}>
              <table className="tbl">
                <thead><tr><th>فایل</th><th>اسکیما</th><th>رکورد</th><th>واردشده</th><th>خالی٪</th><th>زمان</th></tr></thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i}>
                      <td>{r.filename}</td>
                      <td>{r.schema_name || '—'}</td>
                      <td className="num">{faNum(r.rows_read)}</td>
                      <td className="num">{faNum(r.inserted || 0)}</td>
                      <td className="num">{faNum(r.nulls_pct || 0)}</td>
                      <td className="num">{faNum(r.elapsed || 0)}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ChartCard>

        <ChartCard title="مطابقت با ارقام مرجع فایل مالی استانی" d={1}
          sub="مقایسه جمع تراکنش‌های سامانه با ارقام واقعی «گزارش دریافت و پرداخت به تفکیک استان»">
          <Chart chartKey="ad-anchor" height={300} option={barOption({
            labels: Object.keys(q.real_anchor || {}),
            data: [
              Object.entries(q.real_anchor || {}).map(([k, v]) => q.tx_anchor?.[k] ?? 0),
              Object.values(q.real_anchor || {}),
            ],
            legends: ['سامانه', 'فایل مرجع'],
          })} />
          <div className="hint">
            ارقام مرجع فایل (ریال): پرداخت نقدی {shortMoney(q.real_anchor['پرداخت نقدی'])}، پرداخت غیرنقدی
            {' '}{shortMoney(q.real_anchor['پرداخت غیرنقدی'])}، دریافت نقدی {shortMoney(q.real_anchor['دریافت نقدی'])}،
            دریافت غیرنقدی {shortMoney(q.real_anchor['دریافت غیرنقدی'])}
          </div>
        </ChartCard>
      </div>

      <ChartCard title="سلامت جدول‌ها" d={2} sub="شمار رکورد و درصد فیلدهای خالی کلیدی">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>جدول</th><th>رکوردها</th><th>شاخص‌های کیفیت</th></tr></thead>
            <tbody>
              {q.tables.map((t) => (
                <tr key={t.table}>
                  <td><b>{t.table}</b></td>
                  <td className="num">{faNum(t.rows)}</td>
                  <td>
                    {Object.entries(t.notes || {}).map(([k, v]) => (
                      <span key={k} className="badge" style={{ marginInlineEnd: 6 }}>{faNum(v)}٪ {nullLabel(k)}</span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="hint">تعداد رکوردهای گزارش‌های عمومی (فایل‌های با اسکیمای ناشناخته): {faNum(q.agg_reports)}</div>
      </ChartCard>

      <ChartCard title="تراکنش‌های ثبت‌نشده شناسایی‌شده" d={3} sub="اسناد مالی بدون تراکنش بانکی متناظر">
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>استان</th><th>شماره سند</th><th>تاریخ</th><th>نوع</th><th>مبلغ</th><th>شرح</th></tr></thead>
            <tbody>
              {(q.anomalies || []).map((a) => (
                <tr key={a.id}>
                  <td>{a.province}</td>
                  <td className="num">{a.doc_no}</td>
                  <td>{a.date_j}</td>
                  <td>{a.flow}</td>
                  <td className="num">{shortMoney(a.amount)}</td>
                  <td>{a.descr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      <ChartCard title="گزارش واردکردن فایل‌ها" d={4} sub="تاریخچه بارگذاری‌ها و کیفیت هر فایل">
        {(q.logs || []).length === 0 && <div className="hint">هنوز فایلی بارگذاری نشده است. با دکمه بالا فایل‌های CSV خود را وارد کنید.</div>}
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>فایل</th><th>اسکیما</th><th>کدگذاری</th><th>رکورد</th><th>واردشده</th><th>خالی٪</th><th>زمان</th><th>هشدار</th></tr></thead>
            <tbody>
              {(q.logs || []).map((l) => (
                <tr key={l.id}>
                  <td>{l.filename}</td>
                  <td>{l.schema_name}</td>
                  <td>{l.encoding}</td>
                  <td className="num">{faNum(l.rows_read)}</td>
                  <td className="num">{faNum(l.rows_inserted)}</td>
                  <td className="num">{faNum(l.nulls_pct)}</td>
                  <td className="num">{l.imported_at}</td>
                  <td className="tile">{l.warnings}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </>
  )
}

function nullLabel(k) {
  const map = {
    null_decile: 'خالی دهک', null_mobile: 'خالی موبایل', null_nat: 'بدون کدملی',
    null_center: 'بدون مرکز', m: 'میانگین اعضای فعال',
  }
  return map[k] || k
}
