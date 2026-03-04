import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Ensure Vite always resolves index.html correctly in Vercel.
// Vercel sometimes runs the build from the repo root instead of project/frontend.
const cwd = process.cwd()
const expectedRoot = path.resolve(cwd, 'project', 'frontend')
const rootDir = cwd.endsWith(path.join('project', 'frontend')) ? cwd : expectedRoot
export default defineConfig({
  root: rootDir,
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
})
