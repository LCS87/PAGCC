import { describe, expect, it } from 'vitest'

import {
  APPOINTMENT_STATUS,
  addDaysISO,
  deltaTone,
  diffDays,
  formatDate,
  formatDateTime,
  formatMoney,
  formatPercent,
  formatSeconds,
  formatTime,
  isoToDateISO,
  startOfWeekISO,
  weekdayIndex,
} from '@/utils/format'

describe('datas', () => {
  it('soma dias em datas ISO sem deslocar fuso', () => {
    expect(addDaysISO('2026-10-19', 7)).toBe('2026-10-26')
    expect(addDaysISO('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDaysISO('2026-03-01', -1)).toBe('2026-02-28')
  })

  it('calcula a segunda-feira da semana', () => {
    expect(startOfWeekISO('2026-10-19')).toBe('2026-10-19')
    expect(startOfWeekISO('2026-10-22')).toBe('2026-10-19')
    expect(weekdayIndex('2026-10-19')).toBe(0)
    expect(weekdayIndex('2026-10-24')).toBe(5)
  })

  it('calcula diferença em dias', () => {
    expect(diffDays('2026-10-01', '2026-10-19')).toBe(18)
  })

  it('formata data brasileira', () => {
    expect(formatDate('2026-10-19')).toBe('19/10/2026')
    expect(formatDate(null)).toBe('—')
  })

  it('converte instante com offset para a data local da clínica', () => {
    expect(isoToDateISO('2026-10-20T01:30:00-03:00')).toBe('2026-10-20')
    expect(isoToDateISO('2026-10-20T02:30:00+00:00')).toBe('2026-10-19')
  })

  it('formata hora e data/hora', () => {
    expect(formatTime('2026-10-19T14:05:00-03:00')).toBe('14:05')
    expect(formatDateTime('2026-10-19T14:05:00-03:00')).toBe('19/10/2026 14:05')
  })
})

describe('números e métricas', () => {
  it('formata moeda, percentual e segundos', () => {
    expect(formatMoney(1234.5)).toContain('1.234,50')
    expect(formatPercent(73.678)).toBe('73,7%')
    expect(formatSeconds(45)).toBe('45 s')
    expect(formatSeconds(90)).toBe('2 min')
    expect(formatSeconds(3900)).toBe('1 h 5 min')
  })

  it('define tom da variação conforme direção favorável', () => {
    expect(deltaTone(12, 'up')).toBe('good')
    expect(deltaTone(12, 'down')).toBe('bad')
    expect(deltaTone(-8, 'down')).toBe('good')
    expect(deltaTone(0, 'up')).toBe('flat')
    expect(deltaTone(null, 'up')).toBe('flat')
  })

  it('mapeia status para rótulos e tons', () => {
    expect(APPOINTMENT_STATUS.CONCLUIDA.label).toBe('Concluída')
    expect(APPOINTMENT_STATUS.FALTA.tone).toBe('red')
    expect(APPOINTMENT_STATUS.REAGENDADA.tone).toBe('purple')
  })
})
