import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import {
  Chart, ChartCard, Loading, ErrorBox, DataTable, Icons, faNum, faNum1, shortMoney, barOption,
} from '../components/ui.jsx'

// ─── صفحه رصد داده‌ها: فیلتر هر ستون + صفحه‌بندی + گروه‌بندی برای همه جدول‌ها ───

const OPS = [
  { k: 'contains', label: 'شامل باشد' },
  { k: 'ncontains', label: 'شامل نباشد' },
  { k: 'eq', label: 'برابر' },
  { k: 'ne', label: 'نابرابر' },
  { k: 'gt', label: 'بزرگ‌تر از' },
  { k: 'ge', label: 'بزرگ‌تر یا مساوی' },
  { k: 'lt', label: 'کوچک‌تر از' },
  { k: 'le', label: 'کوچک‌تر یا مساوی' },
  { k: 'between', label: 'بین دو مقدار' },
  { k: 'empty', label: 'خالی' },
  { k: 'nempty', label: 'غیرخالی' },
]
const TEXT_OPS = ['contains', 'ncontains', 'eq', 'ne', 'empty', 'nempty']
const NUM_OPS = ['eq', 'ne', 'gt', 'ge', 'lt', 'le', 'between', 'empty', 'nempty']
const AGGS = [
  { k: 'count', label: 'تعداد رکورد' },
  { k: 'sum', label: 'جمع' },
  { k: 'avg', label: 'میانگین' },
  { k: 'max', label: 'بیشینه' },
  { k: 'min', label: 'کمینه' },
]

