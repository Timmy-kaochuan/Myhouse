import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发代理：/api/* -> 127.0.0.1:8000/*（后端路由挂载在根路径，去掉 /api 前缀）
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
