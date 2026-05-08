<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <CrowsNestLogo :size="64" />
        <h1>CrowsNest</h1>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="field">
          <label for="username">Username</label>
          <InputText
            id="username"
            v-model="username"
            placeholder="admin"
            autocomplete="username"
            :disabled="loading"
            fluid
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <Password
            id="password"
            v-model="password"
            placeholder="••••••••"
            :feedback="false"
            toggleMask
            autocomplete="current-password"
            :disabled="loading"
            fluid
          />
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          label="Sign in"
          icon="pi pi-sign-in"
          :loading="loading"
          fluid
          class="mt-2"
        />
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Button from 'primevue/button'
import Message from 'primevue/message'
import CrowsNestLogo from './CrowsNestLogo.vue'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await axios.post('/api/auth/login', {
      username: username.value,
      password: password.value,
    })
    localStorage.setItem('token', data.token)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f1117;
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: #1a1d27;
  border: 1px solid #2d3148;
  border-radius: 12px;
  padding: 2.5rem;
}
.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 2rem;
}
.login-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #e2e8f0;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-bottom: 1.25rem;
}
.field label {
  font-size: 0.875rem;
  color: #94a3b8;
}
.mt-2 {
  margin-top: 0.5rem;
}
</style>
