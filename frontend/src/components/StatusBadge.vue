<script setup lang="ts">
import { computed } from 'vue'

import type { AppointmentStatus } from '@/api/types'
import { APPOINTMENT_STATUS, type Tone } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    status?: AppointmentStatus
    label?: string
    tone?: Tone
    dot?: boolean
  }>(),
  { dot: true },
)

const meta = computed(() => (props.status ? APPOINTMENT_STATUS[props.status] : null))
const resolvedLabel = computed(() => props.label ?? meta.value?.label ?? '—')
const resolvedTone = computed<Tone>(() => props.tone ?? meta.value?.tone ?? 'slate')
</script>

<template>
  <span class="badge" :class="`badge--${resolvedTone}`">
    <span v-if="dot" class="badge-dot" aria-hidden="true" />
    {{ resolvedLabel }}
  </span>
</template>
