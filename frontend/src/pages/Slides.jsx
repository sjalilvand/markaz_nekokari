import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import {
  Chart, Loading, ErrorBox, Icons, faNum, faNum1, money, shortMoney,
  lineOption, barOption, donutOption,
} from '../components/ui.jsx'

// ─── گزارش اسلایدی عملکرد: نمایش ارائه‌ای عملکرد اداره کل در بازه زمانی انتخابی ───

export default function Slides() {
  const { filters, meta } = useFilters()
  const years = meta?.years?.length ? meta.years : [1404, 1405]
  const latest = years[years.length - 1]
  const [year, setYear] = useState(filters.year !== 'all' ? +filters.year : latest)
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    setD(null)
    setIdx(0)
    api.slideReport({
      year, province: filters.province, office: filters.office,
    }).then(setD).catch(setErr)
  }, [filters, year])

  useEffect(() => {
    const onKey = (e) => {
      if (!d) return
      if (e.key === 'ArrowLeft' || e.key === ' ' || e.key === 'PageDown') {
        setIdx((x) => Math.min(x + 1, d.slides.length - 1))
      } else if (e.key === 'ArrowRight' || e.key === 'PageUp') {
        setIdx((x) => Math.max(x - 1, 0))
      } else if (e.key === 'Home') setIdx(0)
      else if (e.key === 'End') setIdx(d.slides.length - 1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [d])

  if (err && !d) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const n = d.slides.length
  const cur = d.slides[Math.min(idx, n - 1)]

  return (
    <>
      <style>{`
        .slide-stage { min-height: 62vh; display: flex; flex-direction: column; }
        .slide-body { flex: 1; display: flex; flex-direction: column; justify-content: center; animation: fadeUp .4s ease both; }
        .slide-title-x { text-align: center; padding: 40px 20px; }
        .slide-title-x h2 { font-size: 2rem; color: var(--acc); margin-bottom: 14px; }
        .slide-title-x .sub { font-size: 1.15rem; color: var(--muted); margin-bottom: 22px; }
        .slide-badges { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
        .slide-badges span { background: var(--card2); border: 1px solid var(--line); padding: 8px 18px; border-radius: 30px; font-size: .9rem; }
        .slide-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .slide-kpi { background: var(--card2); border: 1px solid var(--line); border-radius: 14px; padding: 18px; text-align: center; }
        .slide-kpi .v { font-size: 1.5rem; font-weight: 800; color: var(--acc); direction: ltr; }
        .slide-kpi .l { font-size: .85rem; color: var(--muted); margin-top: 6px; }
        .slide-text ul { list-style: none; padding: 0; }
        .slide-text li { background: var(--card2); border: 1px solid var(--line); border-right: 4px solid var(--acc);
          border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; line-height: 1.9; font-size: 1rem; }
        .slide-ctl { display: flex; align-items: center; gap: 12px; justify-content: center; margin-top: 18px; }
        .slide-dots { display: flex; gap: 6px; }
        .slide-dots i { width: 9px; height: 9px; border-radius: 50%; background: var(--line); display: block; }
        .slide-dots i.on { background: var(--acc); transform: scale(1.25); }
        @media print { .no-print { display: none !important; } .slide-stage { min-height: auto; page-break-after: always; } }
      `}</style>

      <div className="row-flex no-print" style={{ marginBottom: 14, flexWrap: 'wrap' }}>
        <span className="crumb"><b>گزارش اسلایدی</b> — برای نمایش در جلسات؛ کلیدهای ← → یا Space برای جابه‌جایی</span>
        <div className="spacer" />
        <label style={{ fontSize: 12 }}>دوره:</label>
        <select value={year} onChange={(e) => setYear(+e.target.value)}>
          {years.map((y) => <option key={y} value={y}>سال {y}</option>)}
        </select>
        <button className="btn primary" onClick={() => window.print()}><Icons.print /> چاپ / خروجی PDF</button>
      </div>

      <div className="card" style={{ padding: 28 }}>
        <div className="slide-stage">
          <SlideView slide={cur} />
        </div>

        <div className="slide-ctl no-print">
          <button className="btn" disabled={idx === 0} onClick={() => setIdx(idx - 1)}>
            <Icons.close style={{ transform: 'rotate(90deg)' }} /> قبلی
          </button>
          <div className="slide-dots">
            {d.slides.map((_, i) => <i key={i} className={i === idx ? 'on' : ''} />)}
          </div>
          <button className="btn primary" disabled={idx >= n - 1} onClick={() => setIdx(idx + 1)}>
            بعدی <Icons.close style={{ transform: 'rotate(-90deg)' }} />
          </button>
          <span className="hint" style={{ minWidth: 110, textAlign: 'center' }}>
            اسلاید {faNum(idx + 1)} از {faNum(n)}
          </span>
        </div>
      </div>
    </>
  )
}

function SlideView({ slide }) {
  if (!slide) return null
  if (slide.type === 'title') {
    return (
      <div className="slide-body slide-title-x">
        <h2>{slide.title}</h2>
        <div className="sub">{slide.subtitle}</div>
        <div className="slide-badges">
          {(slide.badges || []).map((b, i) => <span key={i}>{b}</span>)}
        </div>
      </div>
    )
  }
  if (slide.type === 'kpi') {
    return (
      <div className="slide-body">
        <h3 style={{ textAlign: 'center', marginBottom: 20, color: 'var(--acc)' }}>{slide.title}</h3>
        <div className="slide-kpis">
          {(slide.items || []).map((it, i) => (
            <div key={i} className="slide-kpi">
              <div className="v">
                {it.unit === 'rial' ? money(it.value)
                  : it.unit === 'percent' ? (it.value == null ? '—' : `${faNum1(it.value)}٪`)
                  : faNum(it.value)}
              </div>
              <div className="l">{it.label}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }
  if (slide.type === 'chart') {
    const height = slide.chart === 'line' ? 340 : 340
    const option = slide.chart === 'line'
      ? lineOption({ labels: slide.labels, series: slide.series.map((s) => s.data), legends: slide.series.map((s) => s.name) })
      : slide.chart === 'bar'
        ? barOption({ labels: slide.labels, data: slide.series.map((s) => s.data), legends: slide.series.map((s) => s.name), horizontal: (slide.labels || []).length > 6 })
        : donutOption({ data: slide.data })
    return (
      <div className="slide-body">
        <h3 style={{ textAlign: 'center', marginBottom: 8, color: 'var(--acc)' }}>{slide.title}</h3>
        {slide.note && <div className="hint" style={{ textAlign: 'center', marginBottom: 10 }}>{slide.note}</div>}
        <Chart chartKey={`sl-${slide.title}`} height={height} option={option} />
      </div>
    )
  }
  if (slide.type === 'table') {
    return (
      <div className="slide-body">
        <h3 style={{ textAlign: 'center', marginBottom: 16, color: 'var(--acc)' }}>{slide.title}</h3>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr>{(slide.head || []).map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
            <tbody>
              {(slide.rows || []).map((r, i) => (
                <tr key={i}>
                  {r.map((cell, j) => (
                    <td key={j} className={typeof cell === 'number' ? 'num' : ''}>
                      {typeof cell === 'number' ? faNum(cell) : cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }
  if (slide.type === 'text') {
    return (
      <div className="slide-body slide-text">
        <h3 style={{ textAlign: 'center', marginBottom: 16, color: 'var(--acc)' }}>{slide.title}</h3>
        <ul>
          {(slide.bullets || []).map((b, i) => <li key={i}>{b}</li>)}
        </ul>
      </div>
    )
  }
  return null
}
