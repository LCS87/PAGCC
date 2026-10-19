/** Formatação pt-BR e metadados de status (fonte única para as telas). */

import type {
  AppointmentStatus,
  EtlStatus,
  Kpi,
  PaymentMethod,
  PaymentStatus,
  QualitySeverity,
  Role,
} from '@/api/types'
import { ROLE_LABELS } from '@/api/types'

export const CLINIC_TIMEZONE = import.meta.env.VITE_CLINIC_TIMEZONE || 'America/Fortaleza'

export type Tone = 'green' | 'blue' | 'teal' | 'amber' | 'red' | 'purple' | 'slate'

const numberFormatter = new Intl.NumberFormat('pt-BR')
const decimalFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const moneyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/

function dateOnlyToUtc(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(Date.UTC(year, (month ?? 1) - 1, day ?? 1))
}

function safeDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const parsed = DATE_ONLY.test(value) ? dateOnlyToUtc(value) : new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function todayISO(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: CLINIC_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

export function addDaysISO(iso: string, days: number): string {
  const date = dateOnlyToUtc(iso)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** Converte um instante ISO com offset para a data local da clínica (AAAA-MM-DD). */
export function isoToDateISO(value: string | null | undefined): string {
  if (!value) return ''
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: CLINIC_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value))
}

export function diffDays(startISO: string, endISO: string): number {
  const start = dateOnlyToUtc(startISO).getTime()
  const end = dateOnlyToUtc(endISO).getTime()
  return Math.round((end - start) / 86_400_000)
}

export function startOfWeekISO(iso: string): string {
  const date = dateOnlyToUtc(iso)
  const weekday = date.getUTCDay()
  const offset = (weekday + 6) % 7
  date.setUTCDate(date.getUTCDate() - offset)
  return date.toISOString().slice(0, 10)
}

export function weekdayIndex(iso: string): number {
  return (dateOnlyToUtc(iso).getUTCDay() + 6) % 7
}

export const WEEKDAY_LABELS = [
  'Segunda',
  'Terça',
  'Quarta',
  'Quinta',
  'Sexta',
  'Sábado',
  'Domingo',
]

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  if (DATE_ONLY.test(value)) {
    const [year, month, day] = value.split('-')
    return `${day}/${month}/${year}`
  }
  const date = safeDate(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: CLINIC_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date)
}

export function formatDateShort(value: string | null | undefined): string {
  if (!value) return '—'
  if (DATE_ONLY.test(value)) {
    const [, month, day] = value.split('-')
    return `${day}/${month}`
  }
  const date = safeDate(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: CLINIC_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
  }).format(date)
}

export function formatTime(value: string | null | undefined): string {
  const date = safeDate(value)
  if (!date) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: CLINIC_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return `${formatDate(value)} ${formatTime(value)}`
}

export function formatWeekdayDate(value: string): string {
  const date = dateOnlyToUtc(value)
  const weekday = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'UTC',
    weekday: 'short',
  })
    .format(date)
    .replace('.', '')
  return `${weekday}, ${formatDateShort(value)}`
}

export function formatMonth(value: string): string {
  const date = DATE_ONLY.test(value) ? dateOnlyToUtc(value) : safeDate(value)
  if (!date) return value
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: DATE_ONLY.test(value) ? 'UTC' : CLINIC_TIMEZONE,
    month: 'short',
    year: '2-digit',
  })
    .format(date)
    .replace('.', '')
}

export function formatDateRange(start: string, end: string): string {
  if (!start || !end) return '—'
  if (start === end) return formatDate(start)
  const sameYear = start.slice(0, 4) === end.slice(0, 4)
  return sameYear
    ? `${formatDateShort(start)} a ${formatDate(end)}`
    : `${formatDate(start)} a ${formatDate(end)}`
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return numberFormatter.format(value)
}

export function formatDecimal(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return decimalFormatter.format(value)
}

export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return moneyFormatter.format(value)
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)}%`
}

export function formatDelta(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'sem base'
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatDecimal(value)}%`
}

export function formatSeconds(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  if (value < 60) return `${Math.round(value)} s`
  const minutes = Math.round(value / 60)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return remainder ? `${hours} h ${remainder} min` : `${hours} h`
}

export function formatKpiValue(kpi: Kpi): string {
  return formatByUnit(kpi.value, kpi.unit)
}

export function formatByUnit(
  value: number | null | undefined,
  unit: Kpi['unit'],
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  switch (unit) {
    case 'currency':
      return formatMoney(value)
    case 'percent':
      return formatPercent(value)
    case 'seconds':
      return formatSeconds(value)
    default:
      return formatNumber(value)
  }
}

export function deltaTone(
  delta: number | null | undefined,
  favorable: Kpi['favorable'],
): 'good' | 'bad' | 'flat' {
  if (delta === null || delta === undefined || Math.abs(delta) < 0.05) return 'flat'
  if (favorable === 'neutral') return 'flat'
  if (delta > 0) return favorable === 'up' ? 'good' : 'bad'
  return favorable === 'down' ? 'good' : 'bad'
}

