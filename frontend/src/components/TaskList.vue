<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import type { OperationalTask } from '@/api/types'
import { SEVERITY_META, formatDateTime, formatNumber } from '@/utils/format'
import Icon from './Icon.vue'
import StatusBadge from './StatusBadge.vue'

const props = withDefaults(
  defineProps<{ tasks: OperationalTask[]; limit?: number }>(),
  { limit: 6 },
)

const visible = computed(() => props.tasks.slice(0, props.limit))
</script>

<template>
  <div v-if="visible.length" class="task-list">
    <article
      v-for="task in visible"
      :key="task.id"
      class="task-item"
      :class="`task-item--${task.severity}`"
    >
      <div class="pt-0.5">
        <Icon
          :name="task.severity === 'critical' ? 'alert' : task.severity === 'warning' ? 'clock' : 'info'"
          :size="16"
        />
      </div>
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <StatusBadge :label="SEVERITY_META[task.severity].label" :tone="SEVERITY_META[task.severity].tone" />
          <span class="tiny subtle">{{ formatNumber(task.count) }} registro(s)</span>
        </div>
        <h4 class="task-title mt-1.5">{{ task.title }}</h4>
        <p class="task-detail">{{ task.detail }}</p>
        <code class="task-rule">{{ task.rule }}</code>
        <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
          <span v-if="task.due_at" class="tiny subtle">
            Prazo sugerido: {{ formatDateTime(task.due_at) }}
          </span>
          <RouterLink v-if="task.link" :to="task.link" class="btn btn-sm btn-ghost">
            Abrir <Icon name="chevron-right" :size="13" />
          </RouterLink>
        </div>
      </div>
    </article>
  </div>
  <div v-else class="note-box">
    <Icon name="check" :size="16" />
    Nenhuma pendência operacional no momento. As regras continuam sendo avaliadas a cada consulta.
  </div>
</template>
