<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth.js'

const auth = useAuthStore()

// On full page-load (refresh, deep-link), restore the user from /auth/me
// if a token is present. Otherwise `auth.user` stays null until next login,
// which breaks role-gated UI like the Users tab in /settings.
onMounted(() => {
  if (auth.token && !auth.user) {
    auth.fetchMe().catch(() => { /* invalid token — guard will redirect */ })
  }
})
</script>
