<script setup lang="ts">
import type { IconName } from '@/utils/icons'
import Icon from './Icon.vue'

withDefaults(
  defineProps<{
    title?: string
    description?: string
    icon?: IconName
  }>(),
  {
    title: 'Nenhum registro encontrado',
    description: 'Ajuste os filtros ou tente outro período.',
    icon: 'search',
  },
)
</script>

<template>
  <div class="empty-state">
    <div class="state-icon"><Icon :name="icon" :size="20" /></div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot name="action" />
  </div>
</template>
