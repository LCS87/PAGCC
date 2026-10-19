<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { errorMessage } from '@/api/client'
import { appointmentApi, kpiApi } from '@/api/endpoints'
import type {
  Appointment,
  AppointmentStatus,
  DashboardFilters,
  OperationalSummary,
} from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import TaskList from '@/components/TaskList.vue'
import { useMetaStore } from '@/stores/meta'
import {
  APPOINTMENT_STATUS,
  addDaysISO,
  diffDays,
  formatDate,
  formatMoney,
  formatNumber,
  formatTime,
  formatWeekdayDate,
  isoToDateISO,
  startOfWeekISO,
} from '@/utils/format'

const meta = useMetaStore()
const route = useRoute()
const filters = ref<DashboardFilters>({
  start: '',
  end: '',
  unit_id: null,
  specialty_id: null,
  professional_id: null,
})
const requestedProfessional = Number(route.query.professional)
if (Number.isFinite(requestedProfessional) && requestedProfessional > 0) {
  filters.value.professional_id = requestedProfessional
}
const statusFilter = ref<AppointmentStatus | ''>('')
const viewMode = ref<'day' | 'week'>('week')
const appointments = ref<Appointment[]>([])
const operational = ref<OperationalSummary | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

function applyPeriod(anchor: string, mode: 'day' | 'week') {
  filters.value = {
    ...filters.value,
    start: mode === 'week' ? startOfWeekISO(anchor) : anchor,
    end: mode === 'week' ? addDaysISO(startOfWeekISO(anchor), 6) : anchor,
  }
}

watch(
  () => meta.options,
  (options) => {
    if (options && !filters.value.end) applyPeriod(options.demo_today, 'week')
  },
  { immediate: true },
)

watch(viewMode, () => {
  if (meta.options) applyPeriod(filters.value.start || meta.demoToday, viewMode.value)
})

watch(
  [filters, statusFilter],
  () => void load(),
  { deep: true },
)

async function load() {
  if (!filters.value.end) return
  loading.value = true
  error.value = null
  try {
    const [agendaData, operationalData] = await Promise.all([
      appointmentApi.agenda({
        ...filters.value,
        status: statusFilter.value ? [statusFilter.value] : undefined,
      }),
      kpiApi.operational(),
    ])
    appointments.value = agendaData
    operational.value = operationalData
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void meta.load()
  void load()
})

function shift(days: number) {
  const start = addDaysISO(filters.value.start, days)
  applyPeriod(start, viewMode.value)
}

function goToday() {
  if (meta.options) applyPeriod(meta.demoToday, viewMode.value)
}

const groups = computed(() => {
  const map = new Map<string, Appointment[]>()
  for (const appointment of appointments.value) {
    const day = isoToDateISO(appointment.scheduled_start)
    const list = map.get(day) ?? []
    list.push(appointment)
    map.set(day, list)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, items]) => ({ date, items }))
})

const statusCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const appointment of appointments.value) {
    counts[appointment.status] = (counts[appointment.status] ?? 0) + 1
  }
  return counts
})

const rangeLabel = computed(() => {
  if (!filters.value.start) return '—'
  return diffDays(filters.value.start, filters.value.end) === 0
    ? formatDate(filters.value.start)
    : `${formatDate(filters.value.start)} a ${formatDate(filters.value.end)}`
})

const professionalCount = computed(() => {
  const ids = new Set(appointments.value.map((item) => item.professional.id))
  return ids.size
})

function statusCountsFor(items: Appointment[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const item of items) {
    counts[item.status] = (counts[item.status] ?? 0) + 1
  }
  return counts
}

function onStatusChange(event: Event) {
  statusFilter.value = (event.target as HTMLSelectElement).value as AppointmentStatus | ''
}

