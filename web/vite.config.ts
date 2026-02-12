import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const WS_PROXY_ENABLED_VALUES = new Set(['1', 'true', 'yes', 'on']);

const toWsTarget = (target: string): string => {
  if (/^https?:\/\//i.test(target)) {
    return target.replace(/^http/i, 'ws');
  }
  return target;
};

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiProxyTarget = (env.VITE_DEV_API_PROXY_TARGET || 'http://localhost:5000').trim();
  const wsProxyEnabled = WS_PROXY_ENABLED_VALUES.has((env.VITE_ENABLE_WS_PROXY || '').trim().toLowerCase());
  const wsProxyTarget = (env.VITE_DEV_WS_PROXY_TARGET || '').trim() || toWsTarget(apiProxyTarget);

  const proxy: Record<string, { target: string; changeOrigin?: boolean; ws?: boolean }> = {
    '/api': {
      target: apiProxyTarget,
      changeOrigin: true,
    },
  };

  if (wsProxyEnabled) {
    proxy['/ws'] = {
      target: wsProxyTarget,
      ws: true,
      changeOrigin: true,
    };
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: true,
      proxy,
    },
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.{ts,tsx}'],
      setupFiles: './src/test/setup.ts',
      clearMocks: true,
      restoreMocks: true,
    },
  };
});
