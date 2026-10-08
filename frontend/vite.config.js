import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: 'localhost', // Use localhost instead of 0.0.0.0
    open: false,       // Don't auto-open browser
  },
})
