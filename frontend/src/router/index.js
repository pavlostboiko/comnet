import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/items' },
  {
    path: '/login',
    component: () => import('../pages/auth/LoginPage.vue'),
  },
  {
    path: '/items',
    component: () => import('../pages/items/ItemsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/movements',
    component: () => import('../pages/movements/MovementsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/residues',
    component: () => import('../pages/PlaceholderPage.vue'),
    meta: { requiresAuth: true, label: 'Залишки' },
  },
  {
    path: '/reports',
    component: () => import('../pages/PlaceholderPage.vue'),
    meta: { requiresAuth: true, label: 'Звіти' },
  },
  {
    path: '/documents',
    component: () => import('../pages/PlaceholderPage.vue'),
    meta: { requiresAuth: true, label: 'Документи' },
  },
  {
    path: '/settings',
    component: () => import('../pages/settings/SettingsPage.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/login' }
  }
})

export default router
