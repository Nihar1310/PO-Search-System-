import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const resolvePort = () => {
  const raw = process.env.PORT || process.env.FRONTEND_PORT || process.env.VITE_PORT
  const parsed = raw ? Number(raw) : undefined
  return Number.isFinite(parsed) ? parsed : 5173
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: resolvePort(),
    strictPort: false,
  },
})