function statusLabel(status: string): string {
  return APPOINTMENT_STATUS[status as AppointmentStatus]?.label ?? status.replaceAll('_', ' ')
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Operação"
      title="Agenda e operação"
      description="Consultas por dia, status e profissional. Use a navegação para percorrer os dias e abrir o detalhe administrativo de cada agendamento."
    >
      <template #actions>
        <div class="preset-group" role="group" aria-label="Modo de visualização">
          <button
            type="button"
            class="preset-btn"
            :class="{ 'is-active': viewMode === 'day' }"
            @click="viewMode = 'day'"
          >
            Dia
          </button>
          <button
            type="button"
            class="preset-btn"
            :class="{ 'is-active': viewMode === 'week' }"
            @click="viewMode = 'week'"
          >
            Semana
          </button>
        </div>
        <button type="button" class="btn btn-sm" @click="goToday">Hoje</button>
        <button type="button" class="btn btn-sm btn-icon" aria-label="Semana anterior" @click="shift(viewMode === 'week' ? -7 : -1)">
          <Icon name="chevron-left" :size="15" />
        </button>
        <button type="button" class="btn btn-sm btn-icon" aria-label="Próxima semana" @click="shift(viewMode === 'week' ? 7 : 1)">
          <Icon name="chevron-right" :size="15" />
        </button>
      </template>
    </PageHeader>

    <div class="filter-bar">
      <div class="field">
        <span class="label">Período</span>
        <span class="badge badge--teal">{{ rangeLabel }}</span>
      </div>
      <label class="field">
        <span class="label">Unidade</span>
        <select
          class="select"
          :value="filters.unit_id ?? ''"
          @change="filters = { ...filters, unit_id: ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null }"
        >
          <option value="">Todas</option>
          <option v-for="unit in meta.options?.units ?? []" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
        </select>
      </label>
      <label class="field">
        <span class="label">Especialidade</span>
        <select
          class="select"
          :value="filters.specialty_id ?? ''"
          @change="filters = { ...filters, specialty_id: ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null }"
        >
          <option value="">Todas</option>
          <option v-for="specialty in meta.options?.specialties ?? []" :key="specialty.id" :value="specialty.id">{{ specialty.name }}</option>
        </select>
      </label>
      <label class="field">
        <span class="label">Profissional</span>
        <select
          class="select"
          :value="filters.professional_id ?? ''"
          @change="filters = { ...filters, professional_id: ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null }"
        >
          <option value="">Todos</option>
          <option v-for="professional in meta.options?.professionals ?? []" :key="professional.id" :value="professional.id">{{ professional.full_name }}</option>
        </select>
      </label>
      <label class="field">
        <span class="label">Status</span>
        <select class="select" :value="statusFilter" @change="onStatusChange">
          <option value="">Todos</option>
          <option v-for="status in meta.options?.statuses ?? []" :key="status" :value="status">{{ statusLabel(status) }}</option>
        </select>
      </label>
      <div class="ml-auto flex items-end gap-2">
        <span class="badge badge--slate">{{ formatNumber(appointments.length) }} consultas</span>
        <button type="button" class="btn btn-sm btn-icon" aria-label="Atualizar agenda" @click="load">
          <Icon name="refresh" :size="14" />
        </button>
      </div>
    </div>

    <ErrorState v-if="error" class="mt-4" :message="error" @retry="load" />

    <div v-else class="mt-4 grid gap-4 xl:grid-cols-4">
      <div class="xl:col-span-3">
        <div v-if="loading" class="flex flex-col gap-3">
          <LoadingSkeleton v-for="index in 3" :key="index" variant="table" :rows="4" />
        </div>

        <EmptyState
          v-else-if="groups.length === 0"
          class="mt-2"
          title="Nenhuma consulta no período"
          description="Troque o dia, o status ou limpe os filtros para ver outros agendamentos."
          icon="calendar"
        />

        <div v-else class="flex flex-col gap-4">
          <section v-for="group in groups" :key="group.date" class="card overflow-hidden">
            <header class="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-3">
              <div>
                <h2 class="text-[13.5px] font-semibold">{{ formatWeekdayDate(group.date) }}</h2>
                <p class="tiny subtle">{{ formatNumber(group.items.length) }} agendamento(s)</p>
              </div>
              <div class="flex flex-wrap gap-1">
                <StatusBadge
                  v-for="(count, status) in statusCountsFor(group.items)"
                  :key="status"
                  :status="status as AppointmentStatus"
                  :label="`${statusLabel(status)} · ${count}`"
                />
              </div>
            </header>
            <div class="table-wrap" style="border: 0; border-radius: 0; box-shadow: none">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Hora</th>
                    <th>Paciente</th>
                    <th>Profissional</th>
                    <th>Serviço</th>
                    <th>Unidade</th>
                    <th>Status</th>
                    <th class="num">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="appointment in group.items" :key="appointment.id">
                    <td class="strong">{{ formatTime(appointment.scheduled_start) }}</td>
                    <td>
                      <RouterLink :to="`/atendimentos?search=${appointment.patient_ref}`" class="table-link mono">
                        {{ appointment.patient_ref }}
                      </RouterLink>
                      <p class="tiny subtle">{{ appointment.external_id }}</p>
                    </td>
                    <td>
                      <RouterLink :to="`/profissionais/${appointment.professional.id}`" class="table-link">
                        {{ appointment.professional.full_name }}
                      </RouterLink>
                      <p class="tiny subtle">{{ appointment.specialty.name }}</p>
                    </td>
                    <td>
                      {{ appointment.service_type.name }}
                      <p class="tiny subtle">{{ appointment.service_type.duration_minutes }} min</p>
                    </td>
                    <td>{{ appointment.unit.name }}</td>
                    <td><StatusBadge :status="appointment.status" /></td>
                    <td class="num">{{ formatMoney(appointment.priced_amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      <aside class="flex flex-col gap-4">
        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Resumo do período</h2>
              <p class="card-subtitle">{{ professionalCount }} profissional(is) com agenda</p>
            </div>
          </header>
          <div class="card-body flex flex-col gap-1.5">
            <div v-for="(count, status) in statusCounts" :key="status" class="meter-row">
              <span class="meter-label">{{ statusLabel(String(status)) }}</span>
              <span class="meter-value">{{ formatNumber(count) }}</span>
            </div>
            <p v-if="Object.keys(statusCounts).length === 0" class="tiny subtle">Sem dados.</p>
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Pendências</h2>
              <p class="card-subtitle">Regras operacionais avaliadas agora</p>
            </div>
          </header>
          <div class="card-body">
            <TaskList :tasks="operational?.tasks ?? []" :limit="4" />
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>
