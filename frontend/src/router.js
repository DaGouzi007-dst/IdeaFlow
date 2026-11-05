import { createRouter, createWebHistory } from 'vue-router'
import IdeaList from './views/IdeaList.vue'
import IdeaDetail from './views/IdeaDetail.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/ideas' },
    { path: '/ideas', name: 'ideas', component: IdeaList },
    { path: '/ideas/:id', name: 'idea', component: IdeaDetail },
  ],
})
