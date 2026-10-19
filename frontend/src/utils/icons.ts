/** Conjunto de ícones SVG (stroke) usado na interface. */

export type IconName =
  | 'dashboard'
  | 'calendar'
  | 'users'
  | 'activity'
  | 'chart'
  | 'shield'
  | 'settings'
  | 'sun'
  | 'moon'
  | 'menu'
  | 'close'
  | 'logout'
  | 'arrow-up'
  | 'arrow-down'
  | 'search'
  | 'download'
  | 'alert'
  | 'info'
  | 'check'
  | 'clock'
  | 'chevron-left'
  | 'chevron-right'
  | 'filter'
  | 'database'
  | 'refresh'
  | 'plus'
  | 'external'
  | 'file'
  | 'sparkles'
  | 'wallet'
  | 'clipboard'
  | 'list'

export const ICONS: Record<IconName, string[]> = {
  dashboard: ['M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z'],
  calendar: [
    'M8 2v4M16 2v4M3 10h18',
    'M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  ],
  users: [
    'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    'M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  ],
  activity: ['M22 12h-4l-3 9L9 3l-3 9H2'],
  chart: ['M3 3v18h18', 'M7 15l4-4 3 3 5-6'],
  shield: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'm9 12 2 2 4-4'],
  settings: [
    'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    'M12 2v3M12 19v3M4.9 4.9 7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1',
  ],
  sun: [
    'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
    'M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42',
  ],
  moon: ['M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'],
  menu: ['M3 6h18M3 12h18M3 18h18'],
  close: ['M18 6 6 18M6 6l12 12'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9'],
  'arrow-up': ['M12 19V5M5 12l7-7 7 7'],
  'arrow-down': ['M12 5v14M19 12l-7 7-7-7'],
  search: ['M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.35-4.35'],
  download: [
    'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4',
    'M7 10l5 5 5-5M12 15V3',
  ],
  alert: [
    'M12 9v4M12 17h.01',
    'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z',
  ],
  info: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01'],
  check: ['M20 6 9 17l-5-5'],
  clock: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2'],
  'chevron-left': ['m15 18-6-6 6-6'],
  'chevron-right': ['m9 18 6-6-6-6'],
  filter: ['M22 3H2l8 9.46V19l4 2v-8.54L22 3z'],
  database: [
    'M12 8c4.97 0 9-1.34 9-3s-4.03-3-9-3-9 1.34-9 3 4.03 3 9 3z',
    'M3 5v6c0 1.66 4.03 3 9 3s9-1.34 9-3V5M3 11v6c0 1.66 4.03 3 9 3s9-1.34 9-3v-6',
  ],
  refresh: [
    'M23 4v6h-6M1 20v-6h6',
    'M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15',
  ],
  plus: ['M12 5v14M5 12h14'],
  external: ['M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3'],
  file: [
    'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z',
    'M14 2v6h6M16 13H8M16 17H8M10 9H8',
  ],
  sparkles: [
    'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z',
    'M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z',
  ],
  wallet: [
    'M21 12V7H5a2 2 0 0 1 0-4h14v4',
    'M3 5v14a2 2 0 0 0 2 2h16v-5M18 12a2 2 0 0 0 0 4h4v-4z',
  ],
  clipboard: [
    'M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2',
    'M9 2h6a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1z',
  ],
  list: ['M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01'],
}
