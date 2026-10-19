import type { EChartsOption, SeriesOption } from 'echarts'

import type { BreakdownItem, SeriesPoint } from '@/api/types'
import {
  formatByUnit,
  formatMoney,
  formatNumber,
  formatPercent,
  formatSeconds,
  type Tone,
} from './format'

function cssVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

export interface ChartColors {
  text: string
  muted: string
  grid: string
  surface: string
  border: string
  primary: string
  info: string
  success: string
  warning: string
  danger: string
  purple: string
  mutedSolid: string
}

export function chartColors(): ChartColors {
  return {
    text: cssVar('--text', '#0f172a'),
    muted: cssVar('--muted', '#5b6b82'),
    grid: cssVar('--chart-grid', '#e5ebf3'),
    surface: cssVar('--surface', '#ffffff'),
    border: cssVar('--border', '#dde5f0'),
    primary: cssVar('--primary', '#0f766e'),
    info: cssVar('--info', '#0369a1'),
    success: cssVar('--success', '#15803d'),
    warning: cssVar('--warning', '#b45309'),
    danger: cssVar('--danger', '#b91c1c'),
    purple: cssVar('--purple', '#7e22ce'),
    mutedSolid: cssVar('--muted', '#64748b'),
  }
}

export const TONE_COLORS: Record<Tone, keyof ChartColors> = {
  green: 'success',
  blue: 'info',
  teal: 'primary',
  amber: 'warning',
  red: 'danger',
  purple: 'purple',
  slate: 'mutedSolid',
}

export type SeriesMetricKey =
  | 'scheduled'
  | 'completed'
  | 'no_show'
  | 'cancelled'
  | 'occupancy_pct'
  | 'revenue'
  | 'wait_seconds_avg'

export const SERIES_METRICS: Record<
  SeriesMetricKey,
  { label: string; tone: Tone; format: (value: number | null | undefined) => string; unit: 'count' | 'percent' | 'currency' | 'seconds' }
> = {
  scheduled: { label: 'Agendadas', tone: 'blue', format: formatNumber, unit: 'count' },
  completed: { label: 'Realizadas', tone: 'green', format: formatNumber, unit: 'count' },
  no_show: { label: 'Faltas', tone: 'red', format: formatNumber, unit: 'count' },
  cancelled: { label: 'Canceladas', tone: 'amber', format: formatNumber, unit: 'count' },
  occupancy_pct: {
    label: 'Ocupação da agenda',
    tone: 'teal',
    format: formatPercent,
    unit: 'percent',
  },
  revenue: { label: 'Receita simulada', tone: 'purple', format: formatMoney, unit: 'currency' },
  wait_seconds_avg: {
    label: 'Espera média',
    tone: 'amber',
    format: formatSeconds,
    unit: 'seconds',
  },
}

export type BreakdownMetricKey =
  | 'scheduled'
  | 'completed'
  | 'no_show'
  | 'cancelled'
  | 'occupancy_pct'
  | 'revenue'
  | 'no_show_rate'

const BREAKDOWN_LABELS: Record<BreakdownMetricKey, string> = {
  scheduled: 'Agendadas',
  completed: 'Realizadas',
  no_show: 'Faltas',
  cancelled: 'Canceladas',
  occupancy_pct: 'Ocupação',
  revenue: 'Receita simulada',
  no_show_rate: 'Taxa de faltas',
}

function tooltipStyle(colors: ChartColors) {
  return {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    padding: [8, 10] as [number, number],
    textStyle: { color: colors.text, fontSize: 12 },
    extraCssText: 'border-radius:10px;box-shadow:0 12px 32px -18px rgba(0,0,0,.45);',
  }
}

function tooltipFormatter(
  colors: ChartColors,
  formatter: (value: number) => string,
): (params: unknown) => string {
  return (params: unknown) => {
    const list = (Array.isArray(params) ? params : [params]) as Array<{
      axisValueLabel?: string
      name?: string
      seriesName?: string
      marker?: string
      value?: number
    }>
    if (list.length === 0) return ''
    const title = list[0]?.axisValueLabel ?? list[0]?.name ?? ''
    const rows = list
      .map((item) => {
        const value = typeof item.value === 'number' ? item.value : Number(item.value ?? 0)
        return `<div style="display:flex;align-items:center;justify-content:space-between;gap:18px;line-height:1.9">
          <span>${item.marker ?? ''}${item.seriesName ?? ''}</span>
          <strong style="color:${colors.text}">${formatter(value)}</strong>
        </div>`
      })
      .join('')
    return `<div style="min-width:150px"><div style="font-weight:650;margin-bottom:3px;color:${colors.muted};font-size:11px">${title}</div>${rows}</div>`
  }
}

function axisCommon(colors: ChartColors) {
  return {
    axisLine: { lineStyle: { color: colors.border } },
    axisTick: { show: false },
    axisLabel: { color: colors.muted, fontSize: 11 },
    splitLine: { lineStyle: { color: colors.grid, type: 'dashed' as const } },
  }
}

