<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

import Icon from './Icon.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
  }>(),
  { description: '' },
)

const emit = defineEmits<{ close: [] }>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') emit('close')
}

watch(
  () => props.open,
  (open) => {
    if (open) document.addEventListener('keydown', onKeydown)
    else document.removeEventListener('keydown', onKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-backdrop"
      role="presentation"
      @click.self="emit('close')"
    >
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <header class="modal-header">
          <div>
            <h2 class="card-title">{{ title }}</h2>
            <p v-if="description" class="card-subtitle">{{ description }}</p>
          </div>
          <button
            type="button"
            class="btn btn-ghost btn-icon btn-sm"
            aria-label="Fechar"
            @click="emit('close')"
          >
            <Icon name="close" :size="16" />
          </button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
        <footer v-if="$slots.footer" class="modal-footer">
          <slot name="footer" />
        </footer>
      </section>
    </div>
  </Teleport>
</template>
