import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, PngButton, DataTable, Medal, faNum, faNum1,
  money, shortMoney, barOption, gaugeOption, PALETTE,
} from '../components/ui.jsx'

const METRICS = [
  { key: 'payments', label: 'جمع پرداخت', unit: 'rial' },
  { key: 'receipts', label: 'جمع دریافت', unit: 'rial' },
  { key: 'pay_per_needy', label: 'سرانه پرداخت (هر نیازمند)', unit: 'rial' },
  { key: 'pay_per_center', label: 'سرانه پرداخت (هر مرکز)', unit: 'rial' },
  { key: 'needy', label: 'شمار نیازمندان', unit: 'count' },
  { key: 'centers', label: 'شمار مراکز', unit: 'count' },
  { key: 'hamyaran_per_1000', label: 'همیار به ازای هزار نیازمند', unit: 'count' },
  { key: 'avg_score', label: 'میانگین امتیاز مراکز', unit: 'score' },
]

// موقعیت تقریبی استان‌ها روی نقشه کاشی (x,y) — بر مبنای جغرافیای ایران
const TILE = {
  'آذربایجان غربی': [1, 2], 'آذربایجان شرقی': [2, 2], 'اردبیل': [2.4, 3.4], 'گیلان': [2, 4.6],
  'زنجان': [2.6, 4.2], 'کردستان': [1.4, 3.8], 'کرمانشاه': [1, 4.6], 'همدان': [1.8, 5.0],
  'مازندران': [3.2, 4.9], 'تهران': [2.6, 5.2], 'البرز': [2.1, 5.3], 'سمنان': [3.4, 5.6],
  'قزوین': [2.2, 4.6], 'مرکزی': [2.5, 5.8], 'قم': [2.9, 5.9], 'اصفهان': [3.3, 6.6],
  'لرستان': [1.9, 6.1], 'خوزستان': [1.3, 6.8], 'چهارمحال و بختیاری': [2.6, 6.8],
  'کهگیلویه و بویراحمد': [1.9, 7.4], 'یزد': [3.8, 6.8], 'فارس': [2.4, 8.0], 'بوشهر': [1.4, 8.2],
  'هرمزگان': [3.4, 8.9], 'کرمان': [4.4, 7.6], 'سیستان و بلوچستان': [5.4, 7.6],
  'خراسان شمالی': [4.8, 4.4], 'خراسان رضوی': [5.4, 5.0], 'خراسان جنوبی': [4.9, 5.9],
  'گلستان': [4.0, 3.8], 'ایلام': [0.8, 5.8],
}

