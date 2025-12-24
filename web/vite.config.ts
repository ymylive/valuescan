import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const rawBase = env.VITE_BASE_PATH || '/'
  const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`
  const apiBase = `${base === '/' ? '' : base.slice(0, -1)}/api`

  return {
    base,
    plugins: [react()],
    build: {
      rollupOptions: {
        output: {
          // Force new hash for cache busting
          entryFileNames: `assets/[name]-[hash]-v2.js`,
          chunkFileNames: `assets/[name]-[hash]-v2.js`,
          assetFileNames: `assets/[name]-[hash]-v2.[ext]`,
        },
      },
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        [apiBase]: {
          target: 'http://localhost:8080',
          changeOrigin: true,
        },
        ...(apiBase === '/api'
          ? {}
          : {
              '/api': {
                target: 'http://localhost:8080',
                changeOrigin: true,
              },
            }),
      },
    },
  }
})
