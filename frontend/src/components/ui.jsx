import React, { useEffect, useMemo, useRef, useState } from 'react'
import * as echarts from 'echarts'

// ───────────────────────── قالب‌بندی اعداد فارسی ─────────────────────────

const faFmt = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 0 })
const faFmt1 = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 })

export const faNum = (n) => (n === null || n === undefined || isNaN(n)) ? '—' : faFmt.format(n)
export const faNum1 = (n) => (n === null || n === undefined || isNaN(n)) ? '—' : faFmt1.format(n)

export function money(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  const a = Math.abs(n)
  if (a >= 1e12) return `${faFmt1.format(n / 1e12)} هزار میلیارد ریال`
  if (a >= 1e9) return `${faFmt1.format(n / 1e9)} میلیارد ریال`
  if (a >= 1e6) return `${faFmt1.format(n / 1e6)} میلیون ریال`
  return faNum(n) + ' ریال'
}
export const shortMoney = (n) => {
  if (n === null || n === undefined || isNaN(n)) return '—'
  const a = Math.abs(n)
  if (a >= 1e12) return `${faFmt1.format(n / 1e12)} همت`
  if (a >= 1e9) return `${faFmt1.format(n / 1e9)} میلیارد`
  if (a >= 1e6) return `${faFmt1.format(n / 1e6)} میلیون`
  return faNum(n)
}
export const MONTHS = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
  'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
export const monthLabel = (y, m) => `${MONTHS[(m || 1) - 1]} ${y}`

export const PALETTE = ['#3ee6c8', '#8f9dff', '#c79dff', '#5aa7ff', '#4ade80',
  '#ffb35c', '#ff7b7b', '#ff8fb8', '#b98cff', '#ffd76e']

export const MEDAL_COLORS = {
  'پلاتین': '#9db9e8', 'طلا': '#ffd76e', 'نقره': '#a9b6cc', 'برنز': '#c77b46',
  'نیازمند بهبود': '#6b789c',
}
export const MEDAL_CLASS = {
  'پلاتین': 'platinum', 'طلا': 'gold', 'نقره': 'silver', 'برنز': 'bronze',
  'نیازمند بهبود': 'none',
}

// ───────────────────────── آیکون‌های SVG ─────────────────────────

const I = (d) => (props) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" {...props}><path d={d} /></svg>
)
export const Icons = {
  dashboard: I('M3 3h8v8H3zM13 3h8v5h-8zM13 12h8v9h-8zM3 15h8v6H3z'),
  analytics: I('M4 20V10M10 20V4M16 20v-7M22 20H2'),
  coins: I('M12 8c4.4 0 8-1.3 8-3s-3.6-3-8-3-8 1.3-8 3 3.6 3 8 3zM4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6'),
  map: I('M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11zM12 8a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z'),
  building: I('M3 21h18M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16M15 9h4a2 2 0 0 1 2 2v10M9 7h2M9 11h2M9 15h2'),
  medal: I('M7.5 4h9l-2.5 6h-4l-2.5-6zM12 10a6 6 0 1 0 0 12 6 6 0 0 0 0-12zM12 13l1 2h2l-1.6 1.4.6 2.1-2-1.2-2 1.2.6-2.1L9 15h2l1-2z'),
  gauge: I('M12 14l4-6M3.5 17a10 10 0 1 1 17 0M12 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'),
  report: I('M6 2h9l5 5v15H6zM15 2v5h5M9 12h6M9 16h6M9 8h2'),
  upload: I('M12 16V4M7 9l5-5 5 5M4 20h16'),
  people: I('M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8'),
  heart: I('M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21.2l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z'),
  download: I('M12 4v12M6 11l6 6 6-6M4 20h16'),
  print: I('M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v7H6z'),
  bookmark: I('M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z'),
  moon: I('M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z'),
  sun: I('M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4'),
  search: I('M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3'),
  close: I('M18 6L6 18M6 6l12 12'),
  warn: I('M12 9v4M12 17h.01M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z'),
  check: I('M20 6L9 17l-5-5'),
  trend: I('M23 6l-9.5 9.5-5-5L1 18M17 6h6v6'),
  presentation: I('M3 3h18v12H3zM12 15v6M8 21h8'),
  layers: I('M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5'),
}

// ───────────────────────── نمودار ECharts ─────────────────────────

const FONT = "'Vazirmatn', system-ui, sans-serif"

