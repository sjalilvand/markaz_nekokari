import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, KpiCard, faNum, faNum1, shortMoney,
  lineOption, barOption, donutOption, PALETTE, MONTHS,
} from '../components/ui.jsx'

// ─── عملکرد دوره‌ای: مقایسه دو سال به تفکیک ماه، استان، مرکز، نوع خدمت و نیازمندان ───

export default function Performance() {
  const { filters, meta } = useFilters()
  const years = meta?.years?.length ? meta.years : [1404, 1405]
  const latest = years[years.length - 1]
  const [year1, setYear1] = useState(filters.year !== 'all' ? +filters.year : latest)
  const [year2, setYear2] = useState(latest > years[0] ? latest - 1 : '')
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setD(null)
    api.performance({
      year1, year2: year2 || '',
      province: filters.province, office: filters.office,
    }).then(setD).catch(setErr)
  }, [filters, year1, year2])

  if (err && !d) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const hasData = (d.totals?.y1?.pay || 0) + (d.totals?.y2?.pay || 0) > 0
  const t1 = d.totals?.y1 || {}
  const t2 = d.totals?.y2 || {}
  const growth = d.totals?.growth_pay

  // روند ماهانه دو سال
  const monthLabels = MONTHS
  const monthlySeries = [
    { name: `پرداخت ${d.year1}`, data: d.months.map((r) => r.pay1) },
  ]
  if (d.year2) monthlySeries.push({ name: `پرداخت ${d.year2}`, data: d.months.map((r) => r.pay2) })
  monthlySeries.push({ name: `دریافت ${d.year1}`, data: d.months.map((r) => r.rec1) })
  if (d.year2) monthlySeries.push({ name: `دریافت ${d.year2}`, data: d.months.map((r) => r.rec2) })

  const provLabels = (d.provinces || []).map((p) => p.name)
  const provPay1 = (d.provinces || []).map((p) => p.pay1 || 0)
  const provPay2 = (d.provinces || []).map((p) => p.pay2 || 0)

  const svcLabels = (d.services || []).map((s) => s.label || 'نامشخص')
  const svcPay1 = (d.services || []).map((s) => s.pay1 || 0)
  const svcPay2 = (d.services || []).map((s) => s.pay2 || 0)

  const bestMonth = [...d.months].sort((a, b) => (b.pay1 || 0) - (a.pay1 || 0))[0]
  const weakMonth = [...d.months].sort((a, b) => (a.pay1 || 0) - (b.pay1 || 0))[0]

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14, flexWrap: 'wrap' }}>
        <span className="crumb"><b>عملکرد دوره‌ای</b> — مقایسه دو سال به تفکیک ماه، استان، مرکز، نوع خدمت و نیازمندان؛ فیلتر استان/اداره از نوار بالا اعمال می‌شود</span>
        <div className="spacer" />
        <label style={{ fontSize: 12 }}>سال اول:</label>
        <select value={year1} onChange={(e) => setYear1(+e.target.value)}>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>سال دوم:</label>
        <select value={year2} onChange={(e) => setYear2(e.target.value ? +e.target.value : '')}>
          <option value="">— بدون مقایسه —</option>
          {years.filter((y) => y !== year1).map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {!hasData && (
        <div className="error" style={{ background: 'rgba(255,179,92,.12)', borderColor: '#ffb35c' }}>
          برای این بازه تراکنشی با سال مشخص ثبت نشده است. اگر فایل‌های پرداخت/دریافت را پیش از این بارگذاری کرده‌اید،
          آن‌ها را دوباره در صفحه «بارگذاری و کیفیت داده» وارد کنید تا ستون تاریخ به‌درستی شناسایی شود.
        </div>
      )}

      <div className="grid g4">
        <KpiCard label={`پرداخت سال ${d.year1}`} value={t1.pay} unit="rial" icon="coins"
          color="#3ee6c8" note={`${faNum(t1.cnt)} تراکنش`} d={0} />
        {d.year2 ? (
          <KpiCard label={`پرداخت سال ${d.year2}`} value={t2.pay} unit="rial" icon="coins"
            color="#8f9dff" note={`${faNum(t2.cnt)} تراکنش`} d={1} />
        ) : <KpiCard label="مقایسه سال دوم" value={0} unit="count" icon="trend" note="سال دوم انتخاب نشده" d={1} />}
        <KpiCard label={`ذی‌نفعان ${d.year1}`} value={t1.ben} unit="count" icon="people" color="#c79dff" d={2}
          note="جمع تعداد ذی‌نفع تراکنش‌ها" />
        {growth !== null && growth !== undefined ? (
          <KpiCard label={`رشد پرداخت ${d.year2} نسبت به ${d.year1}`} value={Math.abs(growth)}
            unit="pct" icon="trend" color={growth >= 0 ? '#4ade80' : '#ff7b7b'}
            delta={growth} d={3} note={growth >= 0 ? 'روند صعودی' : 'روند نزولی'} />
        ) : (
          <KpiCard label="رشد سالانه" value={0} unit="count" icon="trend" note="برای محاسبه، سال دوم را انتخاب کنید" d={3} />
        )}
      </div>

      <ChartCard title={`روند ماهانه پرداخت و دریافت — ${d.year1}${d.year2 ? ` در برابر ${d.year2}` : ''}`}
        sub={bestMonth ? `اوج پرداخت ${d.year1}: ${MONTHS[(bestMonth.month || 1) - 1]} — کمترین: ${MONTHS[(weakMonth?.month || 1) - 1]}` : 'داده ماهانه موجود نیست'}
        d={1}>
        <Chart chartKey="pf-monthly" height={360} option={lineOption({
          labels: monthLabels,
          series: monthlySeries.map((s) => s.data),
          legends: monthlySeries.map((s) => s.name),
        })} />
        <div className="hint">مقایسه هم‌دوره‌ای ماه‌های دو سال، الگوی فصلی کمپین‌ها (رمضان، محرم، اسفند) را آشکار می‌کند.</div>
      </ChartCard>

      <div className="grid g2">
        <ChartCard title="مقایسه استانی" sub="جمع پرداخت به تفکیک استان برای دو سال" d={2}>
          {provLabels.length === 0 ? <div className="hint">داده استانی برای این بازه نیست.</div> : (
            <Chart chartKey="pf-prov" height={Math.min(520, 180 + provLabels.length * 30)} option={barOption({
              labels: provLabels,
              data: d.year2 ? [provPay1, provPay2] : [provPay1],
              legends: d.year2 ? [`پرداخت ${d.year1}`, `پرداخت ${d.year2}`] : [`پرداخت ${d.year1}`],
              horizontal: true,
            })} />
          )}
        </ChartCard>
        <ChartCard title="مقایسه نوع خدمت" sub="سهم فعالیت‌ها در پرداخت‌های دو سال" d={3}>
          {svcLabels.length === 0 ? <div className="hint">داده فعالیت برای این بازه نیست.</div> : (
            <Chart chartKey="pf-svc" height={Math.min(520, 180 + svcLabels.length * 30)} option={barOption({
              labels: svcLabels,
              data: d.year2 ? [svcPay1, svcPay2] : [svcPay1],
              legends: d.year2 ? [`پرداخت ${d.year1}`, `پرداخت ${d.year2}`] : [`پرداخت ${d.year1}`],
              horizontal: true,
            })} />
          )}
        </ChartCard>
      </div>

      <div className="grid g23">
        <ChartCard title="عملکرد حوزه‌ها (ادارات)" sub="جمع پرداخت و رشد هر اداره" d={4}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr>
                <th>اداره</th><th>پرداخت {d.year1}</th>
                {d.year2 && <th>پرداخت {d.year2}</th>}
                {d.year2 && <th>رشد</th>}
                <th>تعداد مرکز</th>
              </tr></thead>
              <tbody>
                {(d.offices || []).slice(0, 14).map((o, i) => (
                  <tr key={i}>
                    <td><b>{o.name}</b></td>
                    <td className="num">{shortMoney(o.pay1 || 0)}</td>
                    {d.year2 && <td className="num">{shortMoney(o.pay2 || 0)}</td>}
                    {d.year2 && (
                      <td className="num">
                        {o.pay1 ? (
                          <b style={{ color: (o.pay2 || 0) >= o.pay1 ? 'var(--green)' : 'var(--red)' }}>
                            {(o.pay2 || 0) >= o.pay1 ? '▲' : '▼'} {faNum1(Math.abs(roundPct(o.pay2 || 0, o.pay1)))}٪
                          </b>
                        ) : '—'}
                      </td>
                    )}
                    <td className="num">{faNum(o.cnt1 || o.cnt2 || 0)}</td>
                  </tr>
                ))}
                {(d.offices || []).length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--muted)', padding: 20 }}>
                    داده‌ای برای ادارات نیست
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>
        <ChartCard title="مراکز برتر دوره" sub="۱۵ مرکز با بیشترین پرداخت" d={5}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>مرکز</th><th>استان</th><th>پرداخت {d.year1}</th>{d.year2 && <th>{d.year2}</th>}</tr></thead>
              <tbody>
                {(d.centers || []).slice(0, 14).map((c, i) => (
                  <tr key={i}>
                    <td>{c.name}</td>
                    <td className="tile">{c.prov || '—'}</td>
                    <td className="num">{shortMoney(c.pay1 || 0)}</td>
                    {d.year2 && <td className="num">{shortMoney(c.pay2 || 0)}</td>}
                  </tr>
                ))}
                {(d.centers || []).length === 0 && (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--muted)', padding: 20 }}>
                    داده‌ای نیست
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>

      <div className="grid g3">
        <ChartCard title="نیازمندان به تفکیک استان" sub={`مجموع ${faNum(d.needy?.total)} مددجوی ثبت‌شده`} d={6}>
          {(d.needy?.by_prov || []).length === 0 ? <div className="hint">داده نیازمندان ثبت نشده است.</div> : (
            <Chart chartKey="pf-needy-prov" height={300} option={barOption({
              labels: d.needy.by_prov.map((r) => r.name || 'نامشخص'),
              data: [d.needy.by_prov.map((r) => r.cnt)],
              legends: ['تعداد نیازمند'],
              horizontal: true,
            })} />
          )}
        </ChartCard>
        <ChartCard title="نیازمندان به تفکیک نوع" sub="دسته‌بندی نوع نیازمند" d={7}>
          {(d.needy?.by_type || []).length === 0 ? <div className="hint">داده‌ای نیست.</div> : (
            <Chart chartKey="pf-needy-type" height={300} option={donutOption({
              data: d.needy.by_type.map((r) => ({ name: r.name, value: r.cnt })),
            })} />
          )}
        </ChartCard>
        <ChartCard title="توزیع دهک درآمدی نیازمندان" sub="تمرکز فقر (دهک ۱ و ۲)" d={8}>
          {(d.needy?.by_decile || []).length === 0 ? <div className="hint">داده دهک ثبت نشده است.</div> : (
            <Chart chartKey="pf-needy-decile" height={300} option={barOption({
              labels: d.needy.by_decile.map((r) => `دهک ${faNum(r.d)}`),
              data: [d.needy.by_decile.map((r) => r.cnt)],
              legends: ['تعداد نیازمند'],
            })} />
          )}
        </ChartCard>
      </div>
    </>
  )
}

function roundPct(part, total) {
  return total ? Math.round((part / total) * 1000) / 10 : 0
}
