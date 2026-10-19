import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { metaApi } from '@/api/endpoints'
import { errorMessage } from '@/api/client'
import type { FilterOptions } from '@/api/types'
import { todayISO } from '@/utils/format'

export const useMetaStore = defineStore('meta', () => {
  const options = ref<FilterOptions | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let inflight: Promise<void> | null = null

  async function load(force = false): Promise<void> {
    if (options.value && !force) return
    if (inflight) return inflight
    loading.value = true
    error.value = null
    inflight = (async () => {
      try {
        options.value = await metaApi.options()
      } catch (cause) {
        error.value = errorMessage(cause)
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    return inflight
  }

  const demoToday = computed(() => options.value?.demo_today ?? todayISO())
  const clinicName = computed(() => options.value?.clinic?.name ?? 'Clínica Vida Integrada')
  const timezone = computed(() => options.value?.timezone ?? 'America/Fortaleza')

  return { options, loading, error, demoToday, clinicName, timezone, load }
})