export function initials(name: string): string {
  const parts = name
    .replace(/^(Dra?\.|Prof\.?)\s+/i, '')
    .split(/\s+/)
    .filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export function roleLabel(role: Role): string {
  return ROLE_LABELS[role] ?? role
}

export const APPOINTMENT_STATUS: Record<
  AppointmentStatus,
  { label: string; tone: Tone }
> = {
  AGENDADA: { label: 'Agendada', tone: 'blue' },
  CONFIRMADA: { label: 'Confirmada', tone: 'teal' },
  EM_ATENDIMENTO: { label: 'Em atendimento', tone: 'amber' },
  CONCLUIDA: { label: 'Concluída', tone: 'green' },
  CANCELADA_PACIENTE: { label: 'Cancelada pelo paciente', tone: 'red' },
  CANCELADA_CLINICA: { label: 'Cancelada pela clínica', tone: 'slate' },
  FALTA: { label: 'Falta', tone: 'red' },
  REAGENDADA: { label: 'Reagendada', tone: 'purple' },
}

export const SOURCE_LABELS: Record<string, string> = {
  TELEFONE: 'Telefone',
  WHATSAPP: 'WhatsApp',
  BALCAO: 'Balcão',
  PORTAL: 'Portal',
}

export const PAYMENT_STATUS: Record<PaymentStatus, { label: string; tone: Tone }> = {
  PAGO: { label: 'Pago', tone: 'green' },
  PENDENTE: { label: 'Pendente', tone: 'amber' },
  ESTORNADO: { label: 'Estornado', tone: 'red' },
}

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  PIX: 'Pix',
  CARTAO_CREDITO: 'Cartão de crédito',
  CARTAO_DEBITO: 'Cartão de débito',
  DINHEIRO: 'Dinheiro',
  CONVENIO: 'Convênio',
}

export const SEVERITY_META: Record<
  'critical' | 'warning' | 'info',
  { label: string; tone: Tone }
> = {
  critical: { label: 'Crítico', tone: 'red' },
  warning: { label: 'Atenção', tone: 'amber' },
  info: { label: 'Informativo', tone: 'blue' },
}

export const QUALITY_SEVERITY: Record<QualitySeverity, { label: string; tone: Tone }> = {
  ERROR: { label: 'Erro', tone: 'red' },
  WARNING: { label: 'Aviso', tone: 'amber' },
}

export const ETL_STATUS: Record<EtlStatus, { label: string; tone: Tone }> = {
  RUNNING: { label: 'Em execução', tone: 'blue' },
  SUCCESS: { label: 'Sucesso', tone: 'green' },
  PARTIAL: { label: 'Parcial', tone: 'amber' },
  FAILED: { label: 'Falhou', tone: 'red' },
}

export const ENTITY_LABELS: Record<string, string> = {
  appointments: 'Agendamentos',
  attendances: 'Atendimentos',
  payments: 'Pagamentos',
  status_history: 'Histórico de status',
  professionals: 'Profissionais',
  units: 'Unidades',
  specialties: 'Especialidades',
  service_types: 'Tipos de serviço',
  availability: 'Disponibilidade',
  clinic: 'Clínica',
}

export function entityLabel(entity: string): string {
  return ENTITY_LABELS[entity] ?? entity
}

export const ISSUE_TYPE_LABELS: Record<string, string> = {
  invalid_status: 'Status inválido',
  invalid_datetime: 'Data/hora inválida',
  end_before_start: 'Fim anterior ao início',
  missing_required_field: 'Campo obrigatório ausente',
  duplicate_external_id: 'Identificador duplicado',
  negative_amount: 'Valor negativo',
  orphan_attendance: 'Atendimento órfão',
  orphan_payment: 'Pagamento órfão',
  orphan_history: 'Histórico órfão',
  unknown_professional: 'Profissional inexistente',
  unknown_unit: 'Unidade inexistente',
  unknown_specialty: 'Especialidade inexistente',
  unknown_service: 'Serviço inexistente',
  dimension_mismatch: 'Dimensões inconsistentes',
  received_above_charged: 'Recebido maior que cobrado',
  arrived_after_start: 'Chegada após o início',
  missing_external_id: 'Identificador ausente',
  invalid_json: 'JSON inválido',
  unknown_reschedule_reference: 'Referência de reagendamento inválida',
  arrived_after_started: 'Chegada após o início',
  invalid_amount: 'Valor inválido',
  invalid_payment_method: 'Forma de pagamento inválida',
  invalid_payment_status: 'Status de pagamento inválido',
  invalid_confirmation_datetime: 'Confirmação com data inválida',
  invalid_cancellation_actor: 'Autor do cancelamento inválido',
  invalid_service_values: 'Valores do serviço inválidos',
  duplicate_code: 'Código duplicado',
  invalid_availability: 'Disponibilidade inválida',
}

export function issueTypeLabel(issueType: string): string {
  return ISSUE_TYPE_LABELS[issueType] ?? issueType.replaceAll('_', ' ')
}

export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural
}

export function maskEmpty(value: string | null | undefined): string {
  return value && value.trim() ? value : '—'
}
