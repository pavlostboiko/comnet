import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

// Routes an operator (non-admin) can access. Everything else redirects
// to /residues (their default landing).
const OPERATOR_ALLOWED = new Set(['/residues', '/items', '/movements', '/login'])

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
    component: () => import('../pages/residues/ResiduesPage.vue'),
    meta: { requiresAuth: true, label: 'Залишки' },
  },
  {
    path: '/reports',
    component: () => import('../pages/PlaceholderPage.vue'),
    meta: { requiresAuth: true, label: 'Звіти', adminOnly: true },
  },
  {
    path: '/documents',
    component: () => import('../pages/documents/DocumentsPage.vue'),
    meta: { requiresAuth: true, adminOnly: true },
  },
  {
    path: '/documents/:id',
    component: () => import('../pages/documents/DocumentFormPage.vue'),
    meta: { requiresAuth: true, adminOnly: true },
  },
  {
    path: '/settings',
    component: () => import('../pages/settings/SettingsPage.vue'),
    meta: { requiresAuth: true, adminOnly: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    return { path: '/login' }
  }
  if (!to.meta.requiresAuth) return

  const auth = useAuthStore()
  // Ensure we know the user's role. If we haven't fetched /auth/me yet
  // (page reload with a stored token), do it now — guard blocks otherwise.
  if (!auth.user && token) {
    try { await auth.fetchMe() } catch (_e) { /* token invalid → redirect */ }
  }

  const role = auth.user?.role
  if (!role) return   // not authenticated cleanly; loader will retry

  // Non-admin scoping: block admin-only pages, land on /residues instead.
  if (role !== 'admin' && to.meta.adminOnly) {
    return { path: '/residues' }
  }
  // Non-admin visiting '/' — redirect straight to their landing.
  if (role !== 'admin' && to.path === '/') {
    return { path: '/residues' }
  }
})

export default router
