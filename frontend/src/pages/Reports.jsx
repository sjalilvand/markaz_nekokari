import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, DataTable, Icons, faNum, shortMoney, heatmapOption,
} from '../components/ui.jsx'

const DS = [
  { key: 'transactions', label: 'تراکنش‌های مالی' },
  { key: 'requests', label: 'درخواست‌ها' },
  { key: 'needy', label: 'نیازمندان' },
  { key: 'members', label: 'اعضای مراکز' },
  { key: 'anomalies', label: 'تراکنش‌های ثبت‌نشده' },
]

export default function Reports() {
  const { filters, meta, bookmarks, saveBookmark, delBookmark, setFilter } = useFilters()
  const [ds, setDs] = useState('transactions')
  const [d, setD] = useState(null)
  const [page, setPage] = useState(1)
  const [per, setPer] = useState(15)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('')
  const [dir, setDir] = useState('desc')
  const [err, setErr] = useState(null)
  const [pivot, setPivot] = useState(null)
  const [pivotRow, setPivotRow] = useState('province')
  const [pivotCol, setPivotCol] = useState('year')
  const [pivotMetric, setPivotMetric] = useState('amount')
  const [bmName, setBmName] = useState('')

  useEffect(() => {
    setPage(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, ds])
  useEffect(() => {
    api.records(filters, { dataset: ds, page, per, search, sort, dir }).then(setD).catch(setErr)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, ds, page, per, search, sort, dir])
  useEffect(() => {
    api.pivot(filters, { row: pivotRow, col: pivotCol, metric: pivotMetric }).then(setPivot).catch(() => {})
  }, [filters, pivotRow, pivotCol, pivotMetric])

  const exportAll = () => {
    const a = document.createElement('a')
    a.href = api.exportUrl(filters, { dataset: ds, limit: 100000 })
    a.click()
  }

  const provName = (id) => meta?.provinces?.find((p) => String(p.id) === String(id))?.name || id

  const applyBookmark = (b) => {
    for (const k of ['year', 'province', 'office']) setFilter(k, b.filters?.[k] ?? 'all')
  }

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14 }}>
        {DS.map((x) => (
          <button key={x.key} className={`chip ${ds === x.key ? 'on' : ''}`}
            onClick={() => setDs(x.key)}>{x.label}</button>
        ))}
        <div className="spacer" />
        <button className="btn primary" onClick={exportAll}><Icons.download /> خروجی CSV (اکسل)</button>
        <button className="btn" onClick={() => window.print()}><Icons.print /> چاپ گزارش</button>
      </div>

      <ChartCard title="جست‌وجو و فیلتر رکوردها" d={0}
        sub="فیلترهای سراسری (سال/استان) + جست‌وجوی متن + مرتب‌سازی ستونی — مشابه Matrix در Power BI">
        <div className="row-flex" style={{ marginBottom: 10 }}>
          <input type="search" placeholder="جست‌وجو (شماره پیگیری، نام، کدملی…)" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }} style={{ flex: 1, minWidth: 220 }} />
          <select value={per} onChange={(e) => { setPer(+e.target.value); setPage(1) }}>
            {[10, 15, 25, 50, 100].map((x) => <option key={x} value={x}>{x} ردیف در صفحه</option>)}
          </select>
        </div>
        {!d ? <Loading /> : (
          <>
            {d.sum_amount !== null && d.sum_amount !== undefined && (
              <div className="row-flex" style={{ marginBottom: 8 }}>
                <span className="badge">جمع مبالغ کل داده فیلترشده: {shortMoney(d.sum_amount)}</span>
                <span className="badge">{faNum(d.total)} رکورد مطابق فیلتر</span>
              </div>
            )}
            <DataTable
              cols={d.cols.map((c) => ({ key: c[0], label: c[1] }))}
              rows={d.rows} page={d.page} per={d.per} total={d.total} onPage={setPage}
              sort={sort} dir={dir}
              onSort={(k) => { setSort(k); setDir(dir === 'desc' ? 'asc' : 'desc') }}
              rowKey={(r) => r.id} />
          </>
        )}
      </ChartCard>

      <div className="grid g32">
        <ChartCard title="جدول محوری (Pivot) با نقشه حرارتی" d={1} sub="ساخت پویا: انتخاب سطر، ستون و سنجه">
          <div className="row-flex" style={{ marginBottom: 10 }}>
            <select value={pivotRow} onChange={(e) => setPivotRow(e.target.value)}>
              <option value="province">سطر: استان</option>
              <option value="category">سطر: فعالیت</option>
              <option value="source">سطر: منبع</option>
              <option value="method">سطر: روش</option>
            </select>
            <select value={pivotCol} onChange={(e) => setPivotCol(e.target.value)}>
              <option value="year">ستون: سال</option>
              <option value="month">ستون: ماه</option>
              <option value="method">ستون: روش</option>
            </select>
            <select value={pivotMetric} onChange={(e) => setPivotMetric(e.target.value)}>
              <option value="amount">سنجه: مبلغ</option>
              <option value="count">سنجه: تعداد</option>
            </select>
          </div>
          {!pivot ? <Loading /> : (
            <>
              <Chart chartKey="rp-pivot" height={Math.min(560, 140 + Math.min(pivot.rows.length, 14) * 34)}
                option={heatmapOption({
                  rows: pivot.rows.slice(0, 14).map((r) => r.label),
                  cols: pivot.cols.map((c) => String(c)),
                  values: pivot.rows.slice(0, 14).map((r) => pivot.cols.map((c) => r.cells[c] || 0)),
                })} />
              <div className="hint">جمع کل: {shortMoney(pivot.grand_total)}</div>
            </>
          )}
        </ChartCard>

        <ChartCard title="نماهای ذخیره‌شده (Bookmarks)" d={2}
          sub="ترکیب فیلتر سال/استان/اداره را ذخیره و یک‌کلیکی فراخوانی کنید">
          <div className="row-flex" style={{ marginBottom: 10 }}>
            <input type="text" placeholder="نام نما…" value={bmName} onChange={(e) => setBmName(e.target.value)}
              style={{ flex: 1 }} />
            <button className="btn primary" disabled={!bmName}
              onClick={() => { saveBookmark(bmName); setBmName('') }}>ذخیره نمای فعلی</button>
          </div>
          {bookmarks.map((b) => (
            <div key={b.id} className="insight" style={{ alignItems: 'center' }}>
              <div style={{ flex: 1 }}>
                <h4>{b.name}</h4>
                <p>سال: {b.filters?.year === 'all' ? 'همه' : b.filters?.year}
                  {' | '}استان: {b.filters?.province === 'all' ? 'همه' : provName(b.filters?.province)}
                </p>
              </div>
              <button className="btn" onClick={() => applyBookmark(b)}>فراخوانی</button>
              <button className="icon-btn" onClick={() => delBookmark(b.id)}><Icons.close /></button>
            </div>
          ))}
          {bookmarks.length === 0 && <div className="hint">هنوز نمای ذخیره‌شده‌ای ندارید.</div>}
        </ChartCard>
      </div>
    </>
  )
}
