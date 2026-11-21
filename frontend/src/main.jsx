import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { FilterProvider } from './filters.jsx'
import './theme.css'
import 'vazirmatn/Vazirmatn-font-face.css'

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <FilterProvider>
      <App />
    </FilterProvider>
  </BrowserRouter>
)
