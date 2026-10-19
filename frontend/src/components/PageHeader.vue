<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string
    eyebrow?: string
    description?: string
  }>(),
  { eyebrow: '' },
)
</script>

<template>
  <header class="page-header">
    <div class="min-w-0">
      <p v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</p>
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>
