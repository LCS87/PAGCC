import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/endpoints'
import { TOKEN_KEY, USER_KEY, setToken } from '@/api/client'
import type { Role, User } from '@/api/types'

function loadStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(loadStoredUser())

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const isManager = computed(
    () => user.value?.role === 'ADMIN' || user.value?.role === 'GESTOR',
  )

  function hasRole(...roles: Role[]): boolean {
    return Boolean(user.value && roles.includes(user.value.role))
  }

  function persist() {
    setToken(token.value)
    if (user.value) localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    else localStorage.removeItem(USER_KEY)
  }

  async function login(email: string, password: string) {
    const response = await authApi.login(email, password)
    token.value = response.access_token
    user.value = response.user
    persist()
    return response.user
  }

  function logout() {
    token.value = null
    user.value = null
    persist()
  }

  async function refreshUser() {
    if (!token.value) return
    try {
      user.value = await authApi.me()
      persist()
    } catch {
      logout()
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    isManager,
    hasRole,
    login,
    logout,
    refreshUser,
  }
})
