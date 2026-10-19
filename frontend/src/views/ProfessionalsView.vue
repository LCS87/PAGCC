<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { errorMessage } from '@/api/client'
import { professionalApi } from '@/api/endpoints'
import type { ProfessionalIndicator } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FilterBar from '@/components/FilterBar.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useDashboardFilters } from '@/composables/useDashboardFilters'
import { useMetaStore } from '@/stores/meta'
import { formatMoney, formatNumber, formatPercent, formatSeconds } from '@/utils/format'

const meta = useMetaStore()
const { filters } = useDashboardFilters(30)
const indicators = ref<ProfessionalIndicator[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function load() {
  if (!filters.value.end) return
  loading.value = true
  error.value = null
  try {
    indicators.value = await professionalApi.indicators(filters.value)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

watch(filters, () => void load(), { deep: true, immediate: true })
onMounted(() => void meta.load())

const totals = computed(() => {
  const scheduled = indicators.value.reduce((sum, item) => sum + item.scheduled, 0)
  const completed = indicators.value.reduce((sum, item) => sum + item.completed, 0)
  const revenue = indicators.value.reduce((sum, item) => sum + item.revenue, 0)
  const withOccupancy = indicators.value.filter((item) => item.occupancy_pct !== null)
  const occupancy =
    withOccupancy.length > 0
      ? withOccupancy.reduce((sum, item) => sum + (item.occupancy_pct ?? 0), 0) /
        withOccupancy.length
      : null
  return { scheduled, completed, revenue, occupancy }
})

function occupancyTone(value: number | null): string {
  if (value === null) return 'badge--slate'
  if (value >= 75) return 'badge--green'
  if (value >= 50) return 'badge--amber'
  return 'badge--red'
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Gestão"
      title="Profissionais e unidades"
      description="Ocupação, comparecimento, faltas e receita simulada por profissional. Os indicadores respeitam o período e os filtros selecionados."
    >
      <template #actions>
        <span class="badge badge--teal">{{ indicators.length }} profissionais</span>
      </template>
    </PageHeader>

    <FilterBar v-model="filters" :options="meta.options" />

    <ErrorState v-if="error" class="mt-4" :message="error" @retry="load" />

    <div v-else-if="loading && indicators.length === 0" class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <LoadingSkeleton v-for="index in 6" :key="index" />
    </div>

    <template v-else-if="indicators.length">
      <section class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="card p-4">
          <p class="tiny subtle">Consultas agendadas</p>
          <p class="text-[22px] font-bold leading-tight">{{ formatNumber(totals.scheduled) }}</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Realizadas</p>
          <p class="text-[22px] font-bold leading-tight">{{ formatNumber(totals.completed) }}</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Ocupação média</p>
          <p class="text-[22px] font-bold leading-tight">{{ formatPercent(totals.occupancy) }}</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Receita simulada</p>
          <p class="text-[22px] font-bold leading-tight">{{ formatMoney(totals.revenue) }}</p>
        </div>
      </section>

      <section class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="item in indicators" :key="item.professional.id" class="card p-4">
          <div class="flex items-start gap-3">
            <span class="avatar">{{ item.professional.full_name.split(' ').slice(-2).map((part) => part[0]).join('') }}</span>
            <div class="min-w-0 flex-1">
              <RouterLink :to="`/profissionais/${item.professional.id}`" class="text-[13.5px] font-semibold hover:underline">
                {{ item.professional.full_name }}
              </RouterLink>
              <p class="tiny subtle">
                {{ item.professional.specialty.name }} · {{ item.professional.unit.name }}
              </p>
            </div>
            <span class="badge" :class="occupancyTone(item.occupancy_pct)">
              {{ formatPercent(item.occupancy_pct) }}
            </span>
          </div>

          <div class="mt-3">
            <div class="progress">
              <div class="progress-bar" :style="{ width: `${Math.min(100, item.occupancy_pct ?? 0)}%` }" />
            </div>
            <p class="tiny subtle mt-1.5">ocupação da agenda no período</p>
          </div>

          <dl class="mt-3 grid grid-cols-2 gap-2 text-[12px]">
            <div>
              <dt class="tiny subtle">Comparecimento</dt>
              <dd class="font-semibold">{{ formatPercent(item.attendance_rate) }}</dd>
            </div>
            <div>
              <dt class="tiny subtle">Faltas</dt>
              <dd class="font-semibold">{{ formatPercent(item.no_show_rate) }}</dd>
            </div>
            <div>
              <dt class="tiny subtle">Realizadas</dt>
              <dd class="font-semibold">{{ formatNumber(item.completed) }} / {{ formatNumber(item.scheduled) }}</dd>
            </div>
            <div>
              <dt class="tiny subtle">Espera média</dt>
              <dd class="font-semibold">{{ formatSeconds(item.wait_seconds_avg) }}</dd>
            </div>
            <div class="col-span-2">
              <dt class="tiny subtle">Receita simulada</dt>
              <dd class="font-semibold">{{ formatMoney(item.revenue) }}</dd>
            </div>
          </dl>

          <RouterLink :to="`/profissionais/${item.professional.id}`" class="btn btn-sm mt-3 w-full">
            Ver perfil e agenda <Icon name="chevron-right" :size="13" />
          </RouterLink>
        </article>
      </section>

      <div class="note-box mt-4">
        <Icon name="info" :size="16" class="mt-0.5" />
        <p>
          A ocupação compara minutos reservados com a disponibilidade semanal cadastrada.
          Profissionais sem disponibilidade no período aparecem com “—”. As datas seguem o fuso
          {{ meta.timezone }}.
        </p>
      </div>
    </template>

    <EmptyState
      v-else-if="!loading"
      class="mt-4"
      title="Nenhum indicador no período"
      description="Ajuste o período ou os filtros de unidade e especialidade."
      icon="users"
    />
  </div>
</template>
