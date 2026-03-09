import { createApp } from 'vue'
import { Quasar, Notify, Dialog, Loading, Dark } from 'quasar'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useAuthStore } from './stores/auth'

// Import Quasar css
import '@quasar/extras/material-icons/material-icons.css'
import 'quasar/src/css/index.sass'

const app = createApp(App)

app.use(Quasar, {
  plugins: {
    Notify,
    Dialog,
    Loading,
    Dark
  },
  config: {
    dark: 'auto',
    notify: {
      position: 'bottom',
      timeout: 3000
    }
  }
})

const pinia = createPinia()
app.use(pinia)
app.use(router)

// Auth-Store initialisieren (setzt Bearer Token in Axios wenn vorhanden)
const authStore = useAuthStore()
authStore.init()

app.mount('#app')
