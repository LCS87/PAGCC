<script setup lang="ts">
import Icon from './Icon.vue'

withDefaults(
  defineProps<{
    title?: string
    message: string
  }>(),
  { title: 'Não foi possível carregar os dados' },
)

defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="error-state" role="alert">
    <div class="state-icon" style="color: var(--danger)"><Icon name="alert" :size="20" /></div>
    <h3>{{ title }}</h3>
    <p>{{ message }}</p>
    <button type="button" class="btn btn-sm" @click="$emit('retry')">
      <Icon name="refresh" :size="14" /> Tentar novamente
    </button>
  </div>
</template>
