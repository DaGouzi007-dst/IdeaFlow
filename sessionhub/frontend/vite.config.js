import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发服务器固定 5171：避开第四模块 ProgressGate 默认占用的 5173，
// 两个模块可以同时开着开发。/api 请求代理到本模块后端 8001。
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8001' },
  },
})
