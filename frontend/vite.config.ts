import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'
import path from 'path'
import fs from 'fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      template: { transformAssetUrls }
    }),
    quasar({
      sassVariables: path.resolve(__dirname, 'src/quasar-variables.sass')
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    https: {
      pfx: fs.readFileSync(path.resolve(__dirname, 'cert/vera-office.pfx')),
      passphrase: 'vera-office-2026'
    },
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.VITE_BACKEND_PORT || 8081}`,
        changeOrigin: true
      }
    }
  }
})
