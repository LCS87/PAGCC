<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'

import type { DashboardFilters, FilterOptions } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { addDaysISO, diffDays } from '@/utils/format'
import Icon from './Icon.vue'

const props = withDefaults(
  defineProps<{
    options: FilterOptions | null
    presets?: boolean
  }>(),
  { presets: true },
)

const model = defineModel<DashboardFilters>({ required: true })
const auth = useAuthStore()
const expanded = ref(false)

const PRESETS = [
  { label: '7d', days: 7 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
  { label: '180d', days: 180 },
] as const

const lockedProfessional = computed(() => auth.user?.role === 'PROFISSIONAL')

const professionalOptions = computed(() => {
  let professionals = props.options?.professionals ?? []
  if (lockedProfessional.value && auth.user?.professional_id) {
    professionals = professionals.filter((item) => item.id === auth.user?.professional_id)
  }
  if (model.value.unit_id) {
    professionals = professionals.filter((item) => item.unit.id === model.value.unit_id)
  }
  if (model.value.specialty_id) {
    professionals = professionals.filter(
      (item) => item.specialty.id === model.value.specialty_id,
    )
  }
  return professionals
})

const activePreset = computed(() => {
  if (!props.options) return null
  if (model.value.end !== props.options.demo_today) return null
  return PRESETS.find(
    (preset) => diffDays(model.value.start, model.value.end) === preset.days - 1,
  )?.days ?? null
})

watchEffect(() => {
  if (lockedProfessional.value && auth.user?.professional_id) {
    if (model.value.professional_id !== auth.user.professional_id) {
      update({ professional_id: auth.user.professional_id })
    }
  }
})

function update(patch: Partial<DashboardFilters>) {
  model.value = { ...model.value, ...patch }
}

function applyPreset(days: number) {
  if (!props.options) return
  update({
    start: addDaysISO(props.options.demo_today, -(days - 1)),
    end: props.options.demo_today,
  })
}

function reset() {
  if (!props.options) return
  update({
    start: addDaysISO(props.options.demo_today, -29),
    end: props.options.demo_today,
    unit_id: null,
    specialty_id: null,
    professional_id: lockedProfessional.value ? auth.user?.professional_id ?? null : null,
  })
}

function onDate(key: 'start' | 'end', event: Event) {
  const value = (event.target as HTMLInputElement).value
  if (!value) return
  if (key === 'start') {
    update({ start: value, end: value > model.value.end ? value : model.value.end })
  } else {
    update({ end: value, start: value < model.value.start ? value : model.value.start })
  }
}

function onUnit(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const unitId = value ? Number(value) : null
  const professionalStillValid = professionalOptions.value.some(
    (item) => item.id === model.value.professional_id,
  )
  update({
    unit_id: unitId,
    professional_id: professionalStillValid ? model.value.professional_id : null,
  })
}

function onSpecialty(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const specialtyId = value ? Number(value) : null
  const professionalStillValid = professionalOptions.value.some(
    (item) => item.id === model.value.professional_id,
  )
  update({
    specialty_id: specialtyId,
    professional_id: professionalStillValid ? model.value.professional_id : null,
  })
}

function onProfessional(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  update({ professional_id: value ? Number(value) : null })
}
</script>

<template>
  <section class="filter-bar" aria-label="Filtros do período e dimensões">
    <div class="flex w-full items-center gap-2 sm:w-auto">
      <div v-if="presets" class="preset-group" role="group" aria-label="Períodos rápidos">
        <button
          v-for="preset in PRESETS"
          :key="preset.days"
          type="button"
          class="preset-btn"
          :class="{ 'is-active': activePreset === preset.days }"
          :aria-label="`Últimos ${preset.days} dias`"
          @click="applyPreset(preset.days)"
        >
          {{ preset.label }}
        </button>
      </div>
      <button
        type="button"
        class="btn btn-sm ml-auto sm:hidden"
        :aria-expanded="expanded"
        aria-controls="filtros-avancados"
        @click="expanded = !expanded"
      >
        <Icon name="filter" :size="13" /> Filtros
      </button>
    </div>

    <div id="filtros-avancados" class="filter-fields" :class="{ 'is-open': expanded }">
      <label class="field">
        <span class="label">Início</span>
        <input
          class="input"
          type="date"
          :value="model.start"
          :min="options?.min_date ?? undefined"
          :max="model.end"
          @change="onDate('start', $event)"
        />
      </label>

      <label class="field">
        <span class="label">Fim</span>
        <input
          class="input"
          type="date"
          :value="model.end"
          :min="model.start"
          :max="options?.max_date ?? undefined"
          @change="onDate('end', $event)"
        />
      </label>

      <label class="field">
        <span class="label">Unidade</span>
        <select class="select" :value="model.unit_id ?? ''" @change="onUnit">
          <option value="">Todas</option>
          <option v-for="unit in options?.units ?? []" :key="unit.id" :value="unit.id">
            {{ unit.name }}
          </option>
        </select>
      </label>

      <label class="field">
        <span class="label">Especialidade</span>
        <select class="select" :value="model.specialty_id ?? ''" @change="onSpecialty">
          <option value="">Todas</option>
          <option
            v-for="specialty in options?.specialties ?? []"
            :key="specialty.id"
            :value="specialty.id"
          >
            {{ specialty.name }}
          </option>
        </select>
      </label>

      <label class="field">
        <span class="label">Profissional</span>
        <select
          class="select"
          :value="model.professional_id ?? ''"
          :disabled="lockedProfessional"
          @change="onProfessional"
        >
          <option value="">Todos</option>
          <option
            v-for="professional in professionalOptions"
            :key="professional.id"
            :value="professional.id"
          >
            {{ professional.full_name }}
          </option>
        </select>
      </label>

      <div class="ml-auto flex items-end">
        <button type="button" class="btn btn-sm btn-ghost" @click="reset">
          <Icon name="refresh" :size="13" /> Limpar
        </button>
      </div>
    </div>
  </section>
</template>
