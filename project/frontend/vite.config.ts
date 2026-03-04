import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// Explicitly pin root to this file's directory so Vite finds index.html
// regardless of what CWD the build system (Vercel/CI) uses.
const __dir = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  root: __dir,
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
})
