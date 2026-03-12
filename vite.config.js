import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/abstract_games/',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        yodd: resolve(__dirname, 'yodd/index.html'),
        oust: resolve(__dirname, 'oust/index.html'),
      },
    },
  },
})
