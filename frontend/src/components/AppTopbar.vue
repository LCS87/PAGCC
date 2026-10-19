<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useThemeStore } from '@/stores/theme'
import { formatDate, initials, roleLabel } from '@/utils/format'
import Icon from './Icon.vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const theme = useThemeStore()

const title = computed(() => route.meta.title ?? 'Clinic Analytics')
const userName = computed(() => auth.user?.full_name ?? 'Visitante')
const userRole = computed(() => (auth.user ? roleLabel(auth.user.role) : ''))

function logout() {
  auth.logout()
  void router.push({ name: 'login' })
}
</script>

<template>
  <header class="topbar">
    <button
      type="button"
      class="btn btn-ghost btn-icon lg:hidden"
      :aria-expanded="open"
      aria-label="Abrir menu de navegação"
      @click="emit('toggle')"
    >
      <Icon :name="open ? 'close' : 'menu'" :size="20" />
    </button>

    <div class="min-w-0">
      <p class="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--subtle)]">
        {{ meta.clinicName }}
      </p>
      <p class="truncate text-[15px] font-semibold">{{ title }}</p>
    </div>

    <div class="ml-auto flex items-center gap-1.5 sm:gap-2">
      <span class="badge badge--slate hidden md:inline-flex" :title="`Data de referência da demonstração (${meta.timezone})`">
        <Icon name="calendar" :size="12" />
        {{ formatDate(meta.demoToday) }} · referência
      </span>

      <button
        type="button"
        class="btn btn-ghost btn-icon"
        :aria-label="theme.mode === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'"
        :title="theme.mode === 'dark' ? 'Tema claro' : 'Tema escuro'"
        @click="theme.toggle()"
      >
        <Icon :name="theme.mode === 'dark' ? 'sun' : 'moon'" :size="18" />
      </button>

      <div class="hidden h-7 w-px bg-[var(--border)] sm:block" />

      <RouterLink
        to="/admin"
        class="flex items-center gap-2.5 rounded-lg px-1 py-1 hover:bg-[var(--surface-3)]"
        :title="auth.isManager ? 'Abrir administração' : 'Perfil'"
      >
        <span class="avatar">{{ initials(userName) }}</span>
        <span class="hidden min-w-0 md:block">
          <span class="block truncate text-[12.5px] font-semibold leading-tight">
            {{ userName }}
          </span>
          <span class="block text-[10.5px] text-[var(--muted)]">{{ userRole }}</span>
        </span>
      </RouterLink>

      <button
        type="button"
        class="btn btn-ghost btn-icon"
        aria-label="Sair"
        title="Sair"
        @click="logout"
      >
        <Icon name="logout" :size="17" />
      </button>
    </div>
  </header>
</template>
