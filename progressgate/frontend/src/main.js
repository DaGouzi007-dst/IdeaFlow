import { createApp, h } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

const Placeholder = { render: () => h('span') }
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/tasks' },
    { path: '/tasks', name: 'tasks', component: Placeholder },
    { path: '/decisions', name: 'decisions', component: Placeholder },
  ],
})

createApp(App).use(router).mount('#app')
