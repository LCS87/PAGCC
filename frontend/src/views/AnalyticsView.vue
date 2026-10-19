<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '@/api/client'
import { analyticsApi, kpiApi } from '@/api/endpoints'
import type {
  Breakdown,
  BreakdownDimension,
  Granularity,
  Overview,
  Timeseries,
} from '@/api/types'
import EChart from '@/components/EChart.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FilterBar from '@/components/FilterBar.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDashboardFilters } from '@/composables/useDashboardFilters'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import { useThemeStore } from '@/stores/theme'
import {
  breakdownBarOption,
  trendOption,
  type BreakdownMetricKey,
  type SeriesMetricKey,
} from '@/utils/charts'
import {
  formatByUnit,
  formatDelta,
  formatMoney,
  formatNumber,
  formatPercent,
} from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const meta = useMetaStore()
const theme = useThemeStore()
const { filters } = useDashboardFilters(90)

const DIMENSIONS: { key: BreakdownDimension; label: string }[] = [
  { key: 'specialty', label: 'Especialidade' },
  { key: 'professional', label: 'Profissional' },
  { key: 'unit', label: 'Unidade' },
  { key: 'weekday', label: 'Dia da semana' },
  { key: 'hour', label: 'Hora' },
  { key: 'status', label: 'Status' },
  { key: 'source', label: 'Origem' },
]

const LINE_METRICS: { key: SeriesMetricKey; label: string }[] = [
  { key: 'scheduled', label: 'Agendadas' },
  { key: 'completed', label: 'Realizadas' },
  { key: 'no_show', label: 'Faltas' },
  { key: 'cancelled', label: 'Canceladas' },
  { key: 'occupancy_pct', label: 'Ocupação' },
  { key: 'revenue', label: 'Receita' },
  { key: 'wait_seconds_avg', label: 'Espera' },
]

const BREAKDOWN_METRICS: { key: BreakdownMetricKey; label: string }[] = [
  { key: 'scheduled', label: 'Agendadas' },
  { key: 'completed', label: 'Realizadas' },
  { key: 'no_show', label: 'Faltas' },
  { key: 'occupancy_pct', label: 'Ocupação' },
  { key: 'revenue', label: 'Receita' },
]

const initialDimension = DIMENSIONS.find((item) => item.key === route.query.dimension)
const dimension = ref<BreakdownDimension>(initialDimension?.key ?? 'specialty')
const granularity = ref<Granularity>('week')
const metric = ref<SeriesMetricKey>('scheduled')
const breakdownMetric = ref<BreakdownMetricKey>('scheduled')

const series = ref<Timeseries | null>(null)
const breakdown = ref<Breakdown | null>(null)
const overview = ref<Overview | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const exporting = ref(false)
const exportMessage = ref('')
const exportError = ref('')

const canExport = computed(() =>
  auth.hasRole('ADMIN', 'GESTOR', 'COORDENADOR', 'ANALISTA'),
)

