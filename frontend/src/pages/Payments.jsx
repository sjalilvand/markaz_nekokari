import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, PngButton, faNum, faNum1, money, shortMoney,
  monthLabel, lineOption, barOption, donutOption, heatmapOption, PALETTE,
} from '../components/ui.jsx'

export default function Payments() {
  const { filters, setFilter, meta } = useFilters()
  const [flow, setFlow] = useState('پرداخت')
  const [trend, setTrend] = useState(null)
  const [compare, setCompare] = useState(null)
  const [cats, setCats] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.trend(filters, { flow }).then(setTrend).catch(setErr)
  }, [filters, flow])
  useEffect(() => {
    api.compare().then(setCompare).catch(setErr)
    api.categories(filters).then(setCats).catch(setErr)
  }, [filters])

  if (err && !trend) return <ErrorBox err={err} />
  if (!trend || !compare) return <Loading />

  const series = trend.series || []
  const labels = series.map((r) => monthLabel(r.y, r.m))
  const methodKey = 'all'
  const amounts = series.map((r) => r.amount)
  const cash = series.map((r) => r.cash)
  const inkind = series.map((r) => r.inkind)

  const annual = trend.annual || []
  const years = compare.years || annual.map((a) => a.y)
  const matrixRows = (compare.province_matrix || []).slice(0, 12)
  const provNames = matrixRows.map((r) => r.province)

  const catFlow = (cats?.categories || []).filter((c) => !flow || c.method)
  const payCats = (cats?.categories || []).filter((c) => flow === 'پرداخت')
  const recvCats = (cats?.categories || []).filter((c) => flow === 'دریافت')
  const catList = (flow === 'پرداخت' ? payCats : recvCats)

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14 }}>
        <span className="crumb"><b>روند {flow}</b> — با تغییر فیلتر سال/استان در نوار بالا، همه نمودارها هم‌زمان به‌روزرسانی می‌شوند</span>
        <div className="spacer" />
        {['پرداخت', 'دریافت'].map((f) => (
          <button key={f} className={`chip ${flow === f ? 'on' : ''}`} onClick={() => setFlow(f)}>{f}</button>
        ))}
      </div>

      <ChartCard title={`روند ماهانه ${flow}ها`} sub="میانگین متحرک ۳ ماهه — برای تحلیل فصلی کمپین‌ها" d={0}
        actions={<PngButton chartKey="pm-trend" />}>
        <Chart chartKey="pm-trend" height={340} option={{
          color: ['#3ee6c8', '#8f9dff', '#ffb35c'],
          tooltip: { trigger: 'axis', ...{ backgroundColor: 'rgba(10,16,38,.94)', borderColor: 'rgba(143,157,255,.4)', textStyle: { color: '#eaeefb', fontSize: 12 } } },
          legend: { data: ['مبلغ', 'میانگین متحرک ۳م', 'نقدی'], textStyle: { color: '#98a5c6', fontSize: 11.5 }, top: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 8 },
          grid: { left: 8, right: 14, top: 34, bottom: 8, containLabel: true },
          xAxis: { type: 'category', data: labels, axisLabel: { color: '#98a5c6', fontSize: 10.5, rotate: 45 } },
          yAxis: { type: 'value', axisLabel: { color: '#98a5c6', fontSize: 11, formatter: (v) => shortMoney(v) }, splitLine: { lineStyle: { color: 'rgba(128,145,190,.15)' } } },
          series: [
            { name: 'مبلغ', type: 'bar', data: amounts, barMaxWidth: 14, itemStyle: { borderRadius: [4, 4, 0, 0], color: '#3ee6c8' } },
            { name: 'میانگین متحرک ۳م', type: 'line', data: series.map((r) => r.ma3 || null), smooth: true, showSymbol: false, lineStyle: { width: 2.4, color: '#ffb35c' } },
            { name: 'نقدی', type: 'line', data: cash, smooth: true, showSymbol: false, lineStyle: { width: 1.8, color: '#8f9dff' } },
          ],
        }} />
      </ChartCard>

      <div className="grid g2">
        <ChartCard title="مقایسه سالانه" sub="پرداخت، دریافت و رشد سالانه" d={1} actions={<PngButton chartKey="pm-compare" />}>
          <Chart chartKey="pm-compare" height={300} option={barOption({
            labels: annual.map((a) => a.y),
            data: [annual.map((a) => a.payments), annual.map((a) => a.receipts)],
            legends: ['پرداخت', 'دریافت'],
          })} />
          <div className="row-flex" style={{ marginTop: 8 }}>
            {annual.map((a) => (
              <span key={a.y} className="chip">سال {faNum(a.y)}:
                {' '}{shortMoney(a.payments)}
                {a.growth !== null && a.growth !== undefined && (
                  <b style={{ color: a.growth >= 0 ? 'var(--green)' : 'var(--red)', marginInlineStart: 6 }}>
                    {a.growth >= 0 ? '▲' : '▼'} {faNum1(Math.abs(a.growth))}٪
                  </b>
                )}
              </span>
            ))}
          </div>
        </ChartCard>
        <ChartCard title="ترکیب نقدی / غیرنقدی سالانه" sub="سهم دو روش پرداخت در هر سال" d={2} actions={<PngButton chartKey="pm-stack" />}>
          <Chart chartKey="pm-stack" height={300} option={barOption({
            labels: annual.map((a) => a.y),
            data: [annual.map((a) => a.cash), annual.map((a) => a.inkind)],
            legends: ['نقدی', 'غیرنقدی'],
            stacked: true,
          })} />
          <div className="hint">جمع این دو، برابر «جمع پرداخت» سال است؛ الگوی واقعی فایل مالی استانی بازتولید شده است.</div>
        </ChartCard>
      </div>

      <div className="grid g23">
        <ChartCard title={`فعالیت‌های ${flow}`} sub="دسته‌بندی مبالغ بر اساس نام فعالیت/گروه فعالیت" d={3}
          actions={<PngButton chartKey="pm-cats" />}>
          <Chart chartKey="pm-cats" height={340} option={barOption({
            labels: catList.map((r) => r.label || 'نامشخص'),
            data: [catList.map((r) => r.s)],
            legends: ['مبلغ'],
            horizontal: true,
          })} onClick={(p) => { /* cross-filter by category is shown in tooltip */ }} />
        </ChartCard>
        <ChartCard title="منابع مالی" sub="سهم منبع کمک‌ها در دریافت‌ها" d={4} actions={<PngButton chartKey="pm-src" />}>
          <Chart chartKey="pm-src" height={340} option={donutOption({
            data: (cats?.sources || []).map((r) => ({ name: r.label, value: r.s })),
          })} />
          <div className="hint">وضعیت تحت پوشش ذی‌نفعان: {(cats?.coverage || []).map((c) => `${c.label}: ${faNum(c.s)}`).join(' | ') || '—'}</div>
        </ChartCard>
      </div>

      <ChartCard title="ماتریس استان × سال" sub="جمع پرداخت هر استان در هر سال (۱۲ استان برتر)" d={5}
        actions={<PngButton chartKey="pm-heat" />}>
        <Chart chartKey="pm-heat" height={380} option={heatmapOption({
          rows: provNames,
          cols: years.map((y) => faNum(y)),
          values: matrixRows.map((r) => years.map((y) => r[y] || 0)),
        })} onClick={(p) => {
          const row = matrixRows[p.value[1]]
          if (row) setFilter('province', String((meta?.provinces || []).find((x) => x.name === row.province)?.id || 'all'))
        }} />
        <div className="hint">کلیک روی هر خانه: اعمال فیلتر استان. مقادیر به «هزار میلیارد ریال» خلاصه‌سازی شده‌اند.</div>
      </ChartCard>
    </>
  )
}
