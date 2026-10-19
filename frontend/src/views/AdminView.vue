<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { errorMessage } from '@/api/client'
import { adminApi } from '@/api/endpoints'
import type { Role, SystemStatus, UserAdmin } from '@/api/types'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import Icon from '@/components/Icon.vue'
import LoadingSkeleton from '@/components/LoadingSkeleton.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'
import {
  ETL_STATUS,
  formatDateTime,
  formatNumber,
  roleLabel,
} from '@/utils/format'

const auth = useAuthStore()
const meta = useMetaStore()
const status = ref<SystemStatus | null>(null)
const users = ref<UserAdmin[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const feedback = ref('')
const feedbackError = ref('')
const modalOpen = ref(false)
const saving = ref(false)

const form = reactive({
  email: '',
  full_name: '',
  password: '',
  role: 'RECEPCAO' as Role,
})

const roles: Role[] = ['ADMIN', 'GESTOR', 'COORDENADOR', 'ANALISTA', 'RECEPCAO', 'PROFISSIONAL']

const COUNT_LABELS: Record<string, string> = {
  appointments: 'Agendamentos',
  attendances: 'Atendimentos',
  payments: 'Pagamentos',
  professionals: 'Profissionais',
  units: 'Unidades',
  specialties: 'Especialidades',
  users: 'Usuários',
  quality_issues: 'Problemas de qualidade (todas as execuções)',
}

function countLabel(key: string): string {
  return COUNT_LABELS[key] ?? key.replaceAll('_', ' ')
}

async function load() {
  loading.value = true
  error.value = null
  try {
    status.value = await adminApi.status()
    if (auth.isAdmin) users.value = await adminApi.users()
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void meta.load()
  void load()
})

function openModal() {
  form.email = ''
  form.full_name = ''
  form.password = ''
  form.role = 'RECEPCAO'
  feedbackError.value = ''
  modalOpen.value = true
}

async function createUser() {
  saving.value = true
  feedbackError.value = ''
  try {
    await adminApi.createUser({
      email: form.email,
      full_name: form.full_name,
      password: form.password,
      role: form.role,
    })
    modalOpen.value = false
    feedback.value = `Usuário ${form.email} criado com sucesso.`
    await load()
  } catch (cause) {
    feedbackError.value = errorMessage(cause)
  } finally {
    saving.value = false
  }
}

async function toggleActive(user: UserAdmin) {
  feedback.value = ''
  feedbackError.value = ''
  try {
    await adminApi.updateUser(user.id, { is_active: !user.is_active })
    feedback.value = `Usuário ${user.email} ${user.is_active ? 'desativado' : 'reativado'}.`
    await load()
  } catch (cause) {
    feedbackError.value = errorMessage(cause)
  }
}
</script>

<template>
  <div>
    <PageHeader
      eyebrow="Sistema"
      title="Administração"
      description="Versão, ambiente, estado do banco e do pipeline. Administradores também gerenciam usuários e papéis."
    >
      <template #actions>
        <span class="badge badge--slate">{{ status?.environment ?? '—' }}</span>
        <button type="button" class="btn btn-sm" @click="load">
          <Icon name="refresh" :size="14" /> Atualizar
        </button>
      </template>
    </PageHeader>

    <div v-if="feedback" class="note-box mb-3" role="status">
      <Icon name="check" :size="16" /> {{ feedback }}
    </div>
    <div v-if="feedbackError" class="error-banner mb-3" role="alert">
      <Icon name="alert" :size="16" /> {{ feedbackError }}
    </div>

    <ErrorState v-if="error" :message="error" @retry="load" />

    <div v-else-if="loading && !status" class="flex flex-col gap-3">
      <LoadingSkeleton variant="chart" height="140px" />
      <LoadingSkeleton variant="table" :rows="5" />
    </div>

    <template v-else-if="status">
      <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div class="card p-4">
          <p class="tiny subtle">Aplicação</p>
          <p class="text-[16px] font-bold">{{ status.app_name }}</p>
          <p class="tiny subtle mt-1">versão {{ status.version }} · {{ status.environment }}</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Banco de dados</p>
          <p class="text-[20px] font-bold" :class="status.database === 'ok' ? 'text-[var(--success)]' : 'text-[var(--danger)]'">
            {{ status.database }}
          </p>
          <p class="tiny subtle mt-1">PostgreSQL · fuso {{ status.timezone }}</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Data de referência</p>
          <p class="text-[20px] font-bold">{{ status.demo_today }}</p>
          <p class="tiny subtle mt-1">âncora do conjunto sintético</p>
        </div>
        <div class="card p-4">
          <p class="tiny subtle">Modo demonstração</p>
          <p class="text-[20px] font-bold">{{ status.demo_mode ? 'Ativo' : 'Desativado' }}</p>
          <p class="tiny subtle mt-1">dados fictícios declarados na interface</p>
        </div>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-3">
        <section class="card xl:col-span-2">
          <header class="card-header">
            <div>
              <h2 class="card-title">Contagens do ambiente</h2>
              <p class="card-subtitle">Registros presentes no banco após o pipeline</p>
            </div>
          </header>
          <div class="card-body grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div v-for="(value, key) in status.counts" :key="key" class="note-box flex-col">
              <span class="tiny subtle">{{ countLabel(String(key)) }}</span>
              <span class="text-[18px] font-bold">{{ formatNumber(value) }}</span>
            </div>
          </div>
        </section>

        <section class="card">
          <header class="card-header">
            <div>
              <h2 class="card-title">Última execução</h2>
              <p class="card-subtitle">Pipeline ETL/ELT</p>
            </div>
            <StatusBadge
              v-if="status.pipeline_last_run"
              :label="ETL_STATUS[status.pipeline_last_run.status].label"
              :tone="ETL_STATUS[status.pipeline_last_run.status].tone"
            />
          </header>
          <div class="card-body">
            <template v-if="status.pipeline_last_run">
              <p class="mono text-[11px] subtle">{{ status.pipeline_last_run.run_id }}</p>
              <dl class="mt-3 grid grid-cols-2 gap-2 text-[12px]">
                <div class="note-box flex-col">
                  <dt class="tiny subtle">Lidas</dt>
                  <dd class="text-[16px] font-bold">{{ formatNumber(status.pipeline_last_run.rows_read) }}</dd>
                </div>
                <div class="note-box flex-col">
                  <dt class="tiny subtle">Rejeitadas</dt>
                  <dd class="text-[16px] font-bold">{{ formatNumber(status.pipeline_last_run.rows_rejected) }}</dd>
                </div>
                <div class="note-box flex-col">
                  <dt class="tiny subtle">Semente</dt>
                  <dd class="text-[16px] font-bold">{{ status.pipeline_last_run.source_seed }}</dd>
                </div>
                <div class="note-box flex-col">
                  <dt class="tiny subtle">Âncora</dt>
                  <dd class="text-[13px] font-bold">{{ status.pipeline_last_run.anchor_date }}</dd>
                </div>
              </dl>
              <p class="tiny subtle mt-3">
                Início {{ formatDateTime(status.pipeline_last_run.started_at) }}<br />
                Fim {{ formatDateTime(status.pipeline_last_run.finished_at) }}
              </p>
              <p v-if="status.pipeline_last_run.message" class="note-box mt-3 text-[11.5px]">
                {{ status.pipeline_last_run.message }}
              </p>
            </template>
            <EmptyState v-else title="Pipeline não executado" description="Rode o pipeline para popular o banco." icon="database" />
          </div>
        </section>
      </div>

      <section v-if="auth.isAdmin" class="card mt-4">
        <header class="card-header">
          <div>
            <h2 class="card-title">Usuários e papéis</h2>
            <p class="card-subtitle">A autorização é aplicada no backend, não apenas na interface</p>
          </div>
          <button type="button" class="btn btn-sm btn-primary" @click="openModal">
            <Icon name="plus" :size="14" /> Novo usuário
          </button>
        </header>
        <div class="card-body pt-0">
          <div v-if="users.length" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Papel</th>
                  <th>Profissional</th>
                  <th>Último acesso</th>
                  <th>Status</th>
                  <th class="num">Ações</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in users" :key="user.id">
                  <td>
                    <span class="strong">{{ user.full_name }}</span>
                    <p class="tiny subtle mono">{{ user.email }}</p>
                  </td>
                  <td>{{ roleLabel(user.role) }}</td>
                  <td>{{ user.professional_id ? `#${user.professional_id}` : '—' }}</td>
                  <td>{{ formatDateTime(user.last_login_at) }}</td>
                  <td>
                    <StatusBadge
                      :label="user.is_active ? 'Ativo' : 'Inativo'"
                      :tone="user.is_active ? 'green' : 'slate'"
                    />
                  </td>
                  <td class="num">
                    <button
                      type="button"
                      class="btn btn-sm"
                      :disabled="user.id === auth.user?.id"
                      :title="user.id === auth.user?.id ? 'Não é possível desativar o próprio usuário' : 'Alternar status'"
                      @click="toggleActive(user)"
                    >
                      {{ user.is_active ? 'Desativar' : 'Reativar' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="Nenhum usuário" description="Crie o primeiro usuário de demonstração." icon="users" />
        </div>
      </section>

      <section v-else class="card mt-4">
        <div class="card-body">
          <div class="note-box">
            <Icon name="shield" :size="16" class="mt-0.5" />
            <p>
              A gestão de usuários está disponível apenas para o papel ADMIN. Seu perfil atual é
              {{ auth.user ? roleLabel(auth.user.role) : '—' }}.
            </p>
          </div>
        </div>
      </section>

      <div class="note-box note-box--warn mt-4">
        <Icon name="alert" :size="16" class="mt-0.5" />
        <p>
          O segredo JWT padrão e a senha de demonstração servem apenas para avaliação local. Antes
          de qualquer implantação, revise variáveis de ambiente, HTTPS, política de senhas e
          requisitos da LGPD.
        </p>
      </div>
    </template>

    <ModalDialog
      :open="modalOpen"
      title="Novo usuário"
      description="O usuário poderá acessar o painel conforme o papel escolhido."
      @close="modalOpen = false"
    >
      <div v-if="feedbackError" class="error-banner" role="alert">
        <Icon name="alert" :size="16" /> {{ feedbackError }}
      </div>
      <label class="field">
        <span class="label">Nome completo</span>
        <input v-model="form.full_name" class="input" type="text" placeholder="Nome do usuário" />
      </label>
      <label class="field">
        <span class="label">E-mail</span>
        <input v-model="form.email" class="input" type="email" placeholder="usuario@clinicavida.example" />
      </label>
      <label class="field">
        <span class="label">Senha provisória</span>
        <input v-model="form.password" class="input" type="password" placeholder="Mínimo de 8 caracteres" />
      </label>
      <label class="field">
        <span class="label">Papel</span>
        <select v-model="form.role" class="select">
          <option v-for="role in roles" :key="role" :value="role">{{ roleLabel(role) }}</option>
        </select>
      </label>
      <template #footer>
        <button type="button" class="btn" @click="modalOpen = false">Cancelar</button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="saving || !form.email || !form.full_name || form.password.length < 8"
          @click="createUser"
        >
          {{ saving ? 'Criando…' : 'Criar usuário' }}
        </button>
      </template>
    </ModalDialog>
  </div>
</template>
