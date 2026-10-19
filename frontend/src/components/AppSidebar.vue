<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import type { IconName } from '@/utils/icons'
import Icon from './Icon.vue'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const meta = useMetaStore()
const route = useRoute()

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

interface NavItem {
  to: string
  label: string
  icon: IconName
}

interface NavSection {
  label: string
  items: NavItem[]
}

const sections = computed<NavSection[]>(() => {
  const base: NavSection[] = [
    {
      label: 'Visão geral',
      items: [
        { to: '/', label: 'Dashboard', icon: 'dashboard' },
        { to: '/agenda', label: 'Agenda e operação', icon: 'calendar' },
      ],
    },
    {
      label: 'Gestão',
      items: [
        { to: '/profissionais', label: 'Profissionais', icon: 'users' },
        { to: '/atendimentos', label: 'Atendimentos', icon: 'clipboard' },
        { to: '/analytics', label: 'Analytics', icon: 'chart' },
      ],
    },
    {
      label: 'Operação',
      items: [{ to: '/qualidade', label: 'Qualidade dos dados', icon: 'shield' }],
    },
  ]

  if (auth.isManager) {
    base.push({
      label: 'Sistema',
      items: [{ to: '/admin', label: 'Administração', icon: 'settings' }],
    })
  }

  return base
})
</script>

<template>
  <aside
    class="sidebar scrollbar-thin"
    :class="{ 'is-open': open }"
    aria-label="Navegação principal"
  >
    <RouterLink to="/" class="brand" @click="emit('close')">
      <span class="brand-mark">
        <Icon name="activity" :size="22" />
      </span>
      <span class="min-w-0">
        <span class="brand-title block">Clinic Analytics</span>
        <span class="brand-sub block">PAGCC · portfólio</span>
      </span>
    </RouterLink>

    <nav class="flex flex-col gap-0.5">
      <template v-for="section in sections" :key="section.label">
        <p class="nav-section">{{ section.label }}</p>
        <RouterLink
          v-for="item in section.items"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'is-active': isActive(item.to) }"
          @click="emit('close')"
        >
          <Icon :name="item.icon" class="nav-icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </template>
    </nav>

    <div class="sidebar-footer">
      <p class="font-medium text-slate-300">{{ meta.clinicName }}</p>
      <p class="mt-0.5">{{ meta.timezone }} · dados sintéticos</p>
      <span class="sidebar-note">
        <Icon name="sparkles" :size="11" />
        Ambiente de demonstração
      </span>
      <p class="mt-3 text-[10.5px] leading-relaxed">
        Não é software clínico. Nenhum dado real de paciente é utilizado.
      </p>
    </div>
  </aside>
</template>
