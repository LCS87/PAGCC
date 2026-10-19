<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '@/api/client'
import Icon from '@/components/Icon.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const auth = useAuthStore()
const theme = useThemeStore()
const route = useRoute()
const router = useRouter()

const email = ref('gestor@clinicavida.example')
const password = ref('Clinic@2026')
const loading = ref(false)
const error = ref('')
const expired = computed(() => route.query.expired === '1')

const demoUsers = [
  { label: 'Gestor da clínica', email: 'gestor@clinicavida.example' },
  { label: 'Administrador', email: 'admin@clinicavida.example' },
  { label: 'Coordenação', email: 'coordenador@clinicavida.example' },
  { label: 'Profissional', email: 'profissional@clinicavida.example' },
  { label: 'Recepção', email: 'recepcao@clinicavida.example' },
]

function fill(userEmail: string) {
  email.value = userEmail
  password.value = 'Clinic@2026'
  error.value = ''
}

async function submit() {
  error.value = ''
  if (!email.value.trim() || !password.value) {
    error.value = 'Informe e-mail e senha.'
    return
  }
  loading.value = true
  try {
    await auth.login(email.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    await router.push(redirect)
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-shell">
    <aside class="login-aside">
      <div class="flex items-center gap-3">
        <span class="brand-mark" style="width: 44px; height: 44px">
          <Icon name="activity" :size="24" />
        </span>
        <div>
          <p class="text-[15px] font-bold text-slate-100">Clinic Analytics</p>
          <p class="text-[10.5px] uppercase tracking-[0.16em] text-slate-400">
            PAGCC · portfólio técnico
          </p>
        </div>
      </div>

      <div class="max-w-[520px]">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-teal-300">
          Gestão orientada por dados
        </p>
        <h1 class="text-[34px] font-bold leading-[1.12] tracking-[-0.035em] text-white">
          Transforme a operação da clínica em decisões priorizadas.
        </h1>
        <p class="mt-4 text-[14px] leading-relaxed text-slate-300">
          Agenda, faltas, ocupação, receita simulada e qualidade dos dados em um painel único —
          com fórmulas documentadas e rastreabilidade do pipeline.
        </p>

        <div class="mt-8 grid max-w-[440px] grid-cols-2 gap-3">
          <div class="rounded-xl border border-white/10 bg-white/5 p-3.5">
            <p class="text-[10px] uppercase tracking-wider text-slate-400">Métricas do MVP</p>
            <p class="mt-1 text-2xl font-bold text-white">11</p>
            <p class="text-[11px] text-slate-400">com fórmula e base de cálculo</p>
          </div>
          <div class="rounded-xl border border-white/10 bg-white/5 p-3.5">
            <p class="text-[10px] uppercase tracking-wider text-slate-400">Histórico sintético</p>
            <p class="mt-1 text-2xl font-bold text-white">18 meses</p>
            <p class="text-[11px] text-slate-400">semente fixa e reproduzível</p>
          </div>
        </div>

        <ul class="mt-8 space-y-3 text-[13px] text-slate-300">
          <li class="flex items-start gap-2.5">
            <Icon name="check" :size="16" class="mt-0.5 text-teal-300" />
            Camadas raw, staging, curada e analytics com testes de qualidade.
          </li>
          <li class="flex items-start gap-2.5">
            <Icon name="check" :size="16" class="mt-0.5 text-teal-300" />
            API FastAPI documentada, PostgreSQL, Docker Compose e CI.
          </li>
          <li class="flex items-start gap-2.5">
            <Icon name="check" :size="16" class="mt-0.5 text-teal-300" />
            Tema claro/escuro, estados de erro e acessibilidade por teclado.
          </li>
        </ul>
      </div>

      <p class="max-w-[460px] text-[11px] leading-relaxed text-slate-500">
        Ambiente acadêmico de demonstração. Todos os pacientes, profissionais e valores são
        fictícios. Não utilize para decisões clínicas.
      </p>
    </aside>

    <div class="flex min-h-screen items-center justify-center p-5 sm:p-8">
      <div class="login-card">
        <div class="mb-6 flex items-start justify-between gap-3">
          <div>
            <p class="page-eyebrow">Acesso restrito</p>
            <h2 class="text-[24px] font-bold tracking-[-0.03em]">Entrar no painel</h2>
            <p class="mt-1 text-[13px] text-[var(--muted)]">
              Use um usuário de demonstração para explorar os perfis.
            </p>
          </div>
          <button
            type="button"
            class="btn btn-ghost btn-icon"
            :aria-label="theme.mode === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'"
            @click="theme.toggle()"
          >
            <Icon :name="theme.mode === 'dark' ? 'sun' : 'moon'" :size="18" />
          </button>
        </div>

        <div v-if="expired" class="note-box note-box--warn mb-4">
          <Icon name="clock" :size="16" />
          Sua sessão expirou. Entre novamente para continuar.
        </div>

        <div v-if="error" class="error-banner mb-4" role="alert">
          <Icon name="alert" :size="16" />
          <span>{{ error }}</span>
        </div>

        <form class="flex flex-col gap-4" @submit.prevent="submit">
          <label class="field">
            <span class="label">E-mail</span>
            <input
              v-model="email"
              class="input"
              type="email"
              autocomplete="username"
              placeholder="voce@clinicavida.example"
              required
            />
          </label>

          <label class="field">
            <span class="label">Senha</span>
            <input
              v-model="password"
              class="input"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
              minlength="6"
              required
            />
          </label>

          <button class="btn btn-primary mt-1 w-full" type="submit" :disabled="loading">
            <Icon v-if="!loading" name="logout" :size="15" />
            <span v-if="loading" class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            {{ loading ? 'Entrando…' : 'Entrar' }}
          </button>
        </form>

        <div class="mt-5 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-3">
          <p class="mb-1.5 text-[10.5px] font-semibold uppercase tracking-wider text-[var(--muted)]">
            Usuários de demonstração · senha Clinic@2026
          </p>
          <div class="flex flex-col">
            <button
              v-for="user in demoUsers"
              :key="user.email"
              type="button"
              class="demo-user"
              @click="fill(user.email)"
            >
              <span>{{ user.label }}</span>
              <span class="mono text-[10.5px]">{{ user.email }}</span>
            </button>
          </div>
        </div>

        <p class="mt-5 text-center text-[10.5px] leading-relaxed text-[var(--subtle)]">
          Projeto acadêmico com dados sintéticos. Nenhuma informação clínica real é armazenada.
        </p>
      </div>
    </div>
  </div>
</template>
