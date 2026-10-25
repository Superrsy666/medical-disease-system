import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8088',
        changeOrigin: true
      },
      // Python FastAPI 智能诊断服务（深度学习 + AI Agent）
      '/ai': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
