// import { defineConfig } from 'vite'
// import react from '@vitejs/plugin-react'
// import tailwindcss from '@tailwindcss/vite'

// // https://vite.dev/config/
// export default defineConfig({
//   plugins: [react(), tailwindcss()],
// })

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path' // 👈 Make sure to import 'path'

// https://vite.dev/config/
export default defineConfig({
  // GitHub Pages base path (repo name). If Pages is set to root of this repo:
  base: '/KRISHI_SHAYAK/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'), // 👈 This line adds alias support
    },
  },
  build: {
    // Output the static site into repo root so Pages (root) serves the built site
    outDir: path.resolve(__dirname, '../..'),
    emptyOutDir: false, // avoid nuking the entire repo; we will only overwrite index.html/assets
  },
})
