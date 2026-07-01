<script setup lang="ts">
import { onUnmounted, watch } from "vue";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

watch(
  () => props.open,
  (open) => {
    document.body.classList.toggle("sheet-open", open);
  },
  { immediate: true },
);

onUnmounted(() => {
  document.body.classList.remove("sheet-open");
});
</script>

<template>
  <Teleport to="body">
    <Transition name="sheet-backdrop">
      <button
        v-if="open"
        type="button"
        class="sheet-backdrop"
        aria-label="Close"
        @click="emit('close')"
      />
    </Transition>
    <Transition name="sheet-panel">
      <div v-if="open" class="sheet-panel" role="dialog" aria-modal="true">
        <div class="sheet-grabber" aria-hidden="true" />
        <slot />
      </div>
    </Transition>
  </Teleport>
</template>