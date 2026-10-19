<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { errorMessage } from '@/api/client'
import { analyticsApi, kpiApi, qualityApi } from '@/api/endpoints'
import type {
  Breakdown,
  Granularity,
  OperationalSummary,
  Overview,
  QualitySummary,
  Timeseries,
} from '@/api/types'
import EChart from '@/components/EChart.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FilterBar from '@/components/FilterBar.vue'
import Icon from '@/components/Icon.vue'
import KpiCard from '@/components/KpiCard.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import TaskList from '@/components/TaskList.vue'
import { useDashboardFilters } from '@/composables/useDashboardFilters'
import { useMetaStore } from '@/stores/meta'
import { useThemeStore } from '@/stores/theme'
import {
  breakdownBarOption,
  donutOption,
  trendOption,
  type SeriesMetricKey,
} from '@/utils/charts'
import {
  ETL_STATUS,
  formatDateRange,
  formatNumber,
  formatPercent,
} from '@/utils/format'

const meta = useMetaStore()
const theme = useThemeStore()
const { filters } = useDashboardFilters(30)

const overview = ref<Overview | null>(null)
const series = ref<Timeseries | null>(null)
const weekday = ref<Breakdown | null>(null)
const statusDistribution = ref<Breakdown | null>(null)
const operational = ref<OperationalSummary | null>(null)
const quality = ref<QualitySummary | null>(null)

const loading = ref(false)
const seriesLoading = ref(false)
const error = ref<string | null>(null)
const granularity = ref<Granularity>('week')
const trendMetrics = ref<SeriesMetricKey[]>(['scheduled', 'completed', 'no_show'])

const METRIC_CHOICES: { key: SeriesMetricKey; label: string }[] = [
  { key: 'scheduled', label: 'Agendadas' },
  { key: 'completed', label: 'Realizadas' },
  { key: 'no_show', label: 'Faltas' },
  { key: 'cancelled', label: 'Canceladas' },
]

const GRANULARITIES: { value: Granularity; label: string }[] = [
  { value: 'day', label: 'Dia' },
  { value: 'week', label: 'Semana' },
  { value: 'month', label: 'Mês' },
]

let requestId = 0

async function load() {
  if (!filters.value.end) return
  const current = ++requestId
  loading.value = true
  error.value = null
  try {
    const [overviewData, seriesData, weekdayData, statusData, operationalData, qualityData] =
      await Promise.all([
        kpiApi.overview(filters.value),
        kpiApi.timeseries(filters.value, granularity.value),
        analyticsApi.breakdown(filters.value, 'weekday'),
        analyticsApi.breakdown(filters.value, 'status'),
        kpiApi.operational(),
        qualityApi.summary(),
      ])
    if (current !== requestId) return
    overview.value = overviewData
    series.value = seriesData
    weekday.value = weekdayData
    statusDistribution.value = statusData
    operational.value = operationalData
    quality.value = qualityData
  } catch (cause) {
    if (current === requestId) error.value = errorMessage(cause)
  } finally {
    if (current === requestId) loading.value = false
  }
}

async function reloadSeries() {
  if (!filters.value.end) return
  seriesLoading.value = true
  try {
    series.value = await kpiApi.timeseries(filters.value, granularity.value)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    seriesLoading.value = false
  }
}

watch(filters, () => void load(), { deep: true, immediate: true })
watch(granularity, () => void reloadSeries())

onMounted(() => {
  void meta.load()
})

const kpis = computed(() => overview.value?.kpis ?? [])
const kpiMap = computed(() =>
  Object.fromEntries(kpis.value.map((kpi) => [kpi.key, kpi])),
)

const counts = computed(() => operational.value?.counts ?? {})
const todayProgress = computed(() => {
  const total = counts.value.today_scheduled ?? 0
  const done = counts.value.today_confirmed ?? 0
  return total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0
})

const periodLabel = computed(() =>
  overview.value
    ? formatDateRange(overview.value.period.start, overview.value.period.end)
    : '—',
)

const trendChart = computed(() => {
  void theme.mode
  if (!series.value || series.value.points.length === 0) return null
  return trendOption(series.value.points, trendMetrics.value)
})

