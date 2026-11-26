import { createRouter, createWebHistory } from 'vue-router'
import IdeaList from './views/IdeaList.vue'
import IdeaNew from './views/IdeaNew.vue'
import IdeaDetail from './views/IdeaDetail.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/ideas' },
    { path: '/ideas', name: 'ideas', component: IdeaList },
    // 放在 /ideas/:id 之前，避免 new 被解析为编号
    { path: '/ideas/new', name: 'idea-new', component: IdeaNew },
    { path: '/ideas/:id', name: 'idea', component: IdeaDetail },
  ],
})
