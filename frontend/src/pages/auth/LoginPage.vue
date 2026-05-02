<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">
        <div class="logo-sq">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
            <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
            <line x1="12" y1="22.08" x2="12" y2="12" />
          </svg>
        </div>
        <span class="logo-text">ComNet</span>
      </div>
      <p class="login-sub">Система обліку майна підрозділу</p>

      <div class="form-group">
        <label class="form-label" for="f-username">Логін</label>
        <input
          id="f-username"
          v-model="username"
          class="form-input"
          :class="{ error: errorField === 'username' }"
          type="text"
          placeholder="admin"
          autocomplete="username"
          @keydown.enter="submit"
        />
      </div>

      <div class="form-group">
        <label class="form-label" for="f-password">Пароль</label>
        <div class="pw-wrap">
          <input
            id="f-password"
            v-model="password"
            class="form-input"
            :class="{ error: errorField === 'password' }"
            :type="showPassword ? 'text' : 'password'"
            placeholder="••••••••"
            autocomplete="current-password"
            @keydown.enter="submit"
          />
          <button class="pw-toggle" type="button" @click="showPassword = !showPassword" title="Показати пароль">
            <!-- eye open -->
            <svg v-show="!showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <!-- eye off -->
            <svg v-show="showPassword" width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <button class="btn-login" :disabled="loading" @click="submit">
        {{ loading ? 'Вхід…' : 'Увійти' }}
      </button>

      <div class="login-footer">ComNet · Система обліку майна · v1.0</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth.js'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const errorMsg = ref('')
const errorField = ref('')

async function submit() {
  errorMsg.value = ''
  errorField.value = ''

  if (!username.value.trim()) {
    errorField.value = 'username'
    return
  }
  if (!password.value) {
    errorField.value = 'password'
    return
  }

  loading.value = true
  try {
    await authStore.login(username.value.trim(), password.value)
    router.push('/items')
  } catch {
    errorMsg.value = 'Невірний логін або пароль'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}

.login-card {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xl);
  width: 400px;
  max-width: calc(100vw - 48px);
  padding: 44px 40px 36px;
  animation: cardIn 0.3s ease-out both;
}

@keyframes cardIn {
  from { opacity: 0; transform: translateY(10px); }
}

.login-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 6px;
}

.logo-sq {
  width: 36px;
  height: 36px;
  background: var(--accent);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.logo-text {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.login-sub {
  text-align: center;
  font-size: 13px;
  color: var(--text-light);
  margin-bottom: 36px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-mid);
}

.form-input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 14px;
  color: var(--text);
  background: var(--bg);
  outline: none;
  transition: all 0.15s;
  width: 100%;
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
  background: var(--surface);
}

.form-input::placeholder { color: var(--text-light); }

.form-input.error {
  border-color: var(--red);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.pw-wrap { position: relative; }

.pw-wrap .form-input { padding-right: 44px; }

.pw-toggle {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-light);
  padding: 4px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  transition: color 0.12s;
}

.pw-toggle:hover { color: var(--text-mid); }

.error-msg {
  font-size: 13px;
  color: var(--red);
  margin-bottom: 8px;
  text-align: center;
}

.btn-login {
  width: 100%;
  margin-top: 8px;
  padding: 11px 20px;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 14.5px;
  font-weight: 700;
  color: white;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-login:hover:not(:disabled) {
  background: var(--accent-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px var(--accent-ring);
}

.btn-login:active { transform: translateY(0); box-shadow: none; }

.btn-login:disabled { opacity: 0.6; cursor: not-allowed; }

.login-footer {
  text-align: center;
  margin-top: 28px;
  font-size: 11.5px;
  color: var(--text-light);
}
</style>