export function Chart({ option, onClick, height = 280, style, chartKey }) {
  const ref = useRef(null)
  const inst = useRef(null)
  const optRef = useRef(option)
  optRef.current = option

  useEffect(() => {
    if (!ref.current) return
    inst.current = echarts.init(ref.current, null, { renderer: 'canvas' })
    inst.current.setOption(optRef.current)
    if (chartKey) chartInstances.set(chartKey, inst.current)
    const ro = new ResizeObserver(() => inst.current && inst.current.resize())
    ro.observe(ref.current)
    if (onClick) {
      inst.current.on('click', (p) => onClick(p))
    }
    return () => { ro.disconnect(); inst.current && inst.current.dispose() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (inst.current) inst.current.setOption(option, true)
  }, [option])

  return <div ref={ref} style={{ height, width: '100%', ...style }} />
}

function axisTheme() {
  return {
    axisLine: { lineStyle: { color: 'rgba(128,145,190,.35)' } },
    axisLabel: { color: '#98a5c6', fontFamily: FONT, fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(128,145,190,.15)' } },
    axisTick: { show: false },
  }
}

export function tooltipStyle(extra = {}) {
  return {
    backgroundColor: 'rgba(10,16,38,.94)', borderColor: 'rgba(143,157,255,.4)',
    textStyle: { color: '#eaeefb', fontFamily: FONT, fontSize: 12 },
    confine: true, ...extra,
  }
}

export function lineOption({ series, labels, legends, smooth = true, area = true, colors = PALETTE }) {
  return {
    color: colors,
    tooltip: { trigger: 'axis', ...tooltipStyle() },
    legend: { data: legends, textStyle: { color: '#98a5c6', fontFamily: FONT, fontSize: 11.5 }, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8 },
    grid: { left: 8, right: 14, top: 30, bottom: 8, containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: labels, ...axisTheme() },
    yAxis: { type: 'value', ...axisTheme(), axisLabel: { ...axisTheme().axisLabel, formatter: (v) => shortMoney(v) } },
    series: series.map((s, i) => ({
      name: legends[i], type: 'line', data: s, smooth,
      showSymbol: false, lineStyle: { width: 2.6 },
      areaStyle: area ? { opacity: .14 } : undefined,
    })),
  }
}

export function barOption({ data, labels, legends = ['مقدار'], stacked = false, horizontal = false, colors = PALETTE, maxBars }) {
  const series = data.map((s, i) => ({
    name: legends[i], type: 'bar', data: s, stack: stacked ? 'a' : undefined,
    barMaxWidth: 26, itemStyle: { borderRadius: horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0], color: colors[i % colors.length] },
  }))
  return {
    color: colors,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, ...tooltipStyle(),
      valueFormatter: (v) => shortMoney(v) },
    legend: legends.length > 1 ? { data: legends, textStyle: { color: '#98a5c6', fontFamily: FONT, fontSize: 11.5 }, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8 } : undefined,
    grid: { left: 8, right: 18, top: legends.length > 1 ? 30 : 16, bottom: 8, containLabel: true },
    ...(horizontal
      ? {
          xAxis: { type: 'value', ...axisTheme(), axisLabel: { ...axisTheme().axisLabel, formatter: (v) => shortMoney(v) } },
          yAxis: { type: 'category', data: maxBars ? labels.slice(-maxBars) : labels, ...axisTheme() },
          series: series.map((s) => ({ ...s, data: maxBars ? s.data.slice(-maxBars) : s.data })),
        }
      : {
          xAxis: { type: 'category', data: labels, ...axisTheme(), axisLabel: { ...axisTheme().axisLabel, rotate: labels.length > 12 ? 40 : 0 } },
          yAxis: { type: 'value', ...axisTheme(), axisLabel: { ...axisTheme().axisLabel, formatter: (v) => shortMoney(v) } },
          series,
        }),
  }
}

export function donutOption({ data, colors = PALETTE, centerText, radius = ['58%', '78%'] }) {
  return {
    color: colors,
    tooltip: { trigger: 'item', ...tooltipStyle(),
      valueFormatter: (v) => shortMoney(v) },
    legend: { orient: 'vertical', right: 4, top: 'middle', textStyle: { color: '#98a5c6', fontFamily: FONT, fontSize: 11.5 },
      icon: 'roundRect', itemWidth: 10, itemHeight: 8, formatter: (n) => n.length > 16 ? n.slice(0, 15) + '…' : n },
    series: [{
      type: 'pie', radius, center: ['40%', '50%'], avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: 'rgba(0,0,0,.25)', borderWidth: 2 },
      label: { show: false }, emphasis: { scale: true, scaleSize: 6 },
      data,
    }],
    graphic: centerText ? [{
      type: 'text', left: '34%', top: '46%', style: {
        text: centerText, fill: '#eaeefb', fontSize: 15, fontWeight: 'bold', fontFamily: FONT,
        textAlign: 'center',
      },
    }] : undefined,
  }
}

