import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 代理目标，可用 VITE_BACKEND 覆盖，默认 8000
const backend = process.env.VITE_BACKEND || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 固定端口，被占用时直接报错，不自动切换
    port: 5172,
    strictPort: true,
    proxy: {
      '/api': backend,
    },
  },
})
