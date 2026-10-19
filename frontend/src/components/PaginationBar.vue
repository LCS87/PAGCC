<script setup lang="ts">
import { computed } from 'vue'

import { formatNumber } from '@/utils/format'
import Icon from './Icon.vue'

const props = defineProps<{
  page: number
  pages: number
  total: number
  pageSize: number
}>()

const emit = defineEmits<{ 'update:page': [page: number] }>()

const start = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const end = computed(() => Math.min(props.page * props.pageSize, props.total))

const items = computed<(number | 'gap')[]>(() => {
  const total = props.pages
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)
  const current = props.page
  const result: (number | 'gap')[] = [1]
  if (current > 4) result.push('gap')
  const first = Math.max(2, current - 1)
  const last = Math.min(total - 1, current + 1)
  for (let page = first; page <= last; page += 1) result.push(page)
  if (current < total - 3) result.push('gap')
  result.push(total)
  return result
})

function go(page: number) {
  if (page < 1 || page > props.pages || page === props.page) return
  emit('update:page', page)
}
</script>

<template>
  <nav class="flex flex-wrap items-center justify-between gap-3 px-1 py-3" aria-label="Paginação">
    <p class="tiny subtle">
      Mostrando {{ formatNumber(start) }}–{{ formatNumber(end) }} de
      {{ formatNumber(total) }}
    </p>
    <div class="flex items-center gap-1">
      <button
        type="button"
        class="btn btn-sm btn-icon"
        :disabled="page <= 1"
        aria-label="Página anterior"
        @click="go(page - 1)"
      >
        <Icon name="chevron-left" :size="14" />
      </button>
      <template v-for="(item, index) in items" :key="`${item}-${index}`">
        <span v-if="item === 'gap'" class="tiny subtle px-1">…</span>
        <button
          v-else
          type="button"
          class="btn btn-sm btn-icon"
          :class="{ 'btn-primary': item === page }"
          :aria-current="item === page ? 'page' : undefined"
          :aria-label="`Página ${item}`"
          @click="go(item)"
        >
          {{ item }}
        </button>
      </template>
      <button
        type="button"
        class="btn btn-sm btn-icon"
        :disabled="page >= pages"
        aria-label="Próxima página"
        @click="go(page + 1)"
      >
        <Icon name="chevron-right" :size="14" />
      </button>
    </div>
  </nav>
</template>
