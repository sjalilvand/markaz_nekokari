import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, PngButton, faNum, faNum1, shortMoney,
  barOption, donutOption, PALETTE,
} from '../components/ui.jsx'

export default function Analytics() {
  const { filters } = useFilters()
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setD(null)
    api.demographics(filters).then(setD).catch(setErr)
  }, [filters])

  if (err) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const genderMap = Object.fromEntries((d.gender || []).map((g) => [g.label, g.n]))

  return (
    <>
      <div className="grid g4">
        <div className="card" style={{ '--d': '0s' }}>
          <div className="card-head"><div><h3>میانگین سن نیازمندان</h3></div></div>
          <div className="k-value">{faNum1(d.age_stats?.mean)} <span className="k-unit">سال</span></div>
          <div className="hint">بر اساس همه رکوردهای دارای سن</div>
        </div>
        <div className="card" style={{ '--d': '0.05s' }}>
          <div className="card-head"><div><h3>تمرکز دهک ۱ و ۲</h3></div></div>
          <div className="k-value">{faNum1(((d.decile || []).filter((x) => x.d <= 2).reduce((a, b) => a + b.n, 0) /
            Math.max((d.decile || []).reduce((a, b) => a + b.n, 0), 1)) * 100)}٪</div>
          <div className="hint">سهم فقر شدید از نیازمندان دارای اطلاعات دهک</div>
        </div>
        <div className="card" style={{ '--d': '0.1s' }}>
          <div className="card-head"><div><h3>ترکیب جنسیتی</h3></div></div>
          <div className="k-value">{faNum1((genderMap['خانم'] || 0) / Math.max((genderMap['خانم'] || 0) + (genderMap['آقا'] || 0), 1) * 100)}٪ خانم</div>
          <div className="hint">خانم: {faNum(genderMap['خانم'])} — آقا: {faNum(genderMap['آقا'])}</div>
        </div>
        <div className="card" style={{ '--d': '0.15s' }}>
          <div className="card-head"><div><h3>در قید حیات</h3></div></div>
          <div className="k-value">{faNum1(((d.vital || []).find((v) => v.label === 'در قید حیات')?.n || 0) /
            Math.max((d.vital || []).reduce((a, b) => a + b.n, 0), 1) * 100)}٪</div>
          <div className="hint">به‌روزرسانی وضعیت مددجویان</div>
        </div>
      </div>

      <div className="grid g2">
        <ChartCard title="توزیع سنی نیازمندان" sub="هیستوگرام سنی — الگوی واقعی داده" d={1}
          actions={<PngButton chartKey="an-age" />}>
          <Chart chartKey="an-age" height={280} option={barOption({
            labels: d.age_hist.map((r) => r.label),
            data: [d.age_hist.map((r) => r.value)],
            legends: ['تعداد نیازمند'],
          })} />
        </ChartCard>
        <ChartCard title="توزیع دهک رفاه" sub="دهک ۱ = فقر شدید" d={2} actions={<PngButton chartKey="an-decile" />}>
          <Chart chartKey="an-decile" height={280} option={barOption({
            labels: (d.decile || []).map((r) => 'دهک ' + faNum(r.d)),
            data: [(d.decile || []).map((r) => r.n)],
            legends: ['تعداد'],
          })} />
        </ChartCard>
      </div>

      <div className="grid g23">
        <ChartCard title="نوع نیازمند" sub="طبقه‌بندی مددجویان امداد، سابق امداد، محله و بهزیستی" d={3}
          actions={<PngButton chartKey="an-needtype" />}>
          <Chart chartKey="an-needtype" height={300} option={barOption({
            labels: (d.need_types || []).map((r) => r.label),
            data: [(d.need_types || []).map((r) => r.n)],
            legends: ['تعداد'],
            horizontal: true,
          })} />
        </ChartCard>
        <ChartCard title="جنسیت نیازمندان" sub="سهم خانم و آقا" d={4}>
          <Chart chartKey="an-gender" height={300} option={donutOption({
            data: (d.gender || []).map((r) => ({ name: r.label, value: r.n })),
            colors: ['#ff8fb8', '#5aa7ff'],
          })} />
          <div className="hint">
            میانگین سن خانم‌ها {faNum1((d.age_gender || []).find((g) => g.gender === 'خانم')?.avg_age || 0)} سال و
            آقایان {faNum1((d.age_gender || []).find((g) => g.gender === 'آقا')?.avg_age || 0)} سال است.
          </div>
        </ChartCard>
      </div>

      <div className="grid g2">
        <ChartCard title="گروه‌های نیازمندی" sub="فقط رکوردهای دارای گروه نیازمندی (الگوی واقعی)" d={5}
          actions={<PngButton chartKey="an-groups" />}>
          <Chart chartKey="an-groups" height={320} option={barOption({
            labels: (d.need_groups || []).map((r) => r.label),
            data: [(d.need_groups || []).map((r) => r.n)],
            legends: ['تعداد'],
            horizontal: true,
          })} />
          <div className="hint">توصیه: ثبت «گروه نیازمندی» برای همه مددجویان اجباری شود تا تحلیل نوع نیاز کامل شود.</div>
        </ChartCard>
        <ChartCard title="میانگین سن به تفکیک دهک" sub="ارتباط سن و شدت فقر" d={6} actions={<PngButton chartKey="an-decage" />}>
          <Chart chartKey="an-decage" height={320} option={barOption({
            labels: (d.dec_age || []).map((r) => 'دهک ' + faNum(r.d)),
            data: [(d.dec_age || []).map((r) => Math.round(r.avg_age * 10) / 10)],
            legends: ['میانگین سن'],
          })} />
        </ChartCard>
      </div>

      <ChartCard title="۱۰ اداره پرنیازمند" sub="به تفکیک اداره شهرستان" d={7} actions={<PngButton chartKey="an-offices" />}>
        <Chart chartKey="an-offices" height={320} option={barOption({
          labels: (d.top_offices || []).map((r) => r.label),
          data: [(d.top_offices || []).map((r) => r.n)],
          legends: ['نیازمند'],
          horizontal: true,
        })} />
      </ChartCard>
    </>
  )
}
