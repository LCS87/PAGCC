<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { errorMessage } from '@/api/client'
import { qualityApi } from '@/api/endpoints'
import type { EtlRun, QualityIssuePage, QualitySummary } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useMetaStore } from '@/stores/meta'
import {
  ETL_STATUS,
  QUALITY_SEVERITY,
  entityLabel,
  formatDateTime,
  formatNumber,
  formatPercent,
  issueTypeLabel,
} from '@/utils/format'

const meta = useMetaStore()
const summary = ref<QualitySummary | null>(null)
const issues = ref<QualityIssuePage | null>(null)
const runs = ref<EtlRun[]>([])
const severity = ref<'ERROR' | 'WARNING' | ''>('')
const entity = ref('')
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const error = ref<string | null>(null)

const entities = [
  'appointments',
  'attendances',
  'payments',
  'status_history',
  'availability',
  'professionals',
  'units',
  'specialties',
]

async function loadIssues() {
  loading.value = true
  error.value = null
  try {
    issues.value = await qualityApi.issues({
      page: page.value,
      page_size: pageSize,
      severity: severity.value || null,
      entity: entity.value || null,
    })
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  loading.value = true
  error.value = null
  try {
    const [summaryData, runsData] = await Promise.all([
      qualityApi.summary(),
      qualityApi.runs(),
    ])
    summary.value = summaryData
    runs.value = runsData
    await loadIssues()
  } catch (cause) {
    error.value = errorMessage(cause)
    loading.value = false
  }
}

watch([severity, entity], () => {
  page.value = 1
  void loadIssues()
})
watch(page, () => void loadIssues())

onMounted(() => {
  void meta.load()
  void loadAll()
})

const lastRun = computed(() => summary.value?.last_run ?? null)
const lastStatus = computed(() => (lastRun.value ? ETL_STATUS[lastRun.value.status] : null))
const errors = computed(() => summary.value?.issues_by_severity.ERROR ?? 0)
const warnings = computed(() => summary.value?.issues_by_severity.WARNING ?? 0)
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Operação"
      title="Qualidade dos dados"
      description="Resultado da última execução do pipeline, registros rejeitados e avisos. Cada problema aponta a entidade, o tipo e a referência do registro."
    >
      <template #actions>
        <StatusBadge
          v-if="lastStatus"
          :label="`Última carga: ${lastStatus.label}`"
          :tone="lastStatus.tone"
        />
        <button type="button" class="btn btn-sm" @click="loadAll">
          <Icon name="refresh" :size="14" /> Atualizar
        </button>
      </template>
    </PageHeader>

    <ErrorState v-if="error" class="mt-4" :message="error" @retry="loadAll" />

    <div v-else-if="loading && !summary" class="mt-4 flex flex-col gap-3">
      <LoadingSkeleton variant="chart" height="120px" />
      <LoadingSkeleton variant="table" :rows="6" />
    </div>

    <template v-else-if="summary">
      <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="card p-4">
          <p class="tiny subtle">Execuções registradas</p>
          <p class="text-[23px] font-bold">{{ formatNumber(summary.total_runs) }}</p>
          <p class="tiny subtle mt-1">histórico rastreável em etl_run</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Linhas lidas</p>
          <p class="text-[23px] font-bold">{{ formatNumber(summary.total_rows_read) }}</p>
          <p class="tiny subtle mt-1">dimensões + fatos no raw</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Rejeitadas</p>
          <p class="text-[23px] font-bold text-[var(--danger)]">{{ formatNumber(summary.total_rows_rejected) }}</p>
          <p class="tiny subtle mt-1">{{ formatPercent(summary.rejected_pct, 3) }} do total lido</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Erros / avisos</p>
          <p class="text-[23px] font-bold">
            <span class="text-[var(--danger)]">{{ formatNumber(errors) }}</span>
            <span class="text-[var(--muted)]"> / {{ formatNumber(warnings) }}</span>
          </p>
          <p class="tiny subtle mt-1">na execução mais recente</p>
        </div>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-3">
        <section class="card xl:col-span-2">
          <header class="card-header">
            <div>
              <h2 class="card-title">Execuções do pipeline</h2>
              <p class="card-subtitle">Início, fim, contagens e mensagem de erro quando houver</p>
            </div>
          </header>
          <div class="card-body pt-0">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Execução</th>
                    <th>Status</th>
                    <th class="num">Lidas</th>
                    <th class="num">Inseridas</th>
                    <th class="num">Atualizadas</th>
                    <th class="num">Rejeitadas</th>
                    <th>Início</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="run in runs" :key="run.id">
                    <td class="mono tiny">{{ run.run_id }}</td>
                    <td>
                      <StatusBadge
                        :label="ETL_STATUS[run.status].label"
                        :tone="ETL_STATUS[run.status].tone"
                      />
                    </td>
                    <td class="num">{{ formatNumber(run.rows_read) }}</td>
                    <td class="num">{{ formatNumber(run.rows_inserted) }}</td>
                    <td class="num">{{ formatNumber(run.rows_updated) }}</td>
                    <td class="num">{{ formatNumber(run.rows_rejected) }}</td>
                    <td>{{ formatDateTime(run.started_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Distribuição por tipo</h2>
              <p class="card-subtitle">Problemas da última execução</p>
            </div>
          </header>
          <div class="card-body">
            <div v-if="summary.issues_by_type.length" class="flex flex-col gap-1.5">
              <div v-for="item in summary.issues_by_type" :key="item.key" class="meter-row">
                <span class="meter-label">{{ issueTypeLabel(item.key) }}</span>
                <span class="meter-value">{{ formatNumber(item.count) }}</span>
              </div>
            </div>
            <EmptyState v-else title="Nenhum problema" description="A última execução não registrou rejeições nem avisos." icon="check" />
          </div>
        </section>
      </div>

      <section class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Registros rejeitados e avisos</h2>
            <p class="card-subtitle">
              Registros rejeitados não entram na camada curada. Avisos são mantidos com ressalva.
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <label class="field">
              <span class="label">Severidade</span>
              <select v-model="severity" class="select">
                <option value="">Todas</option>
                <option value="ERROR">Erros</option>
                <option value="WARNING">Avisos</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Entidade</span>
              <select v-model="entity" class="select">
                <option value="">Todas</option>
                <option v-for="item in entities" :key="item" :value="item">{{ entityLabel(item) }}</option>
              </select>
            </label>
          </div>
        </header>
        <div class="card-body pt-0">
          <div v-if="loading" class="py-3">
            <LoadingSkeleton variant="table" :rows="4" />
          </div>
          <template v-else-if="issues && issues.items.length">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Severidade</th>
                    <th>Entidade</th>
                    <th>Tipo</th>
                    <th>Referência</th>
                    <th>Detalhe</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="issue in issues.items" :key="issue.id">
                    <td>
                      <StatusBadge
                        :label="QUALITY_SEVERITY[issue.severity].label"
                        :tone="QUALITY_SEVERITY[issue.severity].tone"
                      />
                    </td>
                    <td>{{ entityLabel(issue.entity) }}</td>
                    <td class="strong">{{ issueTypeLabel(issue.issue_type) }}</td>
                    <td class="mono tiny">{{ issue.record_ref ?? '—' }}</td>
                    <td>{{ issue.detail }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <PaginationBar
              :page="issues.page"
              :pages="issues.pages"
              :total="issues.total"
              :page-size="issues.page_size"
              @update:page="page = $event"
            />
          </template>
          <EmptyState v-else title="Nenhum registro rejeitado" description="Todos os registros do conjunto passaram nas validações." icon="shield" />
        </div>
      </section>

      <div class="note-box mt-4">
        <Icon name="info" :size="16" class="mt-0.5" />
        <p>
          O gerador injeta casos controlados para demonstrar a rejeição: status inválido, data
          impossível, fim anterior ao início, campo obrigatório ausente, identificador duplicado,
          valor negativo e atendimento órfão. O total esperado é de 7 rejeições por execução.
        </p>
      </div>
    </template>
  </div>
</template>