const weekdayChart = computed(() => {
  void theme.mode
  const items = (weekday.value?.items ?? []).filter((item) => item.scheduled > 0)
  return items.length ? breakdownBarOption(items, 'occupancy_pct') : null
})

const statusChart = computed(() => {
  void theme.mode
  const items = (statusDistribution.value?.items ?? []).filter((item) => item.scheduled > 0)
  return items.length ? donutOption(items) : null
})

const isEmpty = computed(
  () => Boolean(overview.value) && (kpiMap.value.scheduled?.value ?? 0) === 0,
)

const qualityStatus = computed(() => {
  const run = quality.value?.last_run
  return run ? ETL_STATUS[run.status] : null
})

function toggleMetric(key: SeriesMetricKey) {
  if (trendMetrics.value.includes(key)) {
    if (trendMetrics.value.length === 1) return
    trendMetrics.value = trendMetrics.value.filter((metric) => metric !== key)
  } else {
    trendMetrics.value = [...trendMetrics.value, key]
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Dashboard executivo"
      title="Visão geral"
      description="Indicadores de agenda, comparecimento, ocupação e receita simulada da clínica. Compare com o período anterior e priorize pendências operacionais."
    >
      <template #actions>
        <span class="badge badge--amber">
          <Icon name="sparkles" :size="12" /> Dados sintéticos
        </span>
        <RouterLink to="/agenda" class="btn btn-sm">
          <Icon name="calendar" :size="14" /> Agenda de hoje
        </RouterLink>
        <button type="button" class="btn btn-sm btn-icon" aria-label="Atualizar dados" @click="load">
          <Icon name="refresh" :size="15" />
        </button>
      </template>
    </PageHeader>

    <FilterBar v-model="filters" :options="meta.options" />

    <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
      <p class="tiny subtle">
        Período: <strong>{{ periodLabel }}</strong>
        <span v-if="overview">
          · comparado a
          {{ formatDateRange(overview.previous_period.start, overview.previous_period.end) }}
        </span>
      </p>
      <p v-if="overview" class="tiny subtle">
        Gerado em {{ new Date(overview.generated_at).toLocaleString('pt-BR') }}
      </p>
    </div>

    <ErrorState
      v-if="error && !overview"
      class="mt-4"
      :message="error"
      @retry="load"
    />

    <template v-else>
      <div v-if="loading && !overview" class="kpi-grid mt-4">
        <LoadingSkeleton v-for="index in 8" :key="index" />
      </div>

      <div v-else-if="isEmpty" class="mt-4">
        <EmptyState
          title="Nenhum dado no período selecionado"
          description="Ajuste o período ou execute o pipeline para gerar o conjunto sintético."
          icon="database"
        >
          <template #action>
            <RouterLink to="/qualidade" class="btn btn-sm mt-2">
              Ver qualidade dos dados
            </RouterLink>
          </template>
        </EmptyState>
      </div>

      <template v-else-if="kpis.length">
        <section class="kpi-grid mt-4" aria-label="Indicadores do período">
          <KpiCard v-for="kpi in kpis" :key="kpi.key" :kpi="kpi" />
        </section>

        <div class="mt-4 grid gap-4 xl:grid-cols-3">
          <section class="card xl:col-span-2">
            <header class="card-header">
              <div>
                <h2 class="card-title">Evolução dos atendimentos</h2>
                <p class="card-subtitle">
                  Série agregada por {{ granularity === 'day' ? 'dia' : granularity === 'week' ? 'semana' : 'mês' }}.
                  Passe o cursor para ver os valores.
                </p>
              </div>
              <div class="preset-group" role="group" aria-label="Granularidade da série">
                <button
                  v-for="option in GRANULARITIES"
                  :key="option.value"
                  type="button"
                  class="preset-btn"
                  :class="{ 'is-active': granularity === option.value }"
                  @click="granularity = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </header>
            <div class="card-body">
              <div class="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Séries exibidas">
                <button
                  v-for="choice in METRIC_CHOICES"
                  :key="choice.key"
                  type="button"
                  class="btn btn-sm"
                  :class="{ 'btn-primary': trendMetrics.includes(choice.key) }"
                  :aria-pressed="trendMetrics.includes(choice.key)"
                  @click="toggleMetric(choice.key)"
                >
                  {{ choice.label }}
                </button>
                <span v-if="seriesLoading" class="ml-1 inline-flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
                  <span class="h-3 w-3 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
                  atualizando…
                </span>
              </div>
              <EChart
                v-if="trendChart"
                :option="trendChart"
                height="310px"
                aria-label="Gráfico de evolução de consultas agendadas, realizadas e faltas"
              />
              <EmptyState
                v-else
                title="Sem série no período"
                description="Não há agendamentos para os filtros selecionados."
                icon="chart"
              />
            </div>
          </section>

          <section class="card">
            <header class="card-header">
              <div>
                <h2 class="card-title">Operação de hoje</h2>
                <p class="card-subtitle">Data de referência da demonstração</p>
              </div>
              <span class="badge badge--teal">{{ formatNumber(counts.today_scheduled ?? 0) }} agendadas</span>
            </header>
            <div class="card-body">
              <div class="flex items-end justify-between">
                <div>
                  <p class="text-[28px] font-bold leading-none tracking-[-0.04em]">
                    {{ formatPercent(todayProgress, 0) }}
                  </p>
                  <p class="mt-1 tiny subtle">
                    {{ formatNumber(counts.today_confirmed ?? 0) }} confirmadas/concluídas de
                    {{ formatNumber(counts.today_scheduled ?? 0) }}
                  </p>
                </div>
                <span class="badge" :class="todayProgress >= 85 ? 'badge--green' : todayProgress >= 60 ? 'badge--amber' : 'badge--red'">
                  {{ todayProgress >= 85 ? 'No ritmo' : todayProgress >= 60 ? 'Atenção' : 'Crítico' }}
                </span>
              </div>
              <div class="progress mt-3">
                <div
                  class="progress-bar"
                  :class="{ 'progress-bar--warn': todayProgress < 85, 'progress-bar--danger': todayProgress < 60 }"
                  :style="{ width: `${todayProgress}%` }"
                />
              </div>

              <div class="mt-4 grid grid-cols-2 gap-2">
                <div class="note-box">
                  <div>
                    <p class="text-[18px] font-bold leading-none">{{ formatNumber(counts.today_completed ?? 0) }}</p>
                    <p class="tiny subtle mt-1">concluídas hoje</p>
                  </div>
                </div>
                <div class="note-box">
                  <div>
                    <p class="text-[18px] font-bold leading-none">{{ formatNumber(counts.pending_confirmation_48h ?? 0) }}</p>
                    <p class="tiny subtle mt-1">sem confirmação (48h)</p>
                  </div>
                </div>
                <div class="note-box">
                  <div>
                    <p class="text-[18px] font-bold leading-none">{{ formatNumber(counts.late_today ?? 0) }}</p>
                    <p class="tiny subtle mt-1">atrasadas hoje</p>
                  </div>
                </div>
                <div class="note-box">
                  <div>
                    <p class="text-[18px] font-bold leading-none">{{ formatNumber(counts.last7_no_show ?? 0) }}</p>
                    <p class="tiny subtle mt-1">faltas em 7 dias</p>
                  </div>
                </div>
              </div>

              <div class="mt-4 border-t pt-3">
                <div class="mb-2 flex items-center justify-between">
                  <p class="text-[12px] font-semibold">Prioridades</p>
                  <RouterLink to="/agenda" class="text-[11.5px] font-semibold hover:underline">
                    Ver agenda
                  </RouterLink>
                </div>
                <TaskList :tasks="operational?.tasks ?? []" :limit="2" />
              </div>
            </div>
          </section>
        </div>

        <div class="mt-4 grid gap-4 lg:grid-cols-2">
          <section class="card">
            <header class="card-header">
              <div>
                <h2 class="card-title">Ocupação por dia da semana</h2>
                <p class="card-subtitle">
                  Minutos reservados ÷ minutos disponíveis. Ajuda a identificar dias ociosos.
                </p>
              </div>
              <RouterLink to="/analytics?dimension=weekday" class="btn btn-sm btn-ghost">
                Detalhar <Icon name="chevron-right" :size="13" />
              </RouterLink>
            </header>
            <div class="card-body">
              <EChart
                v-if="weekdayChart"
                :option="weekdayChart"
                height="290px"
                aria-label="Gráfico de ocupação da agenda por dia da semana"
              />
              <EmptyState v-else title="Sem ocupação calculada" description="Não há disponibilidade cadastrada no período." icon="calendar" />
            </div>
          </section>

          <section class="card">
            <header class="card-header">
              <div>
                <h2 class="card-title">Distribuição dos agendamentos</h2>
                <p class="card-subtitle">Todos os status do período, inclusive cancelamentos e faltas.</p>
              </div>
            </header>
            <div class="card-body">
              <EChart
                v-if="statusChart"
                :option="statusChart"
                height="290px"
                aria-label="Gráfico de distribuição dos agendamentos por status"
              />
              <EmptyState v-else title="Sem agendamentos" description="Ajuste os filtros para visualizar a distribuição." icon="chart" />
            </div>
          </section>
        </div>

        <div class="mt-4 grid gap-4 xl:grid-cols-3">
          <section class="card xl:col-span-2">
            <header class="card-header">
              <div>
                <h2 class="card-title">Fila de trabalho priorizada</h2>
                <p class="card-subtitle">
                  Cada tarefa declara a regra que a gerou e o prazo sugerido.
                </p>
              </div>
              <span class="badge badge--slate">
                {{ formatNumber(operational?.tasks.length ?? 0) }} pendências
              </span>
            </header>
            <div class="card-body">
              <TaskList :tasks="operational?.tasks ?? []" :limit="5" />
            </div>
          </section>

          <section class="card">
            <header class="card-header">
              <div>
                <h2 class="card-title">Qualidade dos dados</h2>
                <p class="card-subtitle">Última execução do pipeline</p>
              </div>
              <StatusBadge
                v-if="qualityStatus && quality?.last_run"
                :label="qualityStatus.label"
                :tone="qualityStatus.tone"
              />
            </header>
            <div class="card-body">
              <template v-if="quality?.last_run">
                <p class="mono text-[11px] subtle">{{ quality.last_run.run_id }}</p>
                <dl class="mt-3 grid grid-cols-2 gap-2 text-[12px]">
                  <div class="note-box flex-col">
                    <dt class="tiny subtle">Linhas lidas</dt>
                    <dd class="text-[17px] font-bold">{{ formatNumber(quality.total_rows_read) }}</dd>
                  </div>
                  <div class="note-box flex-col">
                    <dt class="tiny subtle">Rejeitadas</dt>
                    <dd class="text-[17px] font-bold text-[var(--danger)]">
                      {{ formatNumber(quality.total_rows_rejected) }}
                    </dd>
                  </div>
                </dl>
                <p class="mt-2 tiny subtle">
                  {{ formatPercent(quality.rejected_pct, 3) }} dos registros lidos foram rejeitados
                  pelas regras de qualidade.
                </p>
                <div class="mt-3 flex flex-wrap gap-1.5">
                  <span
                    v-for="item in quality.issues_by_type.slice(0, 3)"
                    :key="item.key"
                    class="badge badge--slate"
                  >
                    {{ item.key }} · {{ item.count }}
                  </span>
                </div>
                <RouterLink to="/qualidade" class="btn btn-sm mt-4 w-full">
                  Abrir monitor de qualidade <Icon name="chevron-right" :size="13" />
                </RouterLink>
              </template>
              <EmptyState
                v-else
                title="Pipeline ainda não executou"
                description="Rode o pipeline para carregar o conjunto sintético."
                icon="database"
              />
            </div>
          </section>
        </div>

        <div class="note-box note-box--warn mt-4">
          <Icon name="info" :size="16" class="mt-0.5" />
          <p>
            Receitas, valores e pacientes são simulados. Os indicadores demonstram engenharia de
            dados e não representam resultados clínicos ou financeiros reais. Fórmulas completas
            estão em <RouterLink to="/analytics" class="font-semibold underline">Analytics</RouterLink>
            e em <span class="mono">docs/metrics.md</span>.
          </p>
        </div>
      </template>
    </template>
  </div>
</template>
