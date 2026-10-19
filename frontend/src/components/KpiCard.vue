<script setup lang="ts">
import { computed } from 'vue'

import type { Kpi } from '@/api/types'
import {
  deltaTone,
  formatByUnit,
  formatDelta,
  formatKpiValue,
  formatNumber,
} from '@/utils/format'
import Icon from './Icon.vue'

const props = defineProps<{ kpi: Kpi }>()

const tone = computed(() => deltaTone(props.kpi.delta_pct, props.kpi.favorable))
const arrow = computed(() => ((props.kpi.delta_pct ?? 0) >= 0 ? 'arrow-up' : 'arrow-down'))
const previous = computed(() =>
  props.kpi.previous === null || props.kpi.previous === undefined
    ? 'sem base anterior'
    : `antes ${formatByUnit(props.kpi.previous, props.kpi.unit)}`,
)
const base = computed(() => {
  if (props.kpi.denominator !== null && props.kpi.denominator !== undefined) {
    return `base ${formatNumber(props.kpi.denominator)}`
  }
  if (props.kpi.sample_size !== null && props.kpi.sample_size !== undefined) {
    return `amostra ${formatNumber(props.kpi.sample_size)}`
  }
  return ''
})
const progress = computed(() =>
  (props.kpi.key === 'attendance_rate' || props.kpi.key === 'occupancy') &&
  props.kpi.value !== null
    ? Math.max(0, Math.min(100, props.kpi.value))
    : null,
)
const showsTarget = computed(
  () => props.kpi.key === 'attendance_rate' || props.kpi.key === 'occupancy',
)
</script>

<template>
  <article class="kpi-card">
    <div class="kpi-label">
      <span>{{ kpi.label }}</span>
      <button
        type="button"
        class="btn btn-ghost btn-icon btn-sm"
        :title="kpi.formula"
        :aria-label="`Fórmula de ${kpi.label}: ${kpi.formula}`"
      >
        <Icon name="info" :size="14" />
      </button>
    </div>

    <p class="kpi-value">{{ formatKpiValue(kpi) }}</p>

    <div v-if="progress !== null" class="progress mt-2" aria-hidden="true">
      <div class="progress-bar" :style="{ width: `${progress}%` }" />
    </div>

    <div class="kpi-foot">
      <span>{{ previous }}</span>
      <span class="delta" :class="`delta--${tone}`">
        <Icon v-if="kpi.delta_pct !== null" :name="arrow" :size="12" />
        {{ formatDelta(kpi.delta_pct) }}
      </span>
    </div>
    <div v-if="base" class="kpi-foot" style="margin-top: 4px">
      <span class="tiny">{{ base }}</span>
      <span v-if="showsTarget" class="tiny">meta operacional: 85%</span>
    </div>
  </article>
</template>
