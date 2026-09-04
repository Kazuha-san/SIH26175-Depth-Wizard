import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local-only dev server config. No deployment build target needed --
// we run `npm run dev` and demo straight from localhost:5173.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 }
})
