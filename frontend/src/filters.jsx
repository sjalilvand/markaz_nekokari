import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

// ─── زمینه فیلترهای سراسری (اسلایسرها) + نشانک‌ها (Bookmarks) ───

const FilterCtx = createContext(null)
const BM_KEY = 'nk_bookmarks_v1'
const THEME_KEY = 'nk_theme_v1'

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
    api_meta().then(setMeta).catch(() => {})
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
  const res = await fetch('/api/meta')
  return res.json()
}
