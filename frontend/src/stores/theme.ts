import { ref } from 'vue'
import { defineStore } from 'pinia'

export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'pagcc.theme'

function initialMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(initialMode())

  function apply() {
    const root = document.documentElement
    root.classList.toggle('dark', mode.value === 'dark')
    root.dataset.theme = mode.value
    localStorage.setItem(STORAGE_KEY, mode.value)
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', mode.value === 'dark' ? '#070f1c' : '#f3f6fb')
  }

  function toggle() {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
    apply()
  }

  function setMode(value: ThemeMode) {
    mode.value = value
    apply()
  }

  apply()

  return { mode, toggle, setMode, apply }
})
