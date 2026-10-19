<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { errorMessage } from '@/api/client'
import { attendanceApi } from '@/api/endpoints'
import type { AttendanceDetail } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import {
  PAYMENT_METHOD_LABELS,
  PAYMENT_STATUS,
  SOURCE_LABELS,
  formatDate,
  formatDateTime,
  formatMoney,
  formatSeconds,
  formatTime,
} from '@/utils/format'

const route = useRoute()
const detail = ref<AttendanceDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    detail.value = await attendanceApi.detail(Number(route.params.id))
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

onMounted(load)

const appointment = computed(() => detail.value?.appointment ?? null)
const attendance = computed(() => detail.value?.attendance ?? null)
const payments = computed(() => attendance.value?.payments ?? [])

const totalCharged = computed(() =>
  payments.value.reduce((sum, payment) => sum + payment.amount_charged, 0),
)
const totalReceived = computed(() =>
  payments.value.reduce(
    (sum, payment) => sum + payment.amount_received - payment.refund_amount,
    0,
  ),
)
</script>

<template>
  <div>
    <div class="mb-3">
      <RouterLink to="/atendimentos" class="btn btn-sm btn-ghost">
        <Icon name="chevron-left" :size="14" /> Atendimentos
      </RouterLink>
    </div>

    <LoadingSkeleton v-if="loading" variant="chart" height="120px" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="detail && attendance && appointment">
      <PageHeader
        eyebrow="Detalhe administrativo"
        :title="`Atendimento ${appointment.patient_ref}`"
        :description="`${formatDate(appointment.scheduled_start)} · ${formatTime(appointment.scheduled_start)} · ${appointment.professional.full_name}`"
      >
        <template #actions>
          <StatusBadge :status="appointment.status" />
        </template>
      </PageHeader>

      <div class="grid gap-4 xl:grid-cols-3">
        <section class="card xl:col-span-2">
          <header class="card-header">
            <div>
              <h2 class="card-title">Dados do atendimento</h2>
              <p class="card-subtitle">Registro administrativo, sem conteúdo clínico</p>
            </div>
            <span class="badge badge--slate mono">{{ attendance.external_id }}</span>
          </header>
          <div class="card-body grid gap-4 sm:grid-cols-2">
            <div>
              <p class="label">Chegada</p>
              <p class="text-[13px] font-medium">{{ formatDateTime(attendance.arrived_at) }}</p>
            </div>
            <div>
              <p class="label">Início</p>
              <p class="text-[13px] font-medium">{{ formatDateTime(attendance.started_at) }}</p>
            </div>
            <div>
              <p class="label">Fim</p>
              <p class="text-[13px] font-medium">{{ formatDateTime(attendance.ended_at) }}</p>
            </div>
            <div>
              <p class="label">Espera</p>
              <p class="text-[13px] font-medium">
                {{
                  formatSeconds(
                    attendance.arrived_at
                      ? (new Date(attendance.started_at).getTime() -
                        new Date(attendance.arrived_at).getTime()) /
                        1000
                      : null,
                  )
                }}
              </p>
            </div>
            <div class="sm:col-span-2">
              <p class="label">Profissional e local</p>
              <p class="text-[13px] font-medium">
                {{ appointment.professional.full_name }} · {{ appointment.specialty.name }} ·
                {{ appointment.unit.name }}
              </p>
              <p class="tiny subtle">
                {{ appointment.service_type.name }} ({{ appointment.service_type.duration_minutes }} min)
                · origem {{ SOURCE_LABELS[appointment.source] ?? appointment.source }}
              </p>
            </div>
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Financeiro simulado</h2>
              <p class="card-subtitle">Separado do atendimento</p>
            </div>
          </header>
          <div class="card-body">
            <div class="flex items-baseline justify-between">
              <div>
                <p class="tiny subtle">Cobrado</p>
                <p class="text-[22px] font-bold">{{ formatMoney(totalCharged) }}</p>
              </div>
              <div class="text-right">
                <p class="tiny subtle">Recebido líquido</p>
                <p class="text-[15px] font-semibold">{{ formatMoney(totalReceived) }}</p>
              </div>
            </div>
            <div v-if="payments.length" class="mt-3 flex flex-col gap-2">
              <div v-for="payment in payments" :key="payment.id" class="note-box flex-col">
                <div class="flex items-center justify-between">
                  <span class="font-medium">{{ PAYMENT_METHOD_LABELS[payment.method] }}</span>
                  <StatusBadge
                    :label="PAYMENT_STATUS[payment.status].label"
                    :tone="PAYMENT_STATUS[payment.status].tone"
                  />
                </div>
                <span class="tiny subtle">
                  cobrado {{ formatMoney(payment.amount_charged) }} · recebido
                  {{ formatMoney(payment.amount_received) }} · estorno
                  {{ formatMoney(payment.refund_amount) }}
                </span>
                <span class="tiny subtle">Registrado em {{ formatDateTime(payment.recorded_at) }}</span>
              </div>
            </div>
            <EmptyState v-else title="Sem registro financeiro" description="Nenhum pagamento simulado foi associado." icon="wallet" />
          </div>
        </section>
      </div>

      <section class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Vínculo com o agendamento</h2>
            <p class="card-subtitle">Um atendimento só existe para agendamentos concluídos</p>
          </div>
          <RouterLink to="/agenda" class="btn btn-sm btn-ghost">
            Ver na agenda <Icon name="chevron-right" :size="13" />
          </RouterLink>
        </header>
        <div class="card-body grid gap-3 sm:grid-cols-3">
          <div class="note-box flex-col">
            <span class="tiny subtle">Agendamento</span>
            <span class="mono text-[12px]">{{ appointment.external_id }}</span>
          </div>
          <div class="note-box flex-col">
            <span class="tiny subtle">Horário previsto</span>
            <span class="text-[12px] font-medium">{{ formatDateTime(appointment.scheduled_start) }}</span>
          </div>
          <div class="note-box flex-col">
            <span class="tiny subtle">Confirmação</span>
            <span class="text-[12px] font-medium">{{ formatDateTime(appointment.confirmed_at) }}</span>
          </div>
        </div>
      </section>

      <div class="note-box mt-4">
        <Icon name="shield" :size="16" class="mt-0.5" />
        <p>
          Este projeto não armazena prontuário, diagnóstico, prescrição ou qualquer informação
          clínica. Os valores financeiros são sintéticos e não representam faturamento real.
        </p>
      </div>
    </template>
  </div>
</template>
