import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base مطلق: با refresh در مسیرهای تو در تو (مثل /analytics) هم assetها از ریشه لود می‌شوند
  base: '/',
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8000' }
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
    // ماژول‌های مشترک سنگین در chunk جدا و قابل‌کش
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers'],
          react_vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  }
})
