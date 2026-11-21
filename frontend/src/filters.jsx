import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

// ─── زمینه فیلترهای سراسری (اسلایسرها) + نشانک‌ها (Bookmarks) ───

const FilterCtx = createContext(null)
const BM_KEY = 'nk_bookmarks_v1'
const THEME_KEY = 'nk_theme_v1'

// حداقل نسخهٔ سروری که این نسخهٔ فرانت‌اند با آن سازگار است.
// اگر سرور قدیمی‌تر اجرا شود (مثلاً ری‌استارت نشده باشد) هشدار سراسری نمایش داده می‌شود.
export const REQUIRED_SERVER_VERSION = '2.3.0'

function vparts(v) {
  return String(v || '').split('.').map((x) => parseInt(x, 10) || 0)
}

export function serverOutdated(v, required = REQUIRED_SERVER_VERSION) {
  if (!v) return true // سرور بدون فیلد نسخه = بسیار قدیمی
  const a = vparts(v)
  const b = vparts(required)
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) < (b[i] || 0)
  }
  return false
}

export function FilterProvider({ children }) {
  const [filters, setFilters] = useState({ year: 'all', province: 'all', office: 'all' })
  const [meta, setMeta] = useState(null)
  const [theme, setTheme] = useState(localStorage.getItem(THEME_KEY) || 'dark')
  const [bookmarks, setBookmarks] = useState(() => {
    try { return JSON.parse(localStorage.getItem(BM_KEY)) || [] } catch (_) { return [] }
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    api_meta().then((m) => setMeta(m)).catch(() => {
      // اگر meta اصلاً نیامد، نشانگر نسخهٔ نامشخص می‌گذاریم تا بنجر هشدار سرور قدیمی نمایش داده شود
      setMeta({ meta_failed: true })
    })
  }, [])

  const setFilter = useCallback((k, v) => {
    setFilters((f) => {
      const nf = { ...f, [k]: v }
      if (k === 'province' && v !== f.province) nf.office = 'all'
      if (k === 'year' && v === 'all') { /* noop */ }
      return nf
    })
  }, [])

  const reset = useCallback(() => setFilters({ year: 'all', province: 'all', office: 'all' }), [])

  const saveBookmark = useCallback((name) => {
    setBookmarks((b) => {
      const nb = [...b, { id: Date.now(), name, filters: { ...filters } }]
      localStorage.setItem(BM_KEY, JSON.stringify(nb))
      return nb
    })
  }, [filters])

  const delBookmark = useCallback((id) => {
    setBookmarks((b) => {
      const nb = b.filter((x) => x.id !== id)
      localStorage.setItem(BM_KEY, JSON.stringify(nb))
      return nb
    })
  }, [])

  const value = useMemo(() => ({
    filters, setFilter, reset, meta, theme, setTheme, bookmarks, saveBookmark, delBookmark,
  }), [filters, setFilter, reset, meta, theme, bookmarks, saveBookmark, delBookmark])

  return <FilterCtx.Provider value={value}>{children}</FilterCtx.Provider>
}

export const useFilters = () => useContext(FilterCtx)

async function api_meta() {
  // parse امن: هرگز res.json() مستقیم — اگر پاسخ HTML بود خطای دوستانه پرتاب می‌شود
  const res = await fetch('/api/meta')
  const ct = (res.headers.get('content-type') || '').toLowerCase()
  const text = await res.text()
  if (!res.ok || !ct.includes('application/json')) {
    throw new Error('پاسخ /api/meta معتبر نبود')
  }
  try {
    return JSON.parse(text)
  } catch (_) {
    throw new Error('پاسخ /api/meta قابل تجزیه نبود')
  }
}
