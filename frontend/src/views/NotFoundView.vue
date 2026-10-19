<script setup lang="ts">
import { RouterLink } from 'vue-router'

import Icon from '@/components/Icon.vue'
</script>

<template>
  <div class="flex min-h-screen items-center justify-center p-6">
    <div class="card w-full max-w-md p-8 text-center">
      <div class="state-icon mx-auto" style="width: 52px; height: 52px">
        <Icon name="search" :size="24" />
      </div>
      <p class="mt-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
        Erro 404
      </p>
      <h1 class="mt-1 text-[24px] font-bold tracking-[-0.03em]">Página não encontrada</h1>
      <p class="mt-2 text-[13px] text-[var(--muted)]">
        O endereço acessado não existe ou foi movido. Volte ao dashboard para continuar.
      </p>
      <RouterLink to="/" class="btn btn-primary mt-5">
        <Icon name="dashboard" :size="15" /> Ir para o dashboard
      </RouterLink>
    </div>
  </div>
</template>
