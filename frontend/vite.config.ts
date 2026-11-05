import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Sem VITE_API_URL a interface chama /api/v1 no mesmo endereço (padrão de produção).
// Em `npm run dev`/`npm run preview` locais, o Vite encaminha essas chamadas ao backend.
const apiProxy = {
  '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000', changeOrigin: true },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