export default function Provinces() {
  const { filters, meta, setFilter } = useFilters()
  const [d, setD] = useState(null)
  const [fin, setFin] = useState(null)
  const [metric, setMetric] = useState('payments')
  const [sel, setSel] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setD(null)
    api.provinces(filters).then(setD).catch(setErr)
  }, [filters])
  useEffect(() => { api.finance().then(setFin).catch(() => {}) }, [])

  const rows = useMemo(() => {
    if (!d) return []
    const arr = [...d.rows]
    arr.sort((a, b) => (b[metric] || 0) - (a[metric] || 0))
    return arr
  }, [d, metric])

  if (err) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const mdef = METRICS.find((m) => m.key === metric)
  const fmtVal = (v) => mdef.unit === 'rial' ? shortMoney(v) : faNum1(v)
  const selected = sel || rows[0]
  const provIdOf = (name) => meta?.provinces?.find((p) => p.name === name)?.id

  const tileData = rows.map((r) => ({
    name: r.name,
    value: [TILE[r.name]?.[0], TILE[r.name]?.[1], r[metric] || 0],
    provinceId: r.id,
  }))

  const cols = [
    { key: 'name', label: 'استان', render: (r) => <b>{r.name}</b> },
    { key: 'medal', label: 'مدال', render: (r) => <Medal medal={r.medal} score={Math.round(r.avg_score || 0)} /> },
    { key: 'centers', label: 'مراکز', num: true },
    { key: 'members', label: 'اعضای فعال', num: true },
    { key: 'needy', label: 'نیازمندان', num: true },
    { key: 'hamyaran', label: 'همیاران', num: true },
    { key: 'requests', label: 'درخواست‌ها', num: true },
    { key: 'payments', label: 'پرداخت', num: true, render: (r) => shortMoney(r.payments) },
    { key: 'receipts', label: 'دریافت', num: true, render: (r) => shortMoney(r.receipts) },
    { key: 'pay_per_needy', label: 'سرانه/نیازمند', num: true, render: (r) => shortMoney(r.pay_per_needy) },
    { key: 'share', label: 'سهم', num: true, render: (r) => faNum1(r.share) + '٪' },
  ]

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14 }}>
        <span className="crumb">معیار رتبه‌بندی:</span>
        {METRICS.map((m) => (
          <button key={m.key} className={`chip ${metric === m.key ? 'on' : ''}`}
            onClick={() => setMetric(m.key)}>{m.label}</button>
        ))}
      </div>

      <div className="grid g23">
        <ChartCard title={`رتبه‌بندی استان‌ها — ${mdef.label}`} sub="کلیک روی هر استان: جزئیات + فیلتر سراسری" d={0}
          actions={<PngButton chartKey="pv-rank" />}>
          <Chart chartKey="pv-rank" height={520} option={barOption({
            labels: rows.map((r) => r.name),
            data: [rows.map((r) => r[metric] || 0)],
            legends: [mdef.label],
            horizontal: true,
          })} onClick={(p) => {
            const r = [...rows].sort((a, b) => a.name.localeCompare(b.name))[p.dataIndex]
            if (r) { setSel(r); setFilter('province', String(r.id)) }
          }} />
        </ChartCard>
        <div>
          <ChartCard title="نقشه کاشی استان‌ها" sub="رنگ بر اساس معیار انتخابی — کلیک = فیلتر" d={1}
            actions={<PngButton chartKey="pv-tile" />}>
            <Chart chartKey="pv-tile" height={430} option={{
              tooltip: {
                formatter: (p) => `${p.data.name}: ${fmtVal(p.data.value[2])}`,
                backgroundColor: 'rgba(10,16,38,.94)', borderColor: 'rgba(143,157,255,.4)',
                textStyle: { color: '#eaeefb', fontSize: 12 },
              },
              visualMap: {
                min: 0, max: Math.max(...rows.map((r) => r[metric] || 0), 1), show: false,
                inRange: { color: ['#173a5e', '#2f8fff', '#3ee6c8'] },
              },
              series: [{
                type: 'scatter', symbolSize: 42,
                label: { show: true, formatter: (p) => p.data.name.slice(0, 6), fontSize: 9.5,
                  color: '#eaeefb', fontFamily: "'Vazirmatn', sans-serif", position: 'inside' },
                itemStyle: { borderRadius: 10, opacity: .9 },
                emphasis: { scale: 1.15 },
                data: tileData,
              }],
              xAxis: { show: false, min: 0, max: 6 }, yAxis: { show: false, min: 0, max: 10, inverse: true },
            }} onClick={(p) => {
              if (p.data.provinceId) { setSel(rows.find((r) => r.id === p.data.provinceId)); setFilter('province', String(p.data.provinceId)) }
            }} />
            <div className="hint">کاشی‌بندی جغرافیایی تقریبی استان‌ها (بدون نیاز به فایل جیوان).</div>
          </ChartCard>
          {selected && (
            <div className="card" style={{ marginTop: 14, '--d': '0.1s' }}>
              <div className="card-head">
                <div><h3>جزئیات {selected.name}</h3><div className="sub">کلیک روی نمودارها جزئیات را عوض می‌کند</div></div>
                <Medal medal={selected.medal} score={Math.round(selected.avg_score || 0)} />
              </div>
              <div className="keynums" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                <div className="keynum"><b>{shortMoney(selected.payments)}</b><span>پرداخت</span></div>
                <div className="keynum"><b>{shortMoney(selected.receipts)}</b><span>دریافت</span></div>
                <div className="keynum"><b>{shortMoney(selected.balance)}</b><span>مانده</span></div>
                <div className="keynum"><b>{faNum(selected.centers)}</b><span>مراکز</span></div>
                <div className="keynum"><b>{faNum(selected.needy)}</b><span>نیازمندان</span></div>
                <div className="keynum"><b>{faNum1(selected.hamyaran_per_1000)}</b><span>همیار/هزار نیازمند</span></div>
              </div>
              <button className="btn" onClick={() => setFilter('province', 'all')}>حذف فیلتر استان</button>
            </div>
          )}
        </div>
      </div>

      <ChartCard title="جمع‌بندی مالی استانی (بر اساس فایل گزارش واقعی)" d={2}
        sub="ارسال‌شده در «گزارش دریافت و پرداخت به تفکیک استان» — ارقام مرجع">
        {fin && (
          <Chart chartKey="pv-fin" height={420} option={barOption({
            labels: fin.rows.map((r) => r.province),
            data: [
              fin.rows.map((r) => r['جمع دریافت'] || 0),
              fin.rows.map((r) => r['جمع پرداخت'] || 0),
              fin.rows.map((r) => r['باقی مانده'] || 0),
            ],
            legends: ['جمع دریافت', 'جمع پرداخت', 'باقی‌مانده'],
          })} />
        )}
        <div className="hint">جمع کل کشور: دریافت {money(fin?.rows?.reduce((a, r) => a + (r['جمع دریافت'] || 0), 0))} —
          پرداخت {money(fin?.rows?.reduce((a, r) => a + (r['جمع پرداخت'] || 0), 0))}</div>
      </ChartCard>

      {fin && fin.compensation?.length > 0 && (
        <ChartCard title="جبران خدمات به تفکیک استان (تایید شده / نشده)" d={3}
          sub="الگوی فایل «جبران خدمات به تفکیک استان»">
          <Chart chartKey="pv-comp" height={400} option={barOption({
            labels: fin.compensation.map((r) => r.name),
            data: [fin.compensation.map((r) => r.centers_ok), fin.compensation.map((r) => r.centers_not_ok + r.centers_review)],
            legends: ['مراکز تایید شده', 'تایید نشده / در بررسی'],
            stacked: true,
          })} />
        </ChartCard>
      )}

      <ChartCard title="جدول کامل عملکرد استان‌ها" d={4} sub="مرتب‌سازی با کلیک روی ستون‌ها">
        <DataTable cols={cols} rows={rows} total={rows.length} page={1} per={rows.length}
          onPage={() => { }} rowKey={(r) => r.id}
          onSort={(k) => {
            const m = METRICS.find((x) => x.key === k)
            if (m) setMetric(k)
          }} />
      </ChartCard>
    </>
  )
}
