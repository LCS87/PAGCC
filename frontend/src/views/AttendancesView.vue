<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { errorMessage } from '@/api/client'
import { attendanceApi } from '@/api/endpoints'
import type { AttendanceListItem } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useDashboardFilters } from '@/composables/useDashboardFilters'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import {
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  formatSeconds,
  formatTime,
} from '@/utils/format'

const meta = useMetaStore()
const auth = useAuthStore()
const route = useRoute()
const { filters } = useDashboardFilters(30)
const items = ref<AttendanceListItem[]>([])
const total = ref(0)
const pages = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref(typeof route.query.search === 'string' ? route.query.search : '')
const loading = ref(false)
const error = ref<string | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | undefined

async function load() {
  if (!filters.value.end) return
  loading.value = true
  error.value = null
  try {
    const response = await attendanceApi.list({
      ...filters.value,
      search: search.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = response.items
    total.value = response.total
    pages.value = response.pages
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  page.value = 1
  void load()
}, { deep: true })
watch(page, () => void load())

watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 380)
})

onMounted(() => {
  void meta.load()
  void load()
})

function clearSearch() {
  search.value = ''
}

function attendanceTone(status: AttendanceListItem['status']): 'green' | 'amber' {
  return status === 'CONCLUIDO' ? 'green' : 'amber'
}

function attendanceLabel(status: AttendanceListItem['status']): string {
  return status === 'CONCLUIDO' ? 'Concluído' : 'Em andamento'
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Gestão"
      title="Atendimentos"
      description="Atendimentos administrativos concluídos, com espera, valores simulados e vínculo com o agendamento. Nenhum dado clínico é armazenado."
    >
      <template #actions>
        <span class="badge badge--slate">{{ formatNumber(total) }} registros</span>
        <button type="button" class="btn btn-sm" @click="load">
          <Icon name="refresh" :size="14" /> Atualizar
        </button>
      </template>
    </PageHeader>

    <section class="filter-bar" aria-label="Filtros de atendimentos">
      <label class="field">
        <span class="label">Período</span>
        <input v-model="filters.start" class="input" type="date" :max="filters.end" />
      </label>
      <label class="field">
        <span class="label">Até</span>
        <input v-model="filters.end" class="input" type="date" :min="filters.start" />
      </label>
      <label class="field">
        <span class="label">Unidade</span>
        <select v-model.number="filters.unit_id" class="select">
          <option :value="null">Todas</option>
          <option v-for="unit in meta.options?.units ?? []" :key="unit.id" :value="unit.id">{{ unit.name }}</option>
        </select>
      </label>
      <label class="field">
        <span class="label">Profissional</span>
        <select
          v-model.number="filters.professional_id"
          class="select"
          :disabled="auth.user?.role === 'PROFISSIONAL'"
        >
          <option :value="null">Todos</option>
          <option v-for="professional in meta.options?.professionals ?? []" :key="professional.id" :value="professional.id">{{ professional.full_name }}</option>
        </select>
      </label>
      <label class="field" style="min-width: 230px">
        <span class="label">Paciente ou atendimento</span>
        <div class="flex gap-1">
          <input v-model="search" class="input" type="search" placeholder="PAC-0001 ou ATT-…" />
          <button v-if="search" type="button" class="btn btn-sm btn-icon" aria-label="Limpar busca" @click="clearSearch">
            <Icon name="close" :size="14" />
          </button>
        </div>
      </label>
    </section>

    <ErrorState v-if="error" class="mt-4" :message="error" @retry="load" />

    <template v-else>
      <div v-if="loading && items.length === 0" class="mt-4">
        <LoadingSkeleton variant="table" :rows="6" />
      </div>

      <div v-else-if="items.length === 0" class="mt-4">
        <EmptyState title="Nenhum atendimento encontrado" description="Ajuste o período, o profissional ou a busca." icon="clipboard" />
      </div>

      <template v-else>
        <div class="table-wrap mt-4">
          <table class="data-table">
            <thead>
              <tr>
                <th>Atendimento</th>
                <th>Paciente</th>
                <th>Profissional</th>
                <th>Unidade</th>
                <th>Chegada</th>
                <th>Espera</th>
                <th>Status</th>
                <th class="num">Cobrado</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.id">
                <td>
                  <RouterLink :to="`/atendimentos/${item.id}`" class="table-link">
                    {{ formatDate(item.scheduled_start) }}
                  </RouterLink>
                  <p class="tiny subtle mono">{{ item.external_id }}</p>
                </td>
                <td class="mono">{{ item.patient_ref }}</td>
                <td>
                  {{ item.professional_name }}
                  <p class="tiny subtle">{{ item.specialty_name }}</p>
                </td>
                <td>{{ item.unit_name }}</td>
                <td>{{ formatTime(item.arrived_at) }}</td>
                <td>{{ formatSeconds(item.wait_seconds) }}</td>
                <td>
                  <StatusBadge :label="attendanceLabel(item.status)" :tone="attendanceTone(item.status)" />
                </td>
                <td class="num">{{ formatMoney(item.amount_charged) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <PaginationBar
          :page="page"
          :pages="pages"
          :total="total"
          :page-size="pageSize"
          @update:page="page = $event"
        />
        <p class="tiny subtle">
          Início registrado em {{ formatDateTime(items[0]?.started_at) }} no fuso
          {{ meta.timezone }}.
        </p>
      </template>
    </template>
  </div>
</template>