async function load() {
  if (!filters.value.end) return
  loading.value = true
  error.value = null
  try {
    const [seriesData, breakdownData, overviewData] = await Promise.all([
      analyticsApi.timeseries(filters.value, granularity.value),
      analyticsApi.breakdown(filters.value, dimension.value),
      kpiApi.overview(filters.value),
    ])
    series.value = seriesData
    breakdown.value = breakdownData
    overview.value = overviewData
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

watch(filters, () => void load(), { deep: true, immediate: true })
watch([granularity, dimension], () => void load())

watch(dimension, (value) => {
  if (route.query.dimension !== value) {
    void router.replace({ query: { ...route.query, dimension: value } })
  }
  if (dimension.value === 'status' || dimension.value === 'source') {
    breakdownMetric.value = 'scheduled'
  }
})

onMounted(() => void meta.load())

const lineChart = computed(() => {
  void theme.mode
  if (!series.value || series.value.points.length === 0) return null
  return trendOption(series.value.points, [metric.value])
})

const barChart = computed(() => {
  void theme.mode
  const items = (breakdown.value?.items ?? []).filter((item) => item.scheduled > 0 || item.completed > 0)
  return items.length ? breakdownBarOption(items, breakdownMetric.value) : null
})

const availableBreakdownMetrics = computed(() => {
  if (dimension.value === 'status' || dimension.value === 'source') {
    return BREAKDOWN_METRICS.filter((item) => item.key === 'scheduled')
  }
  return BREAKDOWN_METRICS
})

const dimensionLabel = computed(
  () => DIMENSIONS.find((item) => item.key === dimension.value)?.label ?? dimension.value,
)

const hasData = computed(
  () => (series.value?.points.length ?? 0) > 0 || (breakdown.value?.items.length ?? 0) > 0,
)

async function downloadCsv() {
  if (!canExport.value) return
  exporting.value = true
  exportMessage.value = ''
  exportError.value = ''
  try {
    const blob = await analyticsApi.exportCsv(filters.value)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `agendamentos_${filters.value.start}_${filters.value.end}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    exportMessage.value = 'Exportação gerada com sucesso.'
  } catch (cause) {
    exportError.value = errorMessage(cause)
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Engenharia e análise de dados"
      title="Analytics"
      description="Séries temporais, comparação de períodos, segmentações e exportação. As fórmulas de cada métrica estão documentadas abaixo."
    >
      <template #actions>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!canExport || exporting"
          :title="canExport ? 'Exportar CSV do período' : 'Seu perfil não pode exportar dados'"
          @click="downloadCsv"
        >
          <Icon name="download" :size="14" />
          {{ exporting ? 'Gerando…' : 'Exportar CSV' }}
        </button>
      </template>
    </PageHeader>

    <FilterBar v-model="filters" :options="meta.options" />

    <div v-if="exportMessage" class="note-box mt-3" role="status">
      <Icon name="check" :size="16" /> {{ exportMessage }}
    </div>
    <div v-if="exportError" class="error-banner mt-3" role="alert">
      <Icon name="alert" :size="16" /> {{ exportError }}
    </div>

    <ErrorState v-if="error" class="mt-4" :message="error" @retry="load" />

    <div v-else-if="loading && !series" class="mt-4 flex flex-col gap-3">
      <LoadingSkeleton variant="chart" height="320px" />
      <LoadingSkeleton variant="table" :rows="5" />
    </div>

    <EmptyState
      v-else-if="!hasData"
      class="mt-4"
      title="Sem dados para analisar"
      description="Ajuste o período ou os filtros para encontrar agendamentos."
      icon="chart"
    />

    <template v-else>
      <section class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Série temporal</h2>
            <p class="card-subtitle">Agregação por {{ granularity === 'day' ? 'dia' : granularity === 'week' ? 'semana' : 'mês' }}</p>
          </div>
          <div class="preset-group" role="group" aria-label="Granularidade">
            <button
              v-for="option in (['day', 'week', 'month'] as Granularity[])"
              :key="option"
              type="button"
              class="preset-btn"
              :class="{ 'is-active': granularity === option }"
              @click="granularity = option"
            >
              {{ option === 'day' ? 'Dia' : option === 'week' ? 'Semana' : 'Mês' }}
            </button>
          </div>
        </header>
        <div class="card-body">
          <div class="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Métrica da série">
            <button
              v-for="choice in LINE_METRICS"
              :key="choice.key"
              type="button"
              class="btn btn-sm"
              :class="{ 'btn-primary': metric === choice.key }"
              :aria-pressed="metric === choice.key"
              @click="metric = choice.key"
            >
              {{ choice.label }}
            </button>
          </div>
          <EChart v-if="lineChart" :option="lineChart" height="320px" aria-label="Série temporal da métrica selecionada" />
        </div>
      </section>

      <section class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Segmentação por {{ dimensionLabel.toLowerCase() }}</h2>
            <p class="card-subtitle">Compare volume, ocupação e receita entre categorias</p>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="item in availableBreakdownMetrics"
              :key="item.key"
              type="button"
              class="btn btn-sm"
              :class="{ 'btn-primary': breakdownMetric === item.key }"
              @click="breakdownMetric = item.key"
            >
              {{ item.label }}
            </button>
          </div>
        </header>
        <div class="card-body">
          <div class="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Dimensão da segmentação">
            <button
              v-for="item in DIMENSIONS"
              :key="item.key"
              type="button"
              class="preset-btn"
              :class="{ 'is-active': dimension === item.key }"
              @click="dimension = item.key"
            >
              {{ item.label }}
            </button>
          </div>

          <EChart v-if="barChart" :option="barChart" height="330px" :aria-label="`Segmentação por ${dimensionLabel}`" />

          <div v-if="breakdown?.items.length" class="table-wrap mt-4">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ dimensionLabel }}</th>
                  <th class="num">Agendadas</th>
                  <th class="num">Realizadas</th>
                  <th class="num">Faltas</th>
                  <th class="num">Ocupação</th>
                  <th class="num">Receita</th>
                  <th class="num">Participação</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in breakdown.items" :key="item.key">
                  <td class="strong">{{ item.label }}</td>
                  <td class="num">{{ formatNumber(item.scheduled) }}</td>
                  <td class="num">{{ formatNumber(item.completed) }}</td>
                  <td class="num">{{ formatNumber(item.no_show) }}</td>
                  <td class="num">{{ formatPercent(item.occupancy_pct) }}</td>
                  <td class="num">{{ formatMoney(item.revenue) }}</td>
                  <td class="num">{{ formatPercent(item.share_pct) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="Sem categorias" description="Não há registros para esta dimensão no período." icon="chart" />
        </div>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-2">
        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Comparação com o período anterior</h2>
              <p class="card-subtitle">Variação relativa calculada pela API</p>
            </div>
          </header>
          <div class="card-body">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Métrica</th>
                    <th class="num">Atual</th>
                    <th class="num">Anterior</th>
                    <th class="num">Variação</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="kpi in overview?.kpis ?? []" :key="kpi.key">
                    <td class="strong">{{ kpi.label }}</td>
                    <td class="num">{{ formatByUnit(kpi.value, kpi.unit) }}</td>
                    <td class="num">{{ formatByUnit(kpi.previous, kpi.unit) }}</td>
                    <td class="num" :class="kpi.delta_pct !== null && kpi.delta_pct < 0 ? 'text-[var(--danger)]' : ''">
                      {{ formatDelta(kpi.delta_pct) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Definições das métricas</h2>
              <p class="card-subtitle">Fórmulas e denominadores usados pela API</p>
            </div>
          </header>
          <div class="card-body flex flex-col gap-2">
            <details v-for="kpi in overview?.kpis ?? []" :key="kpi.key" class="rounded-lg border p-2.5">
              <summary class="cursor-pointer text-[12.5px] font-semibold">{{ kpi.label }}</summary>
              <p class="mt-1.5 text-[12px] leading-relaxed text-[var(--muted)]">{{ kpi.formula }}</p>
              <p v-if="kpi.denominator !== null" class="tiny subtle mt-1">
                Base de cálculo: {{ formatNumber(kpi.denominator) }}
              </p>
            </details>
          </div>
        </section>
      </div>

      <div class="note-box mt-4">
        <Icon name="info" :size="16" class="mt-0.5" />
        <p>
          Exportação disponível para perfis ADMIN, GESTOR, COORDENADOR e ANALISTA. O arquivo CSV
          usa separador “;” e BOM UTF-8 para abrir corretamente no Excel. Todos os registros são
          sintéticos.
        </p>
      </div>
    </template>
  </div>
</template>
