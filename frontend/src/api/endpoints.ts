/** Funções tipadas de acesso à API. */

import { api } from './client'
import type {
  Appointment,
  AppointmentDetail,
  AppointmentStatus,
  AttendanceDetail,
  AttendanceListItem,
  Breakdown,
  BreakdownDimension,
  EtlRun,
  FilterOptions,
  Granularity,
  OperationalSummary,
  Overview,
  Page,
  ProfessionalDetail,
  ProfessionalIndicator,
  ProfessionalProfile,
  QualityIssuePage,
  QualitySummary,
  SystemStatus,
  Timeseries,
  TokenResponse,
  User,
  UserAdmin,
  UserRole,
} from './types'

export interface PeriodFilters {
  start?: string
  end?: string
  unit_id?: number | null
  specialty_id?: number | null
  professional_id?: number | null
}

function filtersToQuery(filters: PeriodFilters): Record<string, string | number | null> {
  return {
    start: filters.start ?? null,
    end: filters.end ?? null,
    unit_id: filters.unit_id ?? null,
    specialty_id: filters.specialty_id ?? null,
    professional_id: filters.professional_id ?? null,
  }
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/api/v1/auth/login', { email, password }),
  me: () => api.get<User>('/api/v1/auth/me'),
}

export const metaApi = {
  options: () => api.get<FilterOptions>('/api/v1/meta/options'),
}

export const kpiApi = {
  overview: (filters: PeriodFilters) =>
    api.get<Overview>('/api/v1/kpis/overview', {
      query: filtersToQuery(filters),
    }),
  operational: () => api.get<OperationalSummary>('/api/v1/kpis/operational'),
  professionals: (filters: PeriodFilters) =>
    api.get<ProfessionalIndicator[]>('/api/v1/kpis/professionals', {
      query: filtersToQuery(filters),
    }),
  timeseries: (filters: PeriodFilters, granularity: Granularity) =>
    api.get<Timeseries>('/api/v1/kpis/timeseries', {
      query: { ...filtersToQuery(filters), granularity },
    }),
}

export const analyticsApi = {
  timeseries: (filters: PeriodFilters, granularity: Granularity) =>
    api.get<Timeseries>('/api/v1/analytics/timeseries', {
      query: { ...filtersToQuery(filters), granularity },
    }),
  breakdown: (filters: PeriodFilters, dimension: BreakdownDimension) =>
    api.get<Breakdown>('/api/v1/analytics/breakdown', {
      query: { ...filtersToQuery(filters), dimension },
    }),
  exportCsv: (filters: PeriodFilters) =>
    api.get<Blob>('/api/v1/analytics/export.csv', {
      query: filtersToQuery(filters),
      responseType: 'blob',
    }),
}

export interface AppointmentQuery extends PeriodFilters {
  status?: AppointmentStatus[]
  search?: string
  sort?: string
  direction?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export const appointmentApi = {
  list: (query: AppointmentQuery) =>
    api.get<Page<Appointment>>('/api/v1/appointments', {
      query: {
        ...filtersToQuery(query),
        status: query.status ?? null,
        search: query.search ?? null,
        sort: query.sort ?? null,
        direction: query.direction ?? null,
        page: query.page ?? 1,
        page_size: query.page_size ?? 25,
      },
    }),
  agenda: (query: PeriodFilters & { status?: AppointmentStatus[] }) =>
    api.get<Appointment[]>('/api/v1/appointments/agenda', {
      query: { ...filtersToQuery(query), status: query.status ?? null },
    }),
  detail: (id: number) => api.get<AppointmentDetail>(`/api/v1/appointments/${id}`),
}

export const attendanceApi = {
  list: (query: PeriodFilters & { search?: string; page?: number; page_size?: number }) =>
    api.get<Page<AttendanceListItem>>('/api/v1/attendances', {
      query: {
        ...filtersToQuery(query),
        search: query.search ?? null,
        page: query.page ?? 1,
        page_size: query.page_size ?? 25,
      },
    }),
  detail: (id: number) => api.get<AttendanceDetail>(`/api/v1/attendances/${id}`),
}

export const professionalApi = {
  list: (query: { unit_id?: number | null; specialty_id?: number | null } = {}) =>
    api.get<ProfessionalDetail[]>('/api/v1/professionals', {
      query: { unit_id: query.unit_id ?? null, specialty_id: query.specialty_id ?? null },
    }),
  indicators: (filters: PeriodFilters) =>
    api.get<ProfessionalIndicator[]>('/api/v1/professionals/indicators', {
      query: filtersToQuery(filters),
    }),
  detail: (id: number) => api.get<ProfessionalProfile>(`/api/v1/professionals/${id}`),
}

export const qualityApi = {
  summary: () => api.get<QualitySummary>('/api/v1/quality/summary'),
  issues: (query: {
    page?: number
    page_size?: number
    run_id?: number | null
    severity?: 'ERROR' | 'WARNING' | null
    entity?: string | null
  }) =>
    api.get<QualityIssuePage>('/api/v1/quality/issues', {
      query: {
        page: query.page ?? 1,
        page_size: query.page_size ?? 25,
        run_id: query.run_id ?? null,
        severity: query.severity ?? null,
        entity: query.entity ?? null,
      },
    }),
  runs: () => api.get<EtlRun[]>('/api/v1/quality/runs'),
}

export const adminApi = {
  status: () => api.get<SystemStatus>('/api/v1/admin/status'),
  users: () => api.get<UserAdmin[]>('/api/v1/admin/users'),
  createUser: (payload: {
    email: string
    full_name: string
    password: string
    role: UserRole
    professional_id?: number | null
  }) => api.post<UserAdmin>('/api/v1/admin/users', payload),
  updateUser: (
    id: number,
    payload: { full_name?: string; role?: UserRole; is_active?: boolean; password?: string },
  ) => api.patch<UserAdmin>(`/api/v1/admin/users/${id}`, payload),
}

export type { Appointment, AppointmentDetail, AttendanceListItem, UserRole }
