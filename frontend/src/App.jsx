import React, { useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { useFilters } from './filters.jsx'
import { Icons } from './components/ui.jsx'
import Overview from './pages/Overview.jsx'
import Analytics from './pages/Analytics.jsx'
import Payments from './pages/Payments.jsx'
import Provinces from './pages/Provinces.jsx'
import Centers from './pages/Centers.jsx'
import Kpis from './pages/Kpis.jsx'
import Reports from './pages/Reports.jsx'
import TextReport from './pages/TextReport.jsx'
import Admin from './pages/Admin.jsx'

const NAV = [
  { to: '/', label: 'داشبورد مدیریتی', icon: 'dashboard' },
  { to: '/analytics', label: 'تحلیل و توصیف', icon: 'analytics' },
  { to: '/payments', label: 'روند پرداخت‌ها', icon: 'coins' },
  { to: '/provinces', label: 'عملکرد استان‌ها', icon: 'map' },
  { to: '/centers', label: 'مراکز و مدال‌ها', icon: 'building' },
  { to: '/kpis', label: 'شاخص‌های کلیدی', icon: 'gauge' },
  { to: '/reports', label: 'گزارش‌های قابل فیلتر', icon: 'report' },
  { to: '/narrative', label: 'گزارش متنی تحلیلی', icon: 'people' },
  { to: '/admin', label: 'بارگذاری و کیفیت داده', icon: 'upload' },
]

const PROVINCE_ID_TO_TILE = {
  // موقعیت تقریبی نقشه کاشی‌مانند ایران (رديف، ستون)
  'آذربایجان شرقی': [1, 6], 'آذربایجان غربی': [1, 4], 'اردبیل': [1.5, 6.5], 'اصفهان': [3.5, 5.5],
  'البرز': [2.3, 3.2], 'ایلام': [3.5, 0.8], 'بوشهر': [4.4, 1.8], 'تهران': [2.2, 3.8],
  'چهارمحال و بختیاری': [3.8, 3.3], 'خراسان جنوبی': [3.3, 8.6], 'خراسان رضوی': [2.5, 8.8],
  'خراسان شمالی': [1.8, 8.2], 'خوزستان': [4.2, 1.0], 'زنجان': [1.8, 4.2], 'سمنان': [2.5, 5.8],
  'سیستان و بلوچستان': [4.8, 8.2], 'فارس': [4.3, 3.0], 'قزوین': [1.9, 3.6], 'قم': [2.8, 4.2],
  'کردستان': [1.6, 2.2], 'کرمان': [4.6, 5.8], 'کرمانشاه': [2.2, 1.6], 'کهگیلویه و بویراحمد': [4.0, 2.4],
  'گلستان': [1.5, 7.4], 'گیلان': [1.4, 3.4], 'لرستان': [3.0, 2.4], 'مازندران': [1.8, 5.0],
  'مرکزی': [2.6, 3.9], 'هرمزگان': [5.4, 4.6], 'همدان': [2.4, 2.8], 'یزد': [3.8, 4.9],
}

export default function App() {
  const { filters, setFilter, reset, meta, theme, setTheme, bookmarks, saveBookmark, delBookmark } = useFilters()
  const [showBm, setShowBm] = useState(false)
  const [bmName, setBmName] = useState('')
  const provinces = meta?.provinces || []
  const offices = (meta?.offices || []).filter(
    (o) => filters.province === 'all' || String(o.province_id) === String(filters.province))
  const mode = meta?.data_mode || 'demo'

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-logo"><Icons.heart style={{ width: 20, height: 20 }} /></div>
          <div>
            <h1>نیکوکاری و توانمندسازی</h1>
            <span>داشبورد جامع شبکه مردمی</span>
          </div>
        </div>
        {NAV.map((n) => {
          const Ic = Icons[n.icon]
          return (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
              <span style={{ display: 'flex' }}><Ic /></span>
              <span>{n.label}</span>
            </NavLink>
          )
        })}
        <div className="side-foot">
          بک‌اند: Flask + SQLite | فرانت: React + ECharts
          <br />
          {mode === 'demo' ? 'داده نمونه وفادار به آمار فایل‌های واقعی' : mode === 'empty' ? 'پایگاه داده خالی — از صفحه بارگذاری، فایل‌های CSV را وارد کنید' : 'داده واقعی بارگذاری‌شده'}
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <span className={`badge ${mode === 'real' ? 'real' : 'demo'}`}>
            {mode === 'demo' ? 'داده نمونه کالیبره‌شده' : mode === 'empty' ? 'در انتظار بارگذاری داده' : 'داده واقعی'}
          </span>
          <div className="filters">
            <label>سال</label>
            <select value={filters.year} onChange={(e) => setFilter('year', e.target.value)}>
              <option value="all">همه سال‌ها</option>
              {(meta?.years || []).map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
            <label>استان</label>
            <select value={filters.province} onChange={(e) => setFilter('province', e.target.value)}>
              <option value="all">همه استان‌ها</option>
              {provinces.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <label>اداره</label>
            <select value={filters.office} onChange={(e) => setFilter('office', e.target.value)}>
              <option value="all">همه ادارات</option>
              {offices.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
            <button className="btn" onClick={reset}><Icons.close /> پاک کردن</button>
          </div>
          <div className="spacer" />
          <div style={{ position: 'relative' }}>
            <button className="btn" onClick={() => setShowBm(!showBm)}><Icons.bookmark /> نشانک‌ها</button>
            {showBm && (
              <div className="card" style={{ position: 'absolute', top: 40, insetInlineEnd: 0, width: 260, zIndex: 50, padding: 12 }}>
                <div className="row-flex" style={{ marginBottom: 8 }}>
                  <input type="text" placeholder="نام نما (مثلاً گزارش زمستان)" value={bmName}
                    onChange={(e) => setBmName(e.target.value)} style={{ flex: 1, minWidth: 0 }} />
                  <button className="btn primary" disabled={!bmName} onClick={() => { saveBookmark(bmName); setBmName('') }}>ذخیره</button>
                </div>
                {bookmarks.length === 0 && <div className="hint">هنوز نما ذخیره نشده است. ترکیب فعلی فیلترها را با نام دلخواه ذخیره کنید.</div>}
                {bookmarks.map((b) => (
                  <div key={b.id} className="row-flex" style={{ marginBottom: 6 }}>
                    <button className="chip" style={{ flex: 1 }}
                      onClick={() => { setFiltersSafe(b.filters); setShowBm(false) }}>{b.name}</button>
                    <button className="icon-btn" onClick={() => delBookmark(b.id)}><Icons.close /></button>
                  </div>
                ))}
                <div className="hint">نشانک‌ها ترکیب سال/استان/اداره را نگه می‌دارند (مانند Bookmarks در Power BI).</div>
              </div>
            )}
          </div>
          <button className="btn" onClick={() => window.print()}><Icons.print /> چاپ</button>
          <button className="icon-btn" title="تغییر پوسته" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? <Icons.sun /> : <Icons.moon />}
          </button>
        </div>

        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/provinces" element={<Provinces />} />
          <Route path="/centers" element={<Centers />} />
          <Route path="/kpis" element={<Kpis />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/narrative" element={<TextReport />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
    </div>
  )

  function setFiltersSafe(f) {
    if (!f) return
    for (const k of ['year', 'province', 'office']) setFilter(k, f[k] ?? 'all')
  }
}

export { PROVINCE_ID_TO_TILE }
