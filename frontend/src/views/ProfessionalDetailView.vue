<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { errorMessage } from '@/api/client'
import { analyticsApi, professionalApi } from '@/api/endpoints'
import type { ProfessionalProfile, Timeseries } from '@/api/types'
import EChart from '@/components/EChart.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useMetaStore } from '@/stores/meta'
import { useThemeStore } from '@/stores/theme'
import { trendOption } from '@/utils/charts'
import {
  WEEKDAY_LABELS,
  addDaysISO,
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  formatPercent,
  formatSeconds,
  formatTime,
} from '@/utils/format'

const route = useRoute()
const meta = useMetaStore()
const theme = useThemeStore()
const profile = ref<ProfessionalProfile | null>(null)
const series = ref<Timeseries | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const professionalId = computed(() => Number(route.params.id))

async function load() {
  loading.value = true
  error.value = null
  try {
    const [profileData, seriesData] = await Promise.all([
      professionalApi.detail(professionalId.value),
      meta.options
        ? analyticsApi.timeseries(
            {
              start: addDaysISO(meta.demoToday, -89),
              end: meta.demoToday,
              professional_id: professionalId.value,
            },
            'week',
          )
        : Promise.resolve({ granularity: 'week' as const, points: [] }),
    ])
    profile.value = profileData
    series.value = seriesData
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await meta.load()
  await load()
})

watch(professionalId, () => void load())

const availability = computed(() => {
  const map = new Map<number, { start_time: string; end_time: string }[]>()
  for (const window of profile.value?.professional.availabilities ?? []) {
    const list = map.get(window.weekday) ?? []
    list.push({ start_time: window.start_time, end_time: window.end_time })
    map.set(window.weekday, list)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a - b)
    .map(([weekday, windows]) => ({ weekday, windows }))
})

const indicator = computed(() => profile.value?.indicator ?? null)

const chart = computed(() => {
  void theme.mode
  if (!series.value || series.value.points.length === 0) return null
  return trendOption(series.value.points, ['scheduled', 'completed'])
})

const recent = computed(() => profile.value?.recent_appointments ?? [])
</script>

<template>
  <div>
    <div class="mb-3">
      <RouterLink to="/profissionais" class="btn btn-sm btn-ghost">
        <Icon name="chevron-left" :size="14" /> Profissionais
      </RouterLink>
    </div>

    <LoadingSkeleton v-if="loading && !profile" variant="chart" height="120px" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="profile">
      <PageHeader
        eyebrow="Perfil administrativo"
        :title="profile.professional.full_name"
        :description="`${profile.professional.specialty.name} · ${profile.professional.unit.name} · ${profile.professional.email}`"
      >
        <template #actions>
          <RouterLink
            :to="`/agenda?professional=${profile.professional.id}`"
            class="btn btn-sm"
          >
            <Icon name="calendar" :size="14" /> Ver agenda
          </RouterLink>
          <span class="badge badge--slate mono">{{ profile.professional.code }}</span>
        </template>
      </PageHeader>

      <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div class="kpi-card">
          <p class="kpi-label">Ocupação</p>
          <p class="kpi-value">{{ formatPercent(indicator?.occupancy_pct) }}</p>
          <div class="progress mt-2">
            <div class="progress-bar" :style="{ width: `${Math.min(100, indicator?.occupancy_pct ?? 0)}%` }" />
          </div>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Comparecimento</p>
          <p class="kpi-value">{{ formatPercent(indicator?.attendance_rate) }}</p>
          <p class="tiny subtle mt-2">{{ formatNumber(indicator?.completed) }} realizadas</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Taxa de faltas</p>
          <p class="kpi-value">{{ formatPercent(indicator?.no_show_rate) }}</p>
          <p class="tiny subtle mt-2">{{ formatNumber(indicator?.no_show) }} faltas</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Espera média</p>
          <p class="kpi-value">{{ formatSeconds(indicator?.wait_seconds_avg) }}</p>
          <p class="tiny subtle mt-2">chegada → início</p>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Receita simulada</p>
          <p class="kpi-value" style="font-size: 21px">{{ formatMoney(indicator?.revenue) }}</p>
          <p class="tiny subtle mt-2">atendimentos concluídos</p>
        </div>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-3">
        <section class="card xl:col-span-2">
          <header class="card-header">
            <div>
              <h2 class="card-title">Evolução semanal</h2>
              <p class="card-subtitle">Últimos 90 dias · agendadas e realizadas</p>
            </div>
          </header>
          <div class="card-body">
            <EChart
              v-if="chart"
              :option="chart"
              height="280px"
              :aria-label="`Evolução semanal de ${profile.professional.full_name}`"
            />
            <EmptyState v-else title="Sem histórico" description="Não há agendamentos no período." icon="chart" />
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Disponibilidade</h2>
              <p class="card-subtitle">Janelas semanais cadastradas</p>
            </div>
          </header>
          <div class="card-body">
            <div v-if="availability.length" class="flex flex-col gap-1.5">
              <div v-for="day in availability" :key="day.weekday" class="flex items-start justify-between gap-3 border-b py-1.5 last:border-0">
                <span class="text-[12px] font-medium">{{ WEEKDAY_LABELS[day.weekday] }}</span>
                <div class="flex flex-wrap justify-end gap-1">
                  <span v-for="window in day.windows" :key="`${window.start_time}-${window.end_time}`" class="badge badge--teal">
                    {{ window.start_time.slice(0, 5) }}–{{ window.end_time.slice(0, 5) }}
                  </span>
                </div>
              </div>
            </div>
            <p v-else class="tiny subtle">Nenhuma disponibilidade cadastrada.</p>
          </div>
        </section>
      </div>

      <section class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Consultas recentes</h2>
            <p class="card-subtitle">Últimos agendamentos registrados para este profissional</p>
          </div>
          <RouterLink to="/atendimentos" class="btn btn-sm btn-ghost">
            Ver atendimentos <Icon name="chevron-right" :size="13" />
          </RouterLink>
        </header>
        <div class="card-body pt-0">
          <div v-if="recent.length" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Paciente</th>
                  <th>Serviço</th>
                  <th>Unidade</th>
                  <th>Status</th>
                  <th class="num">Valor</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="appointment in recent" :key="appointment.id">
                  <td class="strong">
                    {{ formatDate(appointment.scheduled_start) }}
                    <p class="tiny subtle">{{ formatTime(appointment.scheduled_start) }}</p>
                  </td>
                  <td class="mono">{{ appointment.patient_ref }}</td>
                  <td>{{ appointment.service_type.name }}</td>
                  <td>{{ appointment.unit.name }}</td>
                  <td><StatusBadge :status="appointment.status" /></td>
                  <td class="num">{{ formatMoney(appointment.priced_amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="Sem consultas recentes" description="Este profissional ainda não possui agendamentos." icon="calendar" />
        </div>
      </section>

      <p class="tiny subtle mt-4">
        Última atualização dos dados: {{ formatDateTime(new Date().toISOString()) }} ·
        dados sintéticos para demonstração.
      </p>
    </template>
  </div>
</template>
