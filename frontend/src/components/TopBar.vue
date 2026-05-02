<template>
  <div class="topbar">
    <div class="logo-area">
      <div class="logo-sq">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"
          stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
          <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
          <line x1="12" y1="22.08" x2="12" y2="12" />
        </svg>
      </div>
      <span class="logo-text">ComNet</span>
    </div>

    <nav class="nav-links">
      <router-link class="nav-link" to="/items">Майно</router-link>
      <router-link class="nav-link" to="/movements">Переміщення</router-link>
      <router-link class="nav-link" to="/residues">Залишки</router-link>
      <router-link class="nav-link" to="/reports">Звіти</router-link>
      <router-link class="nav-link" to="/documents">Документи</router-link>
      <router-link class="nav-link" to="/settings">Налаштування</router-link>
    </nav>

    <div class="tb-right">
      <slot name="actions" />
      <div class="user-pill" @click="authStore.logout(); $router.push('/login')" title="Вийти">
        <div class="user-dot">{{ initials }}</div>
        <span>{{ authStore.user?.username || '—' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()

const initials = computed(() => {
  const name = authStore.user?.username || ''
  return name.slice(0, 2).toUpperCase()
})
</script>

<style scoped>
.topbar {
  height: 54px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  flex-shrink: 0;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-right: 32px;
}

.logo-sq {
  width: 28px;
  height: 28px;
  background: var(--accent);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.nav-links {
  display: flex;
  align-items: stretch;
  height: 100%;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 0 13px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-mid);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.15s;
  text-decoration: none;
  white-space: nowrap;
}

.nav-link:hover {
  color: var(--text);
}

.nav-link.router-link-active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.tb-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 5px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: border-color 0.12s;
}

.user-pill:hover {
  border-color: var(--text-light);
}

.user-dot {
  width: 24px;
  height: 24px;
  background: var(--accent);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9.5px;
  font-weight: 700;
  color: white;
}

.user-pill span {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-mid);
}
</style>