/** Série temporal com uma ou mais métricas de contagem. */
export function trendOption(
  points: SeriesPoint[],
  metrics: SeriesMetricKey[],
): EChartsOption {
  const colors = chartColors()
  const series: SeriesOption[] = metrics.map((key) => {
    const meta = SERIES_METRICS[key]
    const color = colors[TONE_COLORS[meta.tone]]
    return {
      name: meta.label,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: points.length <= 40,
      lineStyle: { width: 2.4, color },
      itemStyle: { color, borderWidth: 0 },
      areaStyle: metrics.length === 1 ? { color, opacity: 0.1 } : undefined,
      emphasis: { focus: 'series' },
      data: points.map((point) => point[key]),
    }
  })

  return {
    textStyle: { fontFamily: 'Inter, Segoe UI, system-ui, sans-serif' },
    grid: { left: 10, right: 18, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      ...tooltipStyle(colors),
      formatter: tooltipFormatter(colors, (value) =>
        metrics.length === 1 ? SERIES_METRICS[metrics[0]].format(value) : formatNumber(value),
      ),
      axisPointer: { type: 'line', lineStyle: { color: colors.border } },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: points.map((point) => point.label),
      ...axisCommon(colors),
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      ...axisCommon(colors),
      axisLine: { show: false },
      axisLabel: {
        color: colors.muted,
        fontSize: 11,
        formatter: (value: number) =>
          metrics.length === 1 && SERIES_METRICS[metrics[0]].unit === 'percent'
            ? `${value}%`
            : formatNumber(value),
      },
    },
    series,
  }
}

/** Barras horizontais para uma segmentação. */
export function breakdownBarOption(
  items: BreakdownItem[],
  metric: BreakdownMetricKey,
): EChartsOption {
  const colors = chartColors()
  const sorted = [...items].sort(
    (a, b) => Number(b[metric] ?? 0) - Number(a[metric] ?? 0),
  )
  const formatter =
    metric === 'revenue'
      ? formatMoney
      : metric === 'occupancy_pct' || metric === 'no_show_rate'
        ? formatPercent
        : formatNumber

  return {
    textStyle: { fontFamily: 'Inter, Segoe UI, system-ui, sans-serif' },
    grid: { left: 8, right: 30, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      ...tooltipStyle(colors),
      formatter: tooltipFormatter(colors, formatter),
    },
    xAxis: {
      type: 'value',
      ...axisCommon(colors),
      axisLine: { show: false },
      axisLabel: {
        color: colors.muted,
        fontSize: 11,
        formatter:
          metric === 'revenue'
            ? (value: number) => formatMoney(value)
            : metric === 'occupancy_pct' || metric === 'no_show_rate'
              ? (value: number) => `${value}%`
              : undefined,
      },
    },
    yAxis: {
      type: 'category',
      data: sorted.map((item) => item.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: colors.text, fontSize: 11.5, width: 130, overflow: 'truncate' },
    },
    series: [
      {
        name: BREAKDOWN_LABELS[metric],
        type: 'bar',
        data: sorted.map((item) => Number(item[metric] ?? 0)),
        barMaxWidth: 18,
        itemStyle: {
          color: colors.primary,
          borderRadius: [0, 5, 5, 0],
        },
        emphasis: { itemStyle: { color: colors.info } },
      },
    ],
  }
}

/** Rosca para distribuição (status, origem, etc.). */
export function donutOption(items: BreakdownItem[]): EChartsOption {
  const colors = chartColors()
  const palette = [
    colors.info,
    colors.primary,
    colors.warning,
    colors.success,
    colors.danger,
    colors.purple,
    colors.mutedSolid,
  ]
  return {
    textStyle: { fontFamily: 'Inter, Segoe UI, system-ui, sans-serif' },
    tooltip: {
      trigger: 'item',
      ...tooltipStyle(colors),
      formatter: (params: unknown) => {
        const item = params as { name?: string; value?: number; percent?: number }
        return `<div style="display:flex;gap:12px;justify-content:space-between"><span>${item.name}</span><strong>${formatNumber(item.value ?? 0)} (${formatPercent(item.percent ?? 0)})</strong></div>`
      },
    },
    legend: {
      orient: 'vertical',
      right: 8,
      top: 'center',
      itemWidth: 8,
      itemHeight: 8,
      icon: 'roundRect',
      textStyle: { color: colors.muted, fontSize: 11 },
      formatter: (name: string) => {
        const item = items.find((entry) => entry.label === name)
        return item ? `${name}  ${formatNumber(item.scheduled)}` : name
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['34%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: colors.surface, borderWidth: 2 },
        label: { show: false },
        labelLine: { show: false },
        data: items.map((item, index) => ({
          name: item.label,
          value: item.scheduled,
          itemStyle: { color: palette[index % palette.length] },
        })),
      },
    ],
  }
}

export function formatMetricValue(
  value: number | null | undefined,
  unit: 'count' | 'percent' | 'currency' | 'seconds',
): string {
  return formatByUnit(value, unit)
}
