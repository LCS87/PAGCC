/** Contratos da API (espelham backend/app/schemas). */

export type Role =
  | 'ADMIN'
  | 'GESTOR'
  | 'COORDENADOR'
  | 'ANALISTA'
  | 'RECEPCAO'
  | 'PROFISSIONAL'

export type UserRole = Role

export type AppointmentStatus =
  | 'AGENDADA'
  | 'CONFIRMADA'
  | 'EM_ATENDIMENTO'
  | 'CONCLUIDA'
  | 'CANCELADA_PACIENTE'
  | 'CANCELADA_CLINICA'
  | 'FALTA'
  | 'REAGENDADA'

export type AppointmentSource = 'TELEFONE' | 'WHATSAPP' | 'BALCAO' | 'PORTAL'
export type CancellationActor = 'PACIENTE' | 'CLINICA'
export type AttendanceStatus = 'CONCLUIDO' | 'EM_ANDAMENTO'
export type PaymentStatus = 'PAGO' | 'PENDENTE' | 'ESTORNADO'
export type PaymentMethod =
  | 'PIX'
  | 'CARTAO_CREDITO'
  | 'CARTAO_DEBITO'
  | 'DINHEIRO'
  | 'CONVENIO'
export type QualitySeverity = 'WARNING' | 'ERROR'
export type EtlStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED'
export type Granularity = 'day' | 'week' | 'month'
export type KpiUnit = 'count' | 'percent' | 'currency' | 'seconds'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  professional_id: number | null
  is_active: boolean
}

export interface UserAdmin extends User {
  last_login_at: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Unit {
  id: number
  code: string
  name: string
  city: string
  is_active?: boolean
}

export interface Specialty {
  id: number
  code: string
  name: string
}

export interface UnitOption {
  id: number
  code: string
  name: string
  city: string
}

export interface Availability {
  weekday: number
  start_time: string
  end_time: string
}

export interface Professional {
  id: number
  code: string
  full_name: string
  email: string
  is_active: boolean
  unit: Unit
  specialty: Specialty
}

export interface ProfessionalDetail extends Professional {
  availabilities: Availability[]
}

export interface ServiceType {
  id: number
  code: string
  name: string
  duration_minutes: number
  base_price: number
}

export interface Payment {
  id: number
  amount_charged: number
  amount_received: number
  refund_amount: number
  method: PaymentMethod
  status: PaymentStatus
  recorded_at: string
}

export interface Attendance {
  id: number
  external_id: string
  arrived_at: string | null
  started_at: string
  ended_at: string | null
  status: AttendanceStatus
  payments: Payment[]
}

export interface TimelineEvent {
  from_status: AppointmentStatus | null
  to_status: AppointmentStatus
  changed_at: string
  reason: string | null
}

export interface Appointment {
  id: number
  external_id: string
  patient_ref: string
  scheduled_start: string
  scheduled_end: string
  status: AppointmentStatus
  source: AppointmentSource
  confirmed_at: string | null
  cancellation_actor: CancellationActor | null
  cancellation_reason: string | null
  professional: Professional
  unit: Unit
  specialty: Specialty
  service_type: ServiceType
  priced_amount: number | null
  wait_seconds: number | null
}

export interface AppointmentDetail extends Appointment {
  attendance: Attendance | null
  timeline: TimelineEvent[]
  rescheduled_from_id: number | null
}

export interface AttendanceListItem {
  id: number
  external_id: string
  appointment_id: number
  arrived_at: string | null
  started_at: string
  ended_at: string | null
  status: AttendanceStatus
  patient_ref: string
  professional_name: string
  specialty_name: string
  unit_name: string
  scheduled_start: string
  wait_seconds: number | null
  amount_charged: number
}

export interface AttendanceDetail {
  attendance: Attendance
  appointment: Appointment | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface Kpi {
  key: string
  label: string
  value: number | null
  previous: number | null
  delta_pct: number | null
  unit: KpiUnit
  favorable: 'up' | 'down' | 'neutral'
  formula: string
  denominator: number | null
  sample_size: number | null
}

export interface Period {
  start: string
  end: string
}

export interface Overview {
  period: Period
  previous_period: Period
  kpis: Kpi[]
  generated_at: string
  demo_mode: boolean
}

export interface SeriesPoint {
  bucket: string
  label: string
  scheduled: number
  completed: number
  no_show: number
  cancelled: number
  rescheduled: number
  occupancy_pct: number | null
  revenue: number
  wait_seconds_avg: number | null
}

export interface Timeseries {
  granularity: Granularity
  points: SeriesPoint[]
}

export interface BreakdownItem {
  key: string
  label: string
  scheduled: number
  completed: number
  no_show: number
  cancelled: number
  occupancy_pct: number | null
  no_show_rate: number | null
  revenue: number
  ticket: number | null
  share_pct: number | null
  extra: Record<string, string | number | null> | null
}

export interface Breakdown {
  dimension: string
  items: BreakdownItem[]
}

export interface OperationalTask {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  rule: string
  count: number
  due_at: string | null
  link: string | null
}

export interface OperationalSummary {
  generated_at: string
  tasks: OperationalTask[]
  counts: Record<string, number>
  next_days: string[]
}

export interface ProfessionalIndicator {
  professional: Professional
  scheduled: number
  completed: number
  no_show: number
  cancelled: number
  attendance_rate: number | null
  no_show_rate: number | null
  occupancy_pct: number | null
  revenue: number
  wait_seconds_avg: number | null
}

export interface ProfessionalProfile {
  professional: ProfessionalDetail
  indicator: ProfessionalIndicator | null
  recent_appointments: Appointment[]
}

export interface EtlRun {
  id: number
  run_id: string
  started_at: string
  finished_at: string | null
  status: EtlStatus
  source_seed: number
  anchor_date: string
  raw_path: string
  rows_read: number
  rows_inserted: number
  rows_updated: number
  rows_rejected: number
  message: string | null
}

export interface QualityIssue {
  id: number
  etl_run_id: number
  entity: string
  issue_type: string
  severity: QualitySeverity
  record_ref: string | null
  detail: string
  created_at: string
}

export interface QualityIssuePage {
  items: QualityIssue[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface QualitySummary {
  last_run: EtlRun | null
  total_runs: number
  issues_by_severity: Record<string, number>
  issues_by_type: { key: string; count: number }[]
  total_rows_read: number
  total_rows_rejected: number
  rejected_pct: number
  recent_runs: EtlRun[]
}

export interface SystemStatus {
  app_name: string
  version: string
  environment: string
  timezone: string
  database: string
  demo_mode: boolean
  demo_today: string
  pipeline_last_run: EtlRun | null
  counts: Record<string, number>
}

export interface FilterOptions {
  units: UnitOption[]
  specialties: Specialty[]
  professionals: Professional[]
  statuses: AppointmentStatus[]
  demo_today: string
  min_date: string | null
  max_date: string | null
  timezone: string
  clinic: { id: number; code: string; name: string; timezone: string } | null
}

export interface DashboardFilters {
  start: string
  end: string
  unit_id: number | null
  specialty_id: number | null
  professional_id: number | null
}

export type BreakdownDimension =
  | 'specialty'
  | 'professional'
  | 'unit'
  | 'weekday'
  | 'hour'
  | 'status'
  | 'source'

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: 'Administrador',
  GESTOR: 'Gestor',
  COORDENADOR: 'Coordenador',
  ANALISTA: 'Analista',
  RECEPCAO: 'Recepção',
  PROFISSIONAL: 'Profissional',
}
