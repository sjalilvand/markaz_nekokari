import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Loading, ErrorBox, Icons, faNum, shortMoney, barOption, Chart, ChartCard,
} from '../components/ui.jsx'

export default function Admin() {
  const { meta } = useFilters()
  const [q, setQ] = useState(null)
  const [busy, setBusy] = useState(false)
  const [queue, setQueue] = useState([])   // [{name, status, upPct, result, error}]
  const [err, setErr] = useState(null)
  const [elapsed, setElapsed] = useState(0)
  const [resetBusy, setResetBusy] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    api.quality().then(setQ).catch(setErr)
    return () => clearInterval(timerRef.current)
  }, [])

  const doneCount = queue.filter((x) => x.status === 'done' || x.status === 'error').length
  const total = queue.length
  const fileCount = queue.filter((x) => x.kind !== 'recompute').length
  const overallPct = total ? Math.round((doneCount / total) * 100) : 0
  const current = queue.find((x) => x.status === 'uploading' || x.status === 'processing')

  const patch = (idx, fields) =>
    setQueue((qq) => qq.map((it, j) => (j === idx ? { ...it, ...fields } : it)))

  // ارسال یک فایل با تلاش مجدد خودکار برای خطاهای شبکه (حداکثر ۳ تلاش)
  const sendFile = async (idx, file) => {
    patch(idx, { status: 'uploading', upPct: 0, error: null, result: null })
    setElapsed(0)
    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt > 0) {
        patch(idx, { status: 'pending', error: `تلاش مجدد ${faNum(attempt + 1)} از ${faNum(3)}…` })
        await new Promise((r) => setTimeout(r, 3000))
        patch(idx, { status: 'uploading', upPct: 0 })
        setElapsed(0)
      }
      try {
        const r = await api.importFile(file, (pct) => {
          if (pct >= 100) patch(idx, { status: 'processing', upPct: 100 })
          else patch(idx, { status: 'uploading', upPct: pct })
        })
        clearInterval(timerRef.current)
        patch(idx, { status: 'done', result: r, error: null })
        return true
      } catch (x) {
        clearInterval(timerRef.current)
        patch(idx, { status: 'error', error: String(x?.message || x) })
        if (!x?.network) break // خطای منطقی سرور: تلاش مجدد بی‌فایده است
      }
    }
    return false
  }

  const runRecompute = async (idx) => {
    if (idx == null) return
    patch(idx, { status: 'processing' })
    setElapsed(0)
    clearInterval(timerRef.current)
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
    try {
      await api.recompute()
      clearInterval(timerRef.current)
      patch(idx, { status: 'done', result: {} })
    } catch (x) {
      clearInterval(timerRef.current)
      patch(idx, { status: 'error', error: String(x?.message || x) })
    }
    try { setQ(await api.quality()) } catch (_) { /* noop */ }
  }

  const upload = async (e) => {
    const files = [...e.target.files]
    e.target.value = ''
    if (!files.length) return
    setQueue([
      ...files.map((f) => ({ name: f.name, file: f, status: 'pending', upPct: 0 })),
      { name: 'بازمحاسبه امتیاز و مدال مراکز', kind: 'recompute', status: 'pending', upPct: 0 },
    ])
    setBusy(true)
    for (let i = 0; i < files.length; i++) {
      await sendFile(i, files[i])
    }
    // مرحله پایانی: بازمحاسبه امتیاز و مدال مراکز پس از ورود همه فایل‌ها
    await runRecompute(files.length)
    setBusy(false)
  }

  // تلاش دوباره برای یک فایل خطادار (از جدول نتایج)
  const retryFile = async (idx) => {
    const it = queue[idx]
    if (!it?.file || busy) return
    setBusy(true)
    await sendFile(idx, it.file)
    await runRecompute(queue.length - 1)
    setBusy(false)
  }

  const resetDb = async () => {
    if (!window.confirm('همه داده‌های فعلی پایگاه داده (داده نمونه و بارگذاری‌های قبلی) حذف می‌شود و پایگاه داده برای ورود داده واقعی خالی می‌شود. مطمئن هستید؟')) return
    setResetBusy(true)
    try {
      await api.resetDb()
      setQueue([])
      setQ(await api.quality())
    } catch (x) { setErr(x) }
    setResetBusy(false)
  }

  // پیام راهنما برای فایل‌های خطادار
  const hasErrors = queue.some((x) => x.status === 'error' && x.kind !== 'recompute')

  if (err && !q) return <ErrorBox err={err} />
  if (!q) return <Loading />

  return (
    <>
      <div className="grid g2">
        <ChartCard title="بارگذاری فایل‌های CSV" d={0}
          sub="کدگذاری خودکار (UTF-8 / Windows-1256) — تشخیص خودکار اسکیمای هر فایل و ثبت مستقیم در پایگاه داده">
          <div className="row-flex" style={{ gap: 8 }}>
            <label className="btn primary" style={{ padding: '12px 20px', fontSize: 14 }}>
              <Icons.upload /> انتخاب فایل‌های CSV و بارگذاری
              <input type="file" multiple accept=".csv" onChange={upload} style={{ display: 'none' }} disabled={busy} />
            </label>
            <button className="btn danger" onClick={resetDb} disabled={busy || resetBusy}
              title="حذف داده نمونه و بارگذاری‌های قبلی برای شروع با داده واقعی">
              <Icons.close /> پاک‌سازی پایگاه داده
            </button>
          </div>

          {total > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="row-flex" style={{ gap: 10, alignItems: 'center', marginBottom: 6 }}>
                <b style={{ fontSize: 13 }}>
                  {busy && current?.kind === 'recompute'
                    ? 'مرحله پایانی — بازمحاسبه امتیاز و مدال مراکز'
                    : busy
                      ? `در حال بارگذاری — فایل ${faNum(Math.min(doneCount + 1, fileCount))} از ${faNum(fileCount)}`
                      : `پایان بارگذاری — ${faNum(fileCount)} فایل پردازش شد`}
                </b>
                <span className="badge" style={{ marginInlineEnd: 'auto' }}>{faNum(overallPct)}٪</span>
              </div>
              <div className="pbar big"><i style={{ width: overallPct + '%' }} /></div>
              {current && (
                <div className="pstat" style={{ marginTop: 6 }}>
                  در حال پردازش: <b>{current.name}</b>
                  {current.status === 'processing' && ` — پردازش سمت سرور (${faNum(elapsed)} ثانیه)`}
                </div>
              )}
            </div>
          )}

          <div className="hint">
            می‌توانید همه فایل‌ها را یک‌جا انتخاب کنید؛ فایل‌ها یکی‌یکی ارسال و ثبت می‌شوند و درصد پیشرفت
            و تعداد فایل‌های خوانده‌شده همین‌جا نمایش داده می‌شود. پس از پایان، امتیاز و مدال مراکز
            بازمحاسبه می‌شود. ورود مجدد هر فایل، رکوردهای قبلی همان فایل را جایگزین می‌کند و داده تکراری نمی‌سازد.
            برای شروع با داده واقعی، ابتدا «پاک‌سازی پایگاه داده» را بزنید و سپس فایل‌های خود را بارگذاری کنید.
          </div>

          {hasErrors && !busy && (
            <div className="hint" style={{ borderInlineStart: '3px solid #c0392b' }}>
              به برخی فایل‌ها خطا خورده است. با دکمه «تلاش دوباره» همان فایل می‌توانید فقط همان را دوباره بفرستید؛
              یا همه فایل‌های خطادار را دوباره انتخاب کنید — ورود مجدد، رکوردهای قبلی همان فایل را جایگزین می‌کند و تکراری ایجاد نمی‌شود.
            </div>
          )}

          {total > 0 && (
            <div className="tbl-wrap" style={{ marginTop: 10 }}>
              <table className="tbl">
                <thead><tr><th>فایل</th><th>وضعیت</th><th>اسکیما</th><th>خوانده‌شده</th><th>ثبت‌شده</th><th>خالی٪</th><th>زمان</th></tr></thead>
                <tbody>
                  {queue.map((it, i) => (
                    <tr key={i}>
                      <td>{it.name}</td>
                      <td style={{ minWidth: 150 }}>
                        {statusCell(it, elapsed)}
                        {it.status === 'error' && it.file && (
                          <button className="btn danger" disabled={busy}
                            style={{ padding: '4px 10px', fontSize: 12, marginInlineStart: 8 }}
                            onClick={() => retryFile(i)}>
                            تلاش دوباره
                          </button>
                        )}
                      </td>
                      <td>{it.result?.schema_name || '—'}</td>
                      <td className="num">{it.result?.rows_read != null ? faNum(it.result.rows_read) : '—'}</td>
                      <td className="num">{it.result?.inserted != null ? faNum(it.result.inserted) : '—'}</td>
                      <td className="num">{it.result?.nulls_pct != null ? faNum(it.result.nulls_pct) : '—'}</td>
                      <td className="num">{it.result?.elapsed != null ? `${faNum(it.result.elapsed)}s` : '—'}</td>
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

function statusCell(it, elapsed) {
  if (it.status === 'pending') return <span className="pstat">در صف…</span>
  if (it.status === 'uploading') return (
    <div>
      <div className="pbar"><i style={{ width: it.upPct + '%' }} /></div>
      <span className="pstat">در حال آپلود — {faNum(it.upPct)}٪</span>
    </div>
  )
  if (it.status === 'processing') {
    if (it.kind === 'recompute') return (
      <div>
        <span className="spin" />
        <span className="pstat">در حال بازمحاسبه امتیاز و مدال مراکز… ({faNum(elapsed)} ثانیه)</span>
      </div>
    )
    return (
      <div>
        <span className="spin" />
        <span className="pstat">در حال پردازش و ثبت در پایگاه داده… ({faNum(elapsed)} ثانیه)</span>
      </div>
    )
  }
  if (it.status === 'error') return <span className="st-err">خطا: {it.error}</span>
  if (it.kind === 'recompute') return <span className="st-done">انجام شد</span>
  return <span className="st-done">وارد شد</span>
}

function nullLabel(k) {
  const map = {
    null_decile: 'خالی دهک', null_mobile: 'خالی موبایل', null_nat: 'بدون کدملی',
    null_center: 'بدون مرکز', m: 'میانگین اعضای فعال',
  }
  return map[k] || k
}
