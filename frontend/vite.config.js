import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    https: {
      key: fs.readFileSync(path.resolve(__dirname, '../key.pem')),
      cert: fs.readFileSync(path.resolve(__dirname, '../cert.pem')),
    },
    host: '0.0.0.0',
    // Proxy ALL backend traffic through Vite (same origin = no SSL issues)
    proxy: {
      '/ws': {
        target: 'http://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
      '/spatial': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/vision': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/audio': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/agent': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  }
})
