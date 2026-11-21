import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, KpiCard, InsightCard, PngButton, faNum, faNum1,
  gaugeOption, PALETTE,
} from '../components/ui.jsx'

const UNITS = { percent: 'درصد', count: 'عدد', rial: 'ریال' }

export default function Kpis() {
  const { filters } = useFilters()
  const [d, setD] = useState(null)
  const [ins, setIns] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.kpis(filters).then(setD).catch(setErr)
    api.insights(filters).then(setIns).catch(setErr)
  }, [filters])

  if (err && !d) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const kpis = d.kpis || []
  const gauges = kpis.filter((k) => k.unit === 'percent').slice(0, 6)
  const GAUGE_COLORS = ['#3ee6c8', '#5aa7ff', '#c79dff', '#4ade80', '#ffb35c', '#ff8fb8']

  return (
    <>
      <div className="grid g4">
        {kpis.map((k, i) => (
          <KpiCard key={k.key} label={k.label}
            value={k.value} unit={k.unit === 'percent' ? 'pct' : 'count'}
            note={`هدف: ${faNum(k.target)}${k.unit === 'percent' ? '٪' : ''} — ${UNITS[k.unit] || ''}`}
            icon={k.direction === 'up' ? 'trend' : 'gauge'}
            color={k.status === 'ok' ? '#4ade80' : k.status === 'warn' ? '#ffb35c' : '#ff7b7b'}
            d={i} spark={k.spark || undefined} />
        ))}
      </div>

      <ChartCard title="نمای عقربه‌ای شاخص‌های درصدی" sub="تحقق هدف هر شاخص (مانند KPI Cards در Power BI)" d={1}
        actions={<PngButton chartKey="kp-gauge" />}>
        <div className="grid g3" style={{ margin: 0 }}>
          {gauges.map((k, i) => (
            <div key={k.key}>
              <Chart chartKey={`gp-${i}`} height={190} option={gaugeOption({
                value: Math.min(k.value, 100), color: GAUGE_COLORS[i % GAUGE_COLORS.length],
              })} />
              <div className="row-flex" style={{ justifyContent: 'center', gap: 8 }}>
                <b style={{ fontSize: 13 }}>{k.label}</b>
                <span className={`tag ${k.status === 'ok' ? 'q' : k.status === 'warn' ? 's' : 'w'}`}>
                  تحقق {faNum1(k.attainment || 0)}٪
                </span>
              </div>
              <div className="hint" style={{ textAlign: 'center' }}>{k.desc}</div>
            </div>
          ))}
        </div>
      </ChartCard>

      <div className="grid g32">
        <ChartCard title="کارنامه کامل شاخص‌ها" d={2} sub="مقدار، هدف، تحقق و وضعیت">
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>شاخص</th><th>مقدار</th><th>هدف</th><th>تحقق</th><th>وضعیت</th><th>شرح</th></tr></thead>
              <tbody>
                {kpis.map((k) => (
                  <tr key={k.key}>
                    <td><b>{k.label}</b></td>
                    <td className="num">{faNum1(k.value)}{k.unit === 'percent' ? '٪' : ''}</td>
                    <td className="num">{faNum(k.target)}{k.unit === 'percent' ? '٪' : ''}</td>
                    <td className="num">{k.attainment !== null && k.attainment !== undefined ? faNum1(k.attainment) + '٪' : '—'}</td>
                    <td>
                      <span className={`tag ${k.status === 'ok' ? 'q' : k.status === 'warn' ? 's' : 'w'}`}>
                        {k.status === 'ok' ? 'مطلوب' : k.status === 'warn' ? 'هشدار' : 'بحرانی'}
                      </span>
                    </td>
                    <td className="tile">{k.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="hint">مبدأ مقایسه سالانه: جدول پرداخت‌های سالانه سامانه (۱۴۰۳ تا ۱۴۰۵).</div>
        </ChartCard>
        <ChartCard title="بینش‌ها و اقدام‌های پیشنهادی" d={3} sub="موتور قواعد روی داده زنده">
          {(ins?.insights || []).map((x, i) => <InsightCard key={i} ins={x} d={i} />)}
        </ChartCard>
      </div>
    </>
  )
}
