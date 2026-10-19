import { ref, watch } from 'vue'

import type { DashboardFilters } from '@/api/types'
import { useMetaStore } from '@/stores/meta'
import { addDaysISO } from '@/utils/format'

export function emptyFilters(): DashboardFilters {
  return {
    start: '',
    end: '',
    unit_id: null,
    specialty_id: null,
    professional_id: null,
  }
}

export function lastDaysFilters(endISO: string, days = 30): DashboardFilters {
  return {
    start: addDaysISO(endISO, -(days - 1)),
    end: endISO,
    unit_id: null,
    specialty_id: null,
    professional_id: null,
  }
}

/**
 * Filtros padrão ancorados na data de demonstração da API (âncora do pipeline).
 * Garante que os dados existam mesmo se o conjunto foi gerado em outro dia.
 */
export function useDashboardFilters(defaultDays = 30) {
  const meta = useMetaStore()
  const filters = ref<DashboardFilters>(emptyFilters())

  function initialize(endISO: string) {
    filters.value = lastDaysFilters(endISO, defaultDays)
  }

  watch(
    () => meta.options,
    (options) => {
      if (options && !filters.value.end) initialize(options.demo_today)
    },
    { immediate: true },
  )

  return { filters, initialize }
}
