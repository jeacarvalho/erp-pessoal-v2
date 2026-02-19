import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env': {
        VITE_API_URL: env.VITE_API_URL || 'http://localhost:8000'
      }
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: ['.ngrok-free.app', '.ngrok.io', '.ngrok-free.dev', 'peers-poly-kitty-retained.trycloudflare.com', '.trycloudflare.com'],
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