export function gaugeOption({ value, max = 100, label, color = '#3ee6c8' }) {
  return {
    series: [{
      type: 'gauge', startAngle: 210, endAngle: -30, min: 0, max,
      progress: { show: true, width: 14, itemStyle: { color } },
      axisLine: { lineStyle: { width: 14, color: [[1, 'rgba(128,145,190,.18)']] } },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      pointer: { show: false }, anchor: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true, offsetCenter: [0, 0], fontSize: 18, fontWeight: 'bold',
        color: '#eaeefb', fontFamily: FONT, formatter: (v) => faNum1(v) + '٪',
      },
      data: [{ value, name: label }],
    }],
  }
}

export function heatmapOption({ rows, cols, values, colors = ['#173a5e', '#0fae94'] }) {
  const data = []
  let max = 0
  values.forEach((r, i) => r.forEach((v, j) => {
    if (v != null) { data.push([j, i, v]); if (v > max) max = v }
  }))
  return {
    tooltip: { position: 'top', ...tooltipStyle(), valueFormatter: (v) => shortMoney(v) },
    grid: { left: 8, right: 14, top: 6, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: cols, ...axisTheme(), splitArea: { show: true, areaStyle: { color: ['rgba(128,145,190,.03)', 'rgba(128,145,190,.07)'] } } },
    yAxis: { type: 'category', data: rows, ...axisTheme(), splitArea: { show: true, areaStyle: { color: ['rgba(128,145,190,.03)', 'rgba(128,145,190,.07)'] } } },
    visualMap: {
      min: 0, max: max || 1, calculable: false, orient: 'horizontal', show: false,
      inRange: { color: [colors[0], '#2f8fff', colors[1]] },
    },
    series: [{
      type: 'heatmap', data,
      label: { show: true, fontSize: 10, color: '#cfd8f2', fontFamily: FONT, formatter: (p) => shortMoney(p.value[2]) },
      itemStyle: { borderRadius: 3, borderColor: 'rgba(0,0,0,.2)', borderWidth: 1 },
    }],
  }
}

// ───────────────────────── کارت نمودار ─────────────────────────

export function ChartCard({ title, sub, children, actions, d = 0, height }) {
  const [showMenu, setShowMenu] = useState(false)
  return (
    <div className="card" style={{ '--d': `${d * 0.06}s` }}>
      <div className="card-head">
        <div>
          <h3>{title}</h3>
          {sub && <div className="sub">{sub}</div>}
        </div>
        <div className="card-actions">{actions}</div>
      </div>
      {children}
    </div>
  )
}

// خروجی PNG نمودار: از رویداد اختصاصی استفاده می‌کنیم
export const chartInstances = new Map()

export function PngButton({ chartKey }) {
  return (
    <button className="icon-btn" title="خروجی تصویر"
      onClick={() => {
        const inst = chartInstances.get(chartKey)
        if (!inst) return
        const a = document.createElement('a')
        a.href = inst.getDataURL({ pixelRatio: 2, backgroundColor: '#0c1330' })
        a.download = `${chartKey}.png`
        a.click()
      }}>
      <Icons.download />
    </button>
  )
}

// ───────────────────────── کارت KPI ─────────────────────────

