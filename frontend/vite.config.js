import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze-image': 'http://localhost:8000',
      '/analyze-url':   'http://localhost:8000',
      '/analyze':       'http://localhost:8000',
      '/history':       'http://localhost:8000',
      '/stats':         'http://localhost:8000',
      '/feedback':      'http://localhost:8000',
      '/learn':         'http://localhost:8000',
    }
  }
})
