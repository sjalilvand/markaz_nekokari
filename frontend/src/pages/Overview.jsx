import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, KpiCard, Loading, ErrorBox, InsightCard, PngButton, faNum, money,
  shortMoney, monthLabel, lineOption, barOption, donutOption, PALETTE, Medal,
} from '../components/ui.jsx'

export default function Overview() {
  const { filters, meta, setFilter } = useFilters()
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    setD(null)
    api.overview(filters).then(setD).catch(setErr)
  }, [filters])

  if (err) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const monthly = d.monthly || []
  const labels = monthly.map((r) => monthLabel(r.y, r.m))
  const yearLabels = Object.keys(d.yearly || {}).sort()

  const kpiIcons = { payments: 'coins', receipts: 'trend', balance: 'report', requests: 'report',
    centers: 'building', members: 'people', needy: 'heart', hamyaran: 'people' }
  const kpiColors = { payments: '#3ee6c8', receipts: '#5aa7ff', balance: '#8f9dff',
    requests: '#ffb35c', centers: '#4ade80', members: '#b98cff', needy: '#ff8fb8', hamyaran: '#c79dff' }

  return (
    <>
      <div className="grid g4">
        {d.kpis.map((k, i) => (
          <KpiCard key={k.key} {...k} unit={k.unit === 'rial' ? 'rial' : k.unit}
            icon={kpiIcons[k.key]} color={kpiColors[k.key]} d={i}
            spark={k.key === 'payments' || k.key === 'receipts'
              ? monthly.map((r) => k.key === 'payments' ? r.payments : r.receipts) : undefined} />
        ))}
      </div>

      <div className="grid g23">
        <ChartCard title="روند ماهانه دریافت و پرداخت" sub="تمام دوره‌های موجود — با کلیک روی نمودار استان‌ها فیلتر می‌شوند"
          d={1} actions={<PngButton chartKey="ov-trend" />}>
          <Chart chartKey="ov-trend" height={300} option={lineOption({
            labels,
            legends: ['پرداخت', 'دریافت'],
            series: [monthly.map((r) => r.payments), monthly.map((r) => r.receipts)],
          })} />
        </ChartCard>
        <ChartCard title="ترکیب درخواست‌ها" sub="دسته‌بندی درخواست‌های ثبت‌شده" d={2}>
          <Chart chartKey="ov-donut" height={300} option={donutOption({
            data: (d.req_categories || []).map((r, i) => ({
              name: r.label || 'سایر', value: r.s,
              itemStyle: { color: PALETTE[i % PALETTE.length] },
            })),
            colors: PALETTE,
          })} />
          <div className="hint">درخواست‌ها شامل ثبت نیازمند، دریافت/پرداخت نقدی و غیرنقدی، خرید کالا و امور اداری است.</div>
        </ChartCard>
      </div>

      <div className="grid g23">
        <ChartCard title="۱۰ استان برتر از نظر پرداخت" sub="کلیک روی هر ستون = فیلتر سراسری استان" d={3}
          actions={<PngButton chartKey="ov-prov" />}>
          <Chart chartKey="ov-prov" height={300} option={barOption({
            labels: d.top_provinces.map((r) => r.name),
            data: [d.top_provinces.map((r) => r.s)],
            legends: ['پرداخت (ریال)'],
            horizontal: true,
          })} onClick={(p) => {
            const hit = d.top_provinces[p.dataIndex]
            if (hit) { setFilter('province', String(hit.id)); nav('/provinces') }
          }} />
        </ChartCard>
        <ChartCard title="مقایسه سالانه" sub="جمع پرداخت و دریافت به تفکیک سال" d={4}
          actions={<PngButton chartKey="ov-year" />}>
          <Chart chartKey="ov-year" height={300} option={barOption({
            labels: yearLabels,
            data: [yearLabels.map((y) => d.yearly[y].payments), yearLabels.map((y) => d.yearly[y].receipts)],
            legends: ['پرداخت', 'دریافت'],
          })} />
          <div className="hint">
            {d.prev_year ? `پرداخت ${d.cur_year} نسبت به ${d.prev_year}: ` +
              faNum(d.kpis[0]?.delta ?? 0) + '٪ تغییر' : ''}
          </div>
        </ChartCard>
      </div>

      <div className="grid g32">
        <ChartCard title="مراکز پرداخت‌کننده برتر" sub="ده مرکز با بیشترین حجم پرداخت" d={5}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>مرکز</th><th>استان</th><th>مدال</th><th>پرداخت</th></tr></thead>
              <tbody>
                {d.top_centers.map((c) => (
                  <tr key={c.id}>
                    <td>{c.name}</td>
                    <td>{c.prov}</td>
                    <td><Medal medal={c.medal} /></td>
                    <td className="num">{shortMoney(c.s)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
        <ChartCard title="بینش‌های خودکار و پیشنهاد بهبود" sub="بر اساس قواعد تحلیلی روی داده‌ها" d={6}>
          {d.insights.map((ins, i) => <InsightCard key={i} ins={ins} d={i} />)}
          <div className="hint">مجموعه کامل بینش‌ها و پیشنهادها در داشبورد شاخص‌ها و گزارش متنی موجود است.</div>
        </ChartCard>
      </div>

      <ChartCard title="ترکیب روش پرداخت" sub="سهم نقدی و غیرنقدی در دوره انتخابی" d={7}>
        <Chart chartKey="ov-method" height={220} option={donutOption({
          data: (d.pay_by_method || []).map((r, i) => ({ name: r.label, value: r.value })),
          colors: ['#3ee6c8', '#8f9dff'],
          radius: ['45%', '72%'],
        })} />
        <div className="hint">جمع پرداخت دوره: {money(d.kpis[0]?.value)}</div>
      </ChartCard>
    </>
  )
}
