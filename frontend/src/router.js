import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from './components/LoginPage.vue'
import MainLayout from './components/MainLayout.vue'

const routes = [
  { path: '/login', component: LoginPage },
  {
    path: '/',
    component: MainLayout,
    beforeEnter: () => {
      if (!localStorage.getItem('token')) return '/login'
    },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
