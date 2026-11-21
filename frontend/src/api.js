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
  const res = await fetch(`/api/${path}${buildQS(filters, extra)}`)
  if (!res.ok) {
    let msg = res.statusText
    try { msg = (await res.json()).error || msg } catch (_) { /* noop */ }
    throw new Error(`API ${path}: ${msg}`)
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
  importFiles: async (files) => {
    const fd = new FormData()
    files.forEach((x) => fd.append('files', x))
    const res = await fetch('/api/import', { method: 'POST', body: fd })
    if (!res.ok) throw new Error('خطا در بارگذاری فایل‌ها')
    return res.json()
  },
  exportUrl: (f, extra) => `/api/export/csv${buildQS(f, extra)}`,
}
