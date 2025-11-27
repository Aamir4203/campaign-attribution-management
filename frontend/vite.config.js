import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3009,
    host: true,
    open: true, // Open to root, let router handle routing
    hmr: {
      overlay: true
    },
    watch: {
      usePolling: true,
      interval: 100
    }
  },
  css: {
    postcss: './postcss.config.js'
  }
})
