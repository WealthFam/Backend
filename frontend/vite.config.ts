// @ts-nocheck
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import path from 'path'
import { execSync } from 'child_process'
import fs from 'fs'

// Read version.json from root
let version = '0.0.0'
try {
  const versionData = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../version.json'), 'utf-8'))
  version = `${versionData.major}.${versionData.minor}.${versionData.patch}`
} catch (e) {
  console.warn('Could not read version.json')
}

// Get latest 4 digits of master commit or from environment
let build = (process.env.VITE_APP_BUILD || '').trim() || '0000'

if (build === '0000') {
  try {
    build = execSync('git rev-parse master').toString().trim().substring(0, 4)
  } catch (e) {
    console.warn('Could not get git build number from master, trying HEAD...')
    try {
      build = execSync('git rev-parse HEAD').toString().trim().substring(0, 4)
    } catch (e2) {
      console.warn('Could not get git build number, using fallback.')
    }
  }
}

console.log(`--- Building WealthFam v${version} (Build: ${build}) ---`)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
  ],
  define: {
    '__APP_VERSION__': JSON.stringify(version),
    '__APP_BUILD__': JSON.stringify(build)
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/parser': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/parser/, '/v1'),
      }
    }
  }
})