export default function Explore() {
  const [tables, setTables] = useState(null)
  const [tableKey, setTableKey] = useState('transactions')
  const [filters, setFilters] = useState([])
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [per, setPer] = useState(15)
  const [sort, setSort] = useState('')
  const [dir, setDir] = useState('desc')
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [groupCol, setGroupCol] = useState('category')
  const [groupAgg, setGroupAgg] = useState('sum')
  const [groupAggCol, setGroupAggCol] = useState('amount')
  const [groupData, setGroupData] = useState(null)

  const table = useMemo(
    () => (tables || []).find((t) => t.key === tableKey), [tables, tableKey])
  const colByKey = useMemo(() => {
    const m = {}
    for (const c of table?.cols || []) m[c.key] = c
    return m
  }, [table])
  const numCols = useMemo(
    () => (table?.cols || []).filter((c) => c.type === 'num'), [table])
  const textCols = useMemo(
    () => (table?.cols || []).filter((c) => c.type === 'text'), [table])

  useEffect(() => {
    api.exploreTables().then((d) => setTables(Array.isArray(d) ? d : (d?.tables || []))).catch(setErr)
  }, [])

  // با تغییر جدول: فیلترها و گروه‌بندی ریست و مقادیر پیش‌فرض منطقی
  useEffect(() => {
    setFilters([])
    setPage(1)
    setSort('')
    setGroupData(null)
    const cols = (tables || []).find((t) => t.key === tableKey)?.cols || []
    const nc = cols.filter((c) => c.type === 'num')
    const tc = cols.filter((c) => c.type === 'text')
    setGroupCol(tc.find((c) => ['category', 'province', 'network', 'flow', 'method', 'status', 'request_type', 'role', 'need_type', 'schema_name'].includes(c.key))?.key
      || (tc[0]?.key || ''))
    setGroupAgg(nc.length ? 'sum' : 'count')
    setGroupAggCol(nc.find((c) => c.key === 'amount')?.key || nc[0]?.key || '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableKey, tables])

  useEffect(() => {
    setPage(1)
  }, [filters, search, per])

  useEffect(() => {
    if (!tables) return
    api.explore({
      table: tableKey, page, per, sort, dir, search,
      filters: JSON.stringify(filters.filter((f) => f.col && (f.op === 'empty' || f.op === 'nempty' || (f.val !== '' && f.val !== undefined && f.val !== null)))),
    }).then(setData).catch(setErr)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tables, tableKey, filters, search, page, per, sort, dir])

  useEffect(() => {
    if (!tables || !groupCol) return
    api.exploreGroup({
      table: tableKey, group: groupCol, agg: groupAgg,
      agg_col: groupAggCol || '',
      filters: JSON.stringify(filters.filter((f) => f.col && (f.op === 'empty' || f.op === 'nempty' || (f.val !== '' && f.val !== undefined && f.val !== null)))),
    }).then(setGroupData).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tables, tableKey, groupCol, groupAgg, groupAggCol, filters])

  const addFilter = () => {
    const firstCol = (table?.cols || [])[0]
    setFilters((fs) => [...fs, {
      col: firstCol?.key || '', op: firstCol?.type === 'num' ? 'ge' : 'contains',
      val: '', val2: '',
    }])
  }
  const updFilter = (i, patch) => {
    setFilters((fs) => fs.map((f, j) => {
      if (j !== i) return f
      const nf = { ...f, ...patch }
      if (patch.col) {
        const ct = colByKey[patch.col]?.type || 'text'
        nf.op = ct === 'num' ? 'ge' : 'contains'
      }
      return nf
    }))
  }
  const delFilter = (i) => setFilters((fs) => fs.filter((_, j) => j !== i))

  const exportCsv = () => {
    const a = document.createElement('a')
    a.href = api.exploreExportUrl({
      table: tableKey, search,
      filters: JSON.stringify(filters),
    })
    a.click()
  }

  if (err && !tables) return <ErrorBox err={err} />
  if (!tables) return <Loading />

  const activeFilters = filters.filter((f) => f.col && (f.op === 'empty' || f.op === 'nempty'
    || (f.val !== '' && f.val !== undefined && f.val !== null)))

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14, flexWrap: 'wrap' }}>
        {(tables || []).map((t) => (
          <button key={t.key} className={`chip ${tableKey === t.key ? 'on' : ''}`}
            onClick={() => setTableKey(t.key)}>
            {t.label} <b style={{ opacity: 0.75 }}>({faNum(t.count)})</b>
          </button>
        ))}
      </div>

      <ChartCard title="فیلتر هر ستون" d={0}
        sub="برای هر ستون شرط دلخواه (شامل، برابر، بازه عددی، خالی و…) تعریف کنید؛ فیلترها بلافاصله اعمال می‌شوند"
        actions={<button className="btn" onClick={addFilter}><Icons.close style={{ transform: 'rotate(45deg)' }} /> افزودن فیلتر</button>}>
        {filters.length === 0 && (
          <div className="hint">هنوز فیلتری تعریف نشده است. با دکمه «افزودن فیلتر» شرط‌های ستونی بسازید — مانند فیلترهای Power BI.</div>
        )}
        {filters.map((f, i) => {
          const ct = colByKey[f.col]?.type || 'text'
          const ops = ct === 'num' ? NUM_OPS : TEXT_OPS
          return (
            <div key={i} className="row-flex" style={{ marginBottom: 8, flexWrap: 'wrap', gap: 6 }}>
              <select value={f.col} onChange={(e) => updFilter(i, { col: e.target.value })}
                style={{ maxWidth: 220 }}>
                {(table?.cols || []).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
              </select>
              <select value={f.op} onChange={(e) => updFilter(i, { op: e.target.value })}>
                {OPS.filter((o) => ops.includes(o.k)).map((o) => <option key={o.k} value={o.k}>{o.label}</option>)}
              </select>
              {f.op !== 'empty' && f.op !== 'nempty' && (
                <input type={ct === 'num' ? 'number' : 'text'} value={f.val ?? ''}
                  placeholder={ct === 'num' ? 'مقدار عددی' : 'مقدار'}
                  onChange={(e) => updFilter(i, { val: e.target.value })}
                  style={{ minWidth: 140 }} />
              )}
              {f.op === 'between' && (
                <input type={ct === 'num' ? 'number' : 'text'} value={f.val2 ?? ''}
                  placeholder="تا مقدار" onChange={(e) => updFilter(i, { val2: e.target.value })}
                  style={{ minWidth: 140 }} />
              )}
              <button className="icon-btn" title="حذف فیلتر" onClick={() => delFilter(i)}><Icons.close /></button>
            </div>
          )
        })}
        <div className="row-flex" style={{ marginTop: 6, flexWrap: 'wrap' }}>
          <input type="search" placeholder="جست‌وجوی سراسری در همه ستون‌های متنی…" value={search}
            onChange={(e) => setSearch(e.target.value)} style={{ flex: 1, minWidth: 220 }} />
          <select value={per} onChange={(e) => { setPer(+e.target.value); setPage(1) }}>
            {[10, 15, 25, 50, 100].map((x) => <option key={x} value={x}>{x} ردیف در صفحه</option>)}
          </select>
          <button className="btn primary" onClick={exportCsv}><Icons.download /> خروجی CSV فیلترشده</button>
        </div>
        {activeFilters.length > 0 && (
          <div className="hint">{faNum(activeFilters.length)} شرط فعال — داده‌ها به‌صورت زنده فیلتر شده‌اند.</div>
        )}
      </ChartCard>

      <ChartCard title={`رکوردهای جدول: ${table?.label || ''}`} d={1} sub="کلیک روی سرستون برای مرتب‌سازی">
        {!data ? <Loading /> : (
          <>
            <div className="row-flex" style={{ marginBottom: 8, flexWrap: 'wrap' }}>
              <span className="badge">{faNum(data.total)} رکورد مطابق فیلتر</span>
              {Object.entries(data.aggs || {}).map(([k, v]) => (
                v.sum !== null && v.sum !== undefined && (
                  <span key={k} className="badge">
                    {colByKey[k]?.label}: جمع {faNum(v.sum)} | میانگین {faNum1(v.avg)}
                  </span>
                )
              ))}
            </div>
            <DataTable
              cols={(data.cols || []).map((c) => ({ key: c.key, label: c.label, num: c.type === 'num' }))}
              rows={data.rows} page={data.page} per={data.per} total={data.total} onPage={setPage}
              sort={sort} dir={dir}
              onSort={(k) => { setSort(k); setDir(dir === 'desc' ? 'asc' : 'desc') }}
              rowKey={(r) => r.id !== undefined ? r.id : JSON.stringify(r).slice(0, 60)}
              empty="رکوردی مطابق فیلترها پیدا نشد" />
          </>
        )}
      </ChartCard>

      <ChartCard title="گروه‌بندی و تجمیع" d={2}
        sub="یک ستون را گروه‌بندی و با تابع دلخواه تجمیع کنید (مانند Group By در Excel)">
        <div className="row-flex" style={{ marginBottom: 10, flexWrap: 'wrap' }}>
          <select value={groupCol} onChange={(e) => setGroupCol(e.target.value)}>
            {(table?.cols || []).map((c) => <option key={c.key} value={c.key}>گروه: {c.label}</option>)}
          </select>
          <select value={groupAgg} onChange={(e) => setGroupAgg(e.target.value)}>
            {AGGS.map((a) => <option key={a.k} value={a.k}>{a.label}</option>)}
          </select>
          {['sum', 'avg', 'max', 'min'].includes(groupAgg) && (
            <select value={groupAggCol} onChange={(e) => setGroupAggCol(e.target.value)}>
              {numCols.map((c) => <option key={c.key} value={c.key}>ستون: {c.label}</option>)}
            </select>
          )}
        </div>
        {!groupData || groupData.rows.length === 0 ? (
          <div className="hint">داده‌ای برای گروه‌بندی مطابق فیلترها نیست.</div>
        ) : (
          <div className="grid g23">
            <Chart chartKey={`ex-group-${tableKey}-${groupCol}`} height={Math.min(520, 160 + Math.min(groupData.rows.length, 12) * 32)}
              option={barOption({
                labels: groupData.rows.slice(0, 12).map((r) => r.lbl || 'نامشخص'),
                data: [groupData.rows.slice(0, 12).map((r) => r.val)],
                legends: [groupData.value_label || 'مقدار'],
                horizontal: true,
              })} />
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr><th>{groupData.group_label}</th><th>{groupData.value_label}</th><th>تعداد</th></tr></thead>
                <tbody>
                  {groupData.rows.slice(0, 15).map((r, i) => (
                    <tr key={i}>
                      <td>{r.lbl || 'نامشخص'}</td>
                      <td className="num">{faNum(r.val)}</td>
                      <td className="num">{faNum(r.cnt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="hint">از {faNum(groupData.total)} مقدار یکتا — {faNum(Math.min(60, groupData.rows.length))} مورد نمایش داده شده است.</div>
            </div>
          </div>
        )}
      </ChartCard>
    </>
  )
}
