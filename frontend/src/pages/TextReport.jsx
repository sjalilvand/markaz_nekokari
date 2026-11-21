import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useFilters } from '../filters.jsx'
import { Loading, ErrorBox, faNum, Icons } from '../components/ui.jsx'

export default function TextReport() {
  const { filters, meta } = useFilters()
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    setD(null)
    api.narrative(filters).then(setD).catch(setErr)
  }, [filters])

  if (err) return <ErrorBox err={err} />
  if (!d) return <Loading />

  const kn = d.key_numbers || {}

  return (
    <>
      <div className="row-flex" style={{ marginBottom: 14 }}>
        <span className="badge">دامنه: {d.scope}</span>
        <span className="badge">دوره: {d.year_note}</span>
        <span className="badge">تولید خودکار از داده زنده سامانه</span>
        <div className="spacer" />
        <button className="btn primary" onClick={() => window.print()}>
          <Icons.print /> چاپ / ذخیره PDF گزارش
        </button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-head">
          <div>
            <h3 style={{ fontSize: 17 }}>گزارش متنی تحلیل عملکرد مراکز نیکوکاری و نحوه ارائه خدمات</h3>
            <div className="sub">گزارش خودکار — همه ارقام از پایگاه داده سامانه محاسبه شده است</div>
          </div>
        </div>
        <div className="keynums">
          <div className="keynum"><b>{faNum(kn.centers)}</b><span>مراکز فعال</span></div>
          <div className="keynum"><b>{faNum(kn.members_active)}</b><span>اعضای فعال</span></div>
          <div className="keynum"><b>{faNum(kn.needy)}</b><span>نیازمندان</span></div>
          <div className="keynum"><b>{faNum(kn.hamyaran)}</b><span>همیاران</span></div>
          <div className="keynum"><b>{faNum(kn.requests)}</b><span>درخواست‌ها</span></div>
          <div className="keynum"><b>{kn.growth !== null && kn.growth !== undefined ? `${faNum(kn.growth)}٪` : '—'}</b><span>رشد پرداخت</span></div>
        </div>
      </div>

      {d.sections.map((s, i) => (
        <div className="card report-sec" key={s.id} style={{ '--d': `${i * 0.04}s` }}>
          <h3>{s.title}</h3>
          {(s.paragraphs || []).map((p, j) => <p key={j}>{p}</p>)}
          {s.bullets && <ul>{s.bullets.map((b, j) => <li key={j}>{b}</li>)}</ul>}
          {s.table && (
            <div className="tbl-wrap">
              <table className="tbl">
                <thead><tr>{s.table.headers.map((h) => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {s.table.rows.map((r, j) => (
                    <tr key={j}>{r.map((c, k) => <td key={k} className={k > 0 ? 'num' : ''}>{c}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}

      <div className="hint" style={{ textAlign: 'center', marginTop: 20 }}>
        این گزارش با تغییر فیلترهای سال/استان در نوار بالا به‌صورت زنده بازتولید می‌شود.
      </div>
    </>
  )
}
