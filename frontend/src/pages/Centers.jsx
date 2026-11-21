import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, ChartCard, Loading, ErrorBox, PngButton, DataTable, Medal, ScoreRing, faNum, faNum1,
  shortMoney, barOption, donutOption, PALETTE, MEDAL_COLORS,
} from '../components/ui.jsx'

const MEDAL_CRITERIA = [
  { m: 'پلاتین', desc: 'امتیاز ۹۰ به بالا — ساختار کامل، پرداخت بالا و پوشش مطلوب نیازمندان', c: '#9db9e8' },
  { m: 'طلا', desc: 'امتیاز ۸۰ تا ۸۹ — عملکرد قوی با یک یا دو نقطه ضعف جزئی', c: '#ffd76e' },
  { m: 'نقره', desc: 'امتیاز ۷۰ تا ۷۹ — عملکرد متوسط رو به بالا', c: '#a9b6cc' },
  { m: 'برنز', desc: 'امتیاز ۶۰ تا ۶۹ — نیازمند تقویت ساختار یا فعالیت', c: '#c77b46' },
  { m: 'نیازمند بهبود', desc: 'امتیاز زیر ۶۰ — اولویت مداخله و حمایت استانی', c: '#6b789c' },
]

export default function Centers() {
  const { filters } = useFilters()
  const [sum, setSum] = useState(null)
  const [list, setList] = useState(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [medal, setMedal] = useState('all')
  const [sort, setSort] = useState('score')
  const [dir, setDir] = useState('desc')
  const [err, setErr] = useState(null)

  useEffect(() => {
    api.centersSummary(filters).then(setSum).catch(setErr)
  }, [filters])
  useEffect(() => {
    api.centers(filters, { page, per: 12, search, medal, sort, dir }).then(setList).catch(setErr)
  }, [filters, page, search, medal, sort, dir])

  if (err && !sum) return <ErrorBox err={err} />
  if (!sum) return <Loading />

  const medalData = MEDAL_CRITERIA.map((m) => ({
    name: m.m,
    value: (sum.medal_dist || []).find((x) => x.label === m.m)?.n || 0,
    itemStyle: { color: MEDAL_COLORS[m.m] },
  }))
  const roleLabels = { chair: 'رئیس هیات امنا', vice: 'نایب رئیس', exec_mgr: 'مدیر اجرایی',
    finance: 'مسئول مالی', members: 'عضو', inspector: 'بازرس', alt_inspector: 'علی‌البدل بازرس' }
  const roles = sum.roles || {}
  const roleRows = Object.entries(roleLabels).map(([k, v]) => ({ label: v, n: roles[k] || 0 }))

  const listCols = [
    { key: 'name', label: 'مرکز', render: (r) => <b>{r.name}</b> },
    { key: 'prov', label: 'استان' },
    { key: 'license_no', label: 'شماره مجوز', num: true },
    { key: 'medal', label: 'مدال', render: (r) => <Medal medal={r.medal} score={r.score} /> },
    { key: 'total_active', label: 'اعضای فعال', num: true },
    { key: 'total_inactive', label: 'غیرفعال', num: true },
    { key: 'pay', label: 'پرداخت', num: true, render: (r) => shortMoney(r.pay) },
    { key: 'needy_cnt', label: 'نیازمندان', num: true },
    { key: 'roles', label: 'نقش‌ها', render: (r) => (
      <span className="tile">
        {[r.chair && 'ر', r.vice && 'ن', r.exec_mgr && 'م', r.finance && 'ف', r.members && 'ع', r.inspector && 'ب', r.alt_inspector && 'ع‌ب'].filter(Boolean).join(' · ')}
      </span>) },
  ]

  return (
    <>
      <div className="grid g23">
        <ChartCard title="توزیع مدال مراکز" sub="امتیاز مرکب: ساختار + فعالیت مالی + پوشش + کیفیت اعضا" d={0}
          actions={<PngButton chartKey="ct-medals" />}>
          <Chart chartKey="ct-medals" height={300} option={donutOption({ data: medalData, colors: PALETTE })} />
          <div style={{ marginTop: 10 }}>
            {MEDAL_CRITERIA.map((m) => (
              <div key={m.m} className="row-flex" style={{ marginBottom: 6, fontSize: 12 }}>
                <Medal medal={m.m} />
                <span className="tile" style={{ flex: 1 }}>{m.desc}</span>
                <b>{faNum((sum.medal_dist || []).find((x) => x.label === m.m)?.n || 0)} مرکز</b>
              </div>
            ))}
          </div>
        </ChartCard>
        <div>
          <ChartCard title="پوشش نقش‌های ساختاری" sub="درصد مراکز دارای هر نقش (الگوی واقعی)" d={1}
            actions={<PngButton chartKey="ct-roles" />}>
            <Chart chartKey="ct-roles" height={280} option={barOption({
              labels: roleRows.map((r) => r.label),
              data: [roleRows.map((r) => r.n)],
              legends: ['مرکز دارای نقش'],
              horizontal: true,
            })} />
            <div className="hint">ضعیف‌ترین حلقه «مدیر اجرایی» است — فقط {faNum1(roles.exec_mgr)}٪ مراکز دارند؛ این یافته مستقیماً به پیشنهاد بهبود در گزارش متنی منتقل شده است.</div>
          </ChartCard>
          <ChartCard title="هیستوگرام اعضای فعال" sub="توزیع مجموع اعضای فعال هر مرکز" d={2}
            actions={<PngButton chartKey="ct-hist" />}>
            <Chart chartKey="ct-hist" height={240} option={barOption({
              labels: (sum.completeness_hist || []).map((r) => faNum(r.x)),
              data: [(sum.completeness_hist || []).map((r) => r.n)],
              legends: ['مراکز'],
            })} />
          </ChartCard>
        </div>
      </div>

      <div className="grid g23">
        <ChartCard title="مراکز برتر و نیازمند بهبود" sub="جدول امتیاز" d={3}>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>رتبه</th><th>مرکز</th><th>استان</th><th>امتیاز</th><th>مدال</th><th>اعضا</th></tr></thead>
              <tbody>
                {(sum.top || []).slice(0, 5).map((c, i) => (
                  <tr key={'t' + c.id}><td>{faNum(i + 1)}</td><td>{c.name}</td><td>{c.prov}</td>
                    <td className="num">{faNum(c.score)}</td><td><Medal medal={c.medal} /></td>
                    <td className="num">{faNum(c.total_active)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="hint">مراکز نیازمند بهبود:</div>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>مرکز</th><th>استان</th><th>امتیاز</th><th>مدال</th><th>اعضا</th></tr></thead>
              <tbody>
                {(sum.bottom || []).slice(0, 5).map((c) => (
                  <tr key={'b' + c.id}><td>{c.name}</td><td>{c.prov}</td>
                    <td className="num">{faNum(c.score)}</td><td><Medal medal={c.medal} /></td>
                    <td className="num">{faNum(c.total_active)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
        <ChartCard title="رادار ساختار — ۵ استان برتر" d={4} sub="ساختار، ظرفیت، کیفیت و امتیاز کل">
          <Chart chartKey="ct-radar" height={420} option={{
            color: PALETTE,
            legend: { top: 0, textStyle: { color: '#98a5c6', fontSize: 11, fontFamily: "'Vazirmatn'" } },
            tooltip: { backgroundColor: 'rgba(10,16,38,.94)', borderColor: 'rgba(143,157,255,.4)', textStyle: { color: '#eaeefb', fontSize: 12 } },
            radar: {
              indicator: [
                { name: 'ساختار', max: 100 }, { name: 'ظرفیت', max: 100 },
                { name: 'کیفیت اعضا', max: 100 }, { name: 'امتیاز کل', max: 100 },
              ],
              axisName: { color: '#98a5c6', fontSize: 11 },
              splitArea: { areaStyle: { color: ['rgba(128,145,190,.04)', 'rgba(128,145,190,.08)'] } },
              splitLine: { lineStyle: { color: 'rgba(128,145,190,.2)' } },
            },
            series: [{
              type: 'radar',
              data: (sum.radar || []).map((r) => ({
                name: r.name, value: [r.structure, r.capacity, Math.max(0, r.quality), r.score],
                areaStyle: { opacity: .12 },
              })),
            }],
          }} />
        </ChartCard>
      </div>

      <ChartCard title="پرداخت بر حسب اعضای فعال (حبابی)" d={5} sub="هر نقطه یک مرکز — محور افقی: اعضای فعال، محور عمودی: پرداخت (میلیارد ریال)">
        <Chart chartKey="ct-scatter" height={360} option={{
          tooltip: {
            formatter: (p) => `${p.data[3]}<br/>اعضای فعال: ${faNum(p.data[0])} — پرداخت: ${shortMoney(p.data[1] * 1e9)}`,
            backgroundColor: 'rgba(10,16,38,.94)', borderColor: 'rgba(143,157,255,.4)', textStyle: { color: '#eaeefb', fontSize: 12 },
          },
          legend: { top: 0, textStyle: { color: '#98a5c6', fontSize: 11 } },
          xAxis: { name: 'اعضای فعال', nameTextStyle: { color: '#98a5c6' }, type: 'value',
            splitLine: { lineStyle: { color: 'rgba(128,145,190,.15)' } }, axisLabel: { color: '#98a5c6' } },
          yAxis: { type: 'value', axisLabel: { color: '#98a5c6', formatter: (v) => shortMoney(v * 1e9) },
            splitLine: { lineStyle: { color: 'rgba(128,145,190,.15)' } } },
          series: ['پلاتین', 'طلا', 'نقره', 'برنز', 'نیازمند بهبود'].map((m) => ({
            name: m, type: 'scatter',
            data: (sum.scatter || []).filter((s) => s.medal === m).map((s) => [s.x, s.y, 1, s.name]),
            symbolSize: 9, itemStyle: { color: MEDAL_COLORS[m], opacity: .75 },
          })),
        }} />
        <div className="hint">تفکیک رنگی بر اساس مدال — مراکز با اعضای کم ولی پرداخت بالا، ریسک کنترلی دارند.</div>
      </ChartCard>

      <ChartCard title="فهرست مراکز نیکوکاری" d={6} sub="جست‌وجو، فیلتر مدال و مرتب‌سازی — دقیقاً مانند ماتریس Power BI">
        <div className="row-flex" style={{ marginBottom: 10 }}>
          <input type="search" placeholder="جست‌وجوی نام مرکز یا شماره مجوز…" value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }} style={{ flex: 1, minWidth: 220 }} />
          <select value={medal} onChange={(e) => { setMedal(e.target.value); setPage(1) }}>
            <option value="all">همه مدال‌ها</option>
            {MEDAL_CRITERIA.map((m) => <option key={m.m} value={m.m}>{m.m}</option>)}
          </select>
        </div>
        {!list ? <Loading /> : (
          <DataTable cols={listCols} rows={list.rows} page={list.page} per={list.per} total={list.total}
            onPage={setPage} rowKey={(r) => r.id}
            sort={sort} dir={dir}
            onSort={(k) => {
              const map = { name: 'name', pay: 'payments', total_active: 'members', total_inactive: 'inactive' }
              if (map[k]) { setSort(map[k]); setDir(dir === 'desc' ? 'asc' : 'desc') }
            }} />
        )}
      </ChartCard>
    </>
  )
}
