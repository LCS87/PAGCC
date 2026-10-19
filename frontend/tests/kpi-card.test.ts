import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { Kpi } from '@/api/types'
import KpiCard from '@/components/KpiCard.vue'

const kpi: Kpi = {
  key: 'attendance_rate',
  label: 'Taxa de comparecimento',
  value: 72.4,
  previous: 68.1,
  delta_pct: 6.31,
  unit: 'percent',
  favorable: 'up',
  formula: 'Realizadas ÷ elegíveis × 100',
  denominator: 120,
  sample_size: null,
}

describe('KpiCard', () => {
  it('renderiza rótulo, valor e comparação', () => {
    const wrapper = mount(KpiCard, { props: { kpi } })
    expect(wrapper.text()).toContain('Taxa de comparecimento')
    expect(wrapper.text()).toContain('72,4%')
    expect(wrapper.text()).toContain('antes 68,1%')
    expect(wrapper.text()).toContain('+6,3%')
    expect(wrapper.text()).toContain('base 120')
  })

  it('usa largura proporcional ao percentual', () => {
    const wrapper = mount(KpiCard, { props: { kpi } })
    const bar = wrapper.find('.progress-bar')
    expect(bar.attributes('style')).toContain('width: 72.4%')
  })

  it('exibe travessão para valor ausente', () => {
    const wrapper = mount(KpiCard, {
      props: {
        kpi: { ...kpi, value: null, previous: null, delta_pct: null, denominator: null },
      },
    })
    expect(wrapper.text()).toContain('—')
    expect(wrapper.text()).toContain('sem base')
  })
})
