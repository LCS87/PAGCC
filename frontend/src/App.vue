<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function handleExpired() {
  auth.logout()
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    void router.push({ name: 'login', query: { redirect: current.fullPath, expired: '1' } })
  }
}

onMounted(() => window.addEventListener('auth:expired', handleExpired))
onBeforeUnmount(() => window.removeEventListener('auth:expired', handleExpired))
</script>

<template>
  <RouterView />
</template>
