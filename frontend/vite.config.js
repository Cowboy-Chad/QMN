import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    // Fail loudly instead of silently bumping to 5175+ — the backend CORS
    // allowlist only covers 5174, so an unexpected port breaks API calls.
    strictPort: true,
  },
})