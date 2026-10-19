<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'card' | 'table' | 'chart' | 'text'
    rows?: number
    height?: string
  }>(),
  { variant: 'card', rows: 3, height: '320px' },
)
</script>

<template>
  <div v-if="variant === 'text'" class="flex flex-col gap-2" aria-hidden="true">
    <div v-for="row in rows" :key="row" class="skeleton" :style="{ height: '12px', width: `${95 - row * 9}%` }" />
  </div>

  <div v-else-if="variant === 'table'" class="table-wrap" aria-hidden="true">
    <div class="p-4 flex flex-col gap-3">
      <div class="skeleton" style="height: 24px; width: 100%" />
      <div v-for="row in rows" :key="row" class="skeleton" style="height: 34px; width: 100%" />
    </div>
  </div>

  <div v-else-if="variant === 'chart'" class="skeleton" :style="{ height }" aria-hidden="true" />

  <div v-else class="card p-5 flex flex-col gap-4" aria-hidden="true">
    <div class="skeleton" style="height: 14px; width: 42%" />
    <div class="skeleton" style="height: 30px; width: 68%" />
    <div class="skeleton" style="height: 10px; width: 100%" />
  </div>
</template>
