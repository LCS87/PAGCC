<script setup lang="ts">
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  CanvasRenderer,
])

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    height?: string
    ariaLabel?: string
  }>(),
  { height: '320px', ariaLabel: 'Gráfico' },
)

const container = ref<HTMLDivElement | null>(null)
let instance: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!instance) return
  instance.setOption(props.option, true)
}

onMounted(() => {
  if (!container.value) return
  instance = echarts.init(container.value, undefined, { renderer: 'canvas' })
  render()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => instance?.resize())
    observer.observe(container.value)
  }
})

watch(
  () => props.option,
  () => render(),
  { deep: true },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  instance?.dispose()
  instance = null
})
</script>

<template>
  <div
    ref="container"
    class="chart-box"
    :style="{ height }"
    role="img"
    :aria-label="ariaLabel"
  />
</template>