function Spark({ data, color = '#3ee6c8' }) {
  if (!data || data.length < 2) return null
  const max = Math.max(...data), min = Math.min(...data)
  const rng = max - min || 1
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${28 - ((v - min) / rng) * 24}`).join(' ')
  return (
    <div className="spark">
      <svg viewBox="0 0 100 28" preserveAspectRatio="none">
        <polyline points={pts} fill="none" stroke={color} strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" />
        <polygon points={`0,28 ${pts} 100,28`} fill={color} opacity=".12" />
      </svg>
    </div>
  )
}

export function KpiCard({ label, value, unit = 'count', delta, note, spark, icon, color = '#3ee6c8', d = 0 }) {
  const IconC = Icons[icon] || Icons.dashboard
  const display = unit === 'rial' ? shortMoney(value)
    : unit === 'pct' ? `${faNum1(value)}٪`
    : unit === 'score' ? faNum1(value)
    : faNum(value)
  return (
    <div className="card kpi" style={{ '--d': `${d * 0.05}s` }}>
      <div className="k-top">
        <div className="k-label"><span>{label}</span></div>
        <div className="k-icon" style={{ background: color + '22', color }}>
          <IconC />
        </div>
      </div>
      <div className="k-value">
        {display}
        {unit === 'rial' && !/همت|میلیارد|میلیون/.test(String(display)) && <span className="k-unit">ریال</span>}
      </div>
      <div className="row-flex" style={{ justifyContent: 'space-between' }}>
        {delta !== undefined && delta !== null ? (
          <span className={`k-delta ${delta >= 0 ? 'delta-up' : 'delta-down'}`}>
            {delta >= 0 ? '▲' : '▼'} {faNum1(Math.abs(delta))}٪ نسبت به سال قبل
          </span>
        ) : <span />}
        {note && <span className="k-note">{note}</span>}
      </div>
      {spark && <Spark data={spark} color={color} />}
    </div>
  )
}

// ───────────────────────── مدال ─────────────────────────

export function Medal({ medal, score, size = 'sm' }) {
  if (!medal) return <span className="tile">—</span>
  return (
    <span className={`medal ${MEDAL_CLASS[medal] || 'none'}`}>
      <span className="dot">{medal === 'پلاتین' ? 'P' : medal === 'طلا' ? 'G' : medal === 'نقره' ? 'S' : medal === 'برنز' ? 'B' : '•'}</span>
      {medal}
      {score !== undefined && <b style={{ fontSize: 11 }}>{faNum(score)}</b>}
    </span>
  )
}

export function ScoreRing({ score }) {
  return (
    <div className="score-ring" style={{ '--p': score || 0 }}>
      <b>{faNum(score || 0)}</b>
    </div>
  )
}

// ───────────────────────── جدول داده ─────────────────────────

export function DataTable({ cols, rows, sort, dir, onSort, page, per, total, onPage,
  footer, empty = 'داده‌ای یافت نشد', rowKey }) {
  const pages = Math.max(1, Math.ceil(total / per))
  const fmtCell = (row, c) => {
    let v = row[c]
    if (c.includes('amount') && v != null) return faNum(v)
    if ((c === 'score') && v != null) return faNum(v)
    if (v === null || v === undefined || v === '') return <span className="tile">—</span>
    return String(v)
  }
  return (
    <>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} onClick={() => onSort && onSort(c.key)}>
                  {c.label}
                  {sort === c.key && <span style={{ color: 'var(--acc)' }}>{dir === 'desc' ? ' ▾' : ' ▴'}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={cols.length} style={{ textAlign: 'center', color: 'var(--muted)', padding: 24 }}>{empty}</td></tr>
            )}
            {rows.map((r, i) => (
              <tr key={rowKey ? rowKey(r) : i}>
                {cols.map((c) => <td key={c.key} className={c.num ? 'num' : ''}>{c.render ? c.render(r) : fmtCell(r, c.key)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {footer}
      {total > 0 && (
        <div className="pager">
          <button className="btn" disabled={page <= 1} onClick={() => onPage(page - 1)}>قبلی</button>
          <span>صفحه {faNum(page)} از {faNum(pages)} — {faNum(total)} رکورد</span>
          <button className="btn" disabled={page >= pages} onClick={() => onPage(page + 1)}>بعدی</button>
        </div>
      )}
    </>
  )
}

// ───────────────────────── بینش ─────────────────────────

export function InsightCard({ ins, d = 0 }) {
  const cls = ins.type === 'قوت' ? 'q' : ins.type === 'ضعف' ? 'w' : 's'
  return (
    <div className="insight" style={{ '--d': `${d * 0.05}s`, animation: 'fadeUp .5s var(--ease) both' }}>
      <div className={`sev s${ins.severity || 1}`} />
      <div style={{ flex: 1 }}>
        <div className="row-flex" style={{ marginBottom: 4 }}>
          <h4>{ins.title}</h4>
          <span className={`tag ${cls}`}>{ins.type}</span>
        </div>
        <p>{ins.detail}</p>
        {ins.action && <div className="action">پیشنهاد اقدام: {ins.action}</div>}
      </div>
    </div>
  )
}

export function Loading() {
  return <div className="loading">در حال بارگذاری داده‌ها…</div>
}
export function ErrorBox({ err }) {
  return <div className="error">خطا در دریافت داده: {String(err?.message || err)}</div>
}
