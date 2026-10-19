<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import Icon from '@/components/Icon.vue'
import { useMetaStore } from '@/stores/meta'

const sidebarOpen = ref(false)
const route = useRoute()
const meta = useMetaStore()

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  },
)

onMounted(() => {
  void meta.load()
})
</script>

<template>
  <a class="skip-link" href="#conteudo">Pular para o conteúdo</a>

  <div class="app-shell">
    <AppSidebar :open="sidebarOpen" @close="sidebarOpen = false" />
    <div
      v-if="sidebarOpen"
      class="sidebar-overlay"
      aria-hidden="true"
      @click="sidebarOpen = false"
    />

    <div class="app-main">
      <AppTopbar :open="sidebarOpen" @toggle="sidebarOpen = !sidebarOpen" />

      <div v-if="meta.error" class="px-4 pt-4 md:px-8">
        <div class="error-banner">
          <Icon name="alert" :size="16" />
          <span class="flex-1">{{ meta.error }}</span>
          <button type="button" class="btn btn-sm" @click="meta.load(true)">
            <Icon name="refresh" :size="13" /> Recarregar
          </button>
        </div>
      </div>

      <main id="conteudo" class="page-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
