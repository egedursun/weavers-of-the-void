import path from 'path'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import { playwright } from '@vitest/browser-playwright'
import { readFileSync, realpathSync } from 'fs'
import { defineConfig } from 'vitest/config'

const ELEMENT_WAIT_MS = 5000

const ROOT = import.meta.dirname
const PORT_AT = process.argv.indexOf('--port')
const SERVER_KEY = process.env.VITEST
  ? 'vitest'
  : PORT_AT >= 0
    ? (process.argv[PORT_AT + 1] ?? 'dev')
    : 'dev'

const { version } = JSON.parse(
  readFileSync(path.resolve(import.meta.dirname, 'package.json'), 'utf-8')
) as { version: string }

export default defineConfig({
  cacheDir: path.resolve(ROOT, '.vite-cache', SERVER_KEY),
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  server: process.env.VITEST
    ? {}
    : {
        fs: {
          allow: [ROOT, realpathSync(path.resolve(ROOT, 'node_modules'))],
        },
        proxy: {
          '/api': {
            target: process.env.AERONA_API_ORIGIN ?? 'http://127.0.0.1:8000',
            changeOrigin: false,
          },
        },
      },
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    silent: 'passed-only',
    unstubEnvs: true,
    setupFiles: ['src/test-utils/setup.ts'],
    expect: { poll: { timeout: ELEMENT_WAIT_MS } },
    browser: {
      enabled: true,
      provider: playwright(),
      instances: [{ browser: 'chromium' }],
    },
    coverage: {
      exclude: [
        'src/components/ui/**',
        'src/assets/**',
        'src/routeTree.gen.ts',
        'src/test-utils/**',
        'src/routes/**',
      ],
    },
  },
})
