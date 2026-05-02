import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import http from '../api/http.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('token'))

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)

    const res = await http.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchMe()
  }

  async function fetchMe() {
    const res = await http.get('/auth/me')
    user.value = res.data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isAuthenticated, login, logout, fetchMe }
})
