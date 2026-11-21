// لایه ارتباط با API بک‌اند Flask

function buildQS(filters = {}, extra = {}) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries({ ...filters, ...extra })) {
    if (v !== undefined && v !== null && v !== '') p.set(k, v)
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

async function getJSON(path, filters = {}, extra = {}) {
  let res
  try {
    res = await fetch(`/api/${path}${buildQS(filters, extra)}`)
  } catch (_) {
    throw new Error('اتصال به سرور برقرار نشد — لطفاً مطمئن شوید سرور در حال اجرا است')
  }
  const ct = (res.headers.get('content-type') || '').toLowerCase()
  if (!res.ok) {
    let msg = res.statusText || ('HTTP ' + res.status)
    if (ct.includes('application/json')) {
      try { msg = (await res.json()).error || msg } catch (_) { /* noop */ }
    } else if (res.status === 500) {
      msg = 'خطای داخلی سرور — اگر ادامه یافت، سرور را با آخرین نسخه راه‌اندازی مجدد کنید'
    }
    throw new Error(`API ${path}: ${msg}`)
  }
  // پاسخ ۲۰۰ اما غیر JSON (مثلاً HTML) — هرگز res.json() صدا زده نمی‌شود تا
  // خطای خام JSON.parse به کاربر نمایش داده نشود
  if (!ct.includes('application/json')) {
    throw new Error(`API ${path}: پاسخ سرور JSON نبود — سرور قدیمی است؛ سرویس را با آخرین نسخه راه‌اندازی مجدد کنید`)
  }
  return res.json()
}

export const api = {
  meta: () => getJSON('meta'),
  overview: (f) => getJSON('overview', f),
  demographics: (f) => getJSON('demographics', f),
  trend: (f, extra) => getJSON('payments/trend', f, extra),
  compare: () => getJSON('payments/compare'),
  categories: (f) => getJSON('payments/categories', f),
  provinces: (f) => getJSON('provinces', f),
  centers: (f, extra) => getJSON('centers', f, extra),
  centersSummary: (f) => getJSON('centers/summary', f),
  kpis: (f) => getJSON('kpis', f),
  insights: (f) => getJSON('insights', f),
  narrative: (f) => getJSON('narrative', f),
  networks: (f) => getJSON('networks', f),
  finance: () => getJSON('finance'),
  quality: () => getJSON('quality'),
  records: (f, extra) => getJSON('records', f, extra),
  pivot: (f, extra) => getJSON('pivot', f, extra),
  // ── APIهای توسعه‌یافته (رصد داده‌ها، شاخص‌ها، عملکرد دوره‌ای، گزارش اسلایدی) ──
  exploreTables: () => getJSON('explore/tables'),
  explore: (extra) => getJSON('explore', {}, extra),
  exploreGroup: (extra) => getJSON('explore/group', {}, extra),
  exploreExportUrl: (extra) => `/api/explore/export?${new URLSearchParams(extra)}`,
  kpi21: () => getJSON('kpi21'),
  performance: (extra) => getJSON('performance', {}, extra),
  slideReport: (extra) => getJSON('slide-report', {}, extra),
  importFile: (file, onProgress) => new Promise((resolve, reject) => {
    const fd = new FormData()
    fd.append('files', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/import')
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      const body = xhr.response || {}
      if (xhr.status !== 200) { reject(new Error(body.error || ('خطای سرور: ' + xhr.status))); return }
      const r = (body.results && body.results[0]) || {}
      if (r.error) { reject(new Error(r.error)); return }
      resolve(r)
    }
    xhr.onerror = () => {
      const e = new Error('خطای شبکه در حین ارسال فایل — اتصال به سرور قطع شد')
      e.network = true
      reject(e)
    }
    xhr.onabort = () => {
      const e = new Error('ارسال فایل ناتمام ماند')
      e.network = true
      reject(e)
    }
    xhr.send(fd)
  }),
  resetDb: async () => {
    const res = await fetch('/api/reset-db', { method: 'POST' })
    if (!res.ok) throw new Error('خطا در پاک‌سازی پایگاه داده')
    return res.json()
  },
  recompute: async () => {
    const res = await fetch('/api/recompute', { method: 'POST' })
    if (!res.ok) throw new Error('خطا در بازمحاسبه امتیازها')
    return res.json()
  },
  exportUrl: (f, extra) => `/api/export/csv${buildQS(f, extra)}`,
}
