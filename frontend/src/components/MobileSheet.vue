<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";

const props = defineProps<{
  open: boolean;
  touchStart?: (event: TouchEvent) => void;
  touchEnd?: (event: TouchEvent) => void;
}>();

const emit = defineEmits<{
  close: [];
}>();

const isMobileViewport = ref(false);
let savedScrollY = 0;
const mq = window.matchMedia("(max-width: 767px)");

function syncViewport() {
  isMobileViewport.value = mq.matches;
}

function lockBody() {
  if (!isMobileViewport.value) return;
  savedScrollY = window.scrollY;
  document.body.style.top = `-${savedScrollY}px`;
  document.body.classList.add("sheet-open");
}

function unlockBody() {
  document.body.classList.remove("sheet-open");
  document.body.style.top = "";
  if (savedScrollY > 0) {
    window.scrollTo(0, savedScrollY);
    savedScrollY = 0;
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) lockBody();
    else unlockBody();
  },
  { immediate: true },
);

watch(isMobileViewport, (mobile) => {
  if (!mobile) unlockBody();
  else if (props.open) lockBody();
});

onMounted(() => {
  syncViewport();
  mq.addEventListener("change", syncViewport);
});

onUnmounted(() => {
  mq.removeEventListener("change", syncViewport);
  unlockBody();
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
      <div
        v-if="open"
        class="sheet-panel"
        role="dialog"
        aria-modal="true"
        @touchstart.passive="touchStart"
        @touchend.passive="touchEnd"
      >
        <div class="sheet-grabber" aria-hidden="true" />
        <slot />
      </div>
    </Transition>
  </Teleport>
</template>