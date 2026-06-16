import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Intercepts any local frontend fetches starting with /auth or /admin
      '/auth': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/track': 'http://127.0.0.1:8000',
      '/growth': 'http://127.0.0.1:8000',
      '/value': 'http://127.0.0.1:8000',
    }
  }
})