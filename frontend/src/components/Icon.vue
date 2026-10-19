<script setup lang="ts">
import { computed } from 'vue'

import { ICONS, type IconName } from '@/utils/icons'

const props = withDefaults(defineProps<{ name: IconName; size?: number }>(), {
  size: 18,
})

const paths = computed(() => ICONS[props.name] ?? ICONS.info)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(path, index) in paths" :key="index" :d="path" />
  </svg>
</template>
