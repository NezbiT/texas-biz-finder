<script setup lang="ts">
// "Bottom sheet" móvil (panel que sube desde abajo) para el research de sitios.
// Bloquea el scroll del body mientras está abierto y lo restaura al cerrar.
const props = defineProps<{
  open: boolean                              // ¿mostrar la hoja?
  touchStart?: (event: TouchEvent) => void   // handlers de swipe del padre
  touchEnd?: (event: TouchEvent) => void
}>()

const emit = defineEmits<{
  close: []
}>()

const isMobileViewport = ref(false)   // ¿estamos en viewport móvil (<768px)?
let savedScrollY = 0                  // scroll a restaurar al cerrar
// v2/SSR: el MediaQueryList se crea en onMounted (en la v1 estaba a nivel de
// módulo y window no existe en el servidor — habría reventado el SSR)
let mq: MediaQueryList | null = null

// Sincroniza el flag con el media query actual
function syncViewport() {
  if (mq) isMobileViewport.value = mq.matches
}

// Congela el body (position:fixed vía clase sheet-open) recordando el scroll
function lockBody() {
  if (!isMobileViewport.value) return
  savedScrollY = window.scrollY
  document.body.style.top = `-${savedScrollY}px`
  document.body.classList.add('sheet-open')
}

// Descongela el body y vuelve al scroll donde estaba
function unlockBody() {
  document.body.classList.remove('sheet-open')
  document.body.style.top = ''
  if (savedScrollY > 0) {
    window.scrollTo(0, savedScrollY)
    savedScrollY = 0
  }
}

// Abrir → bloquear; cerrar → desbloquear (sin immediate: en SSR no hay body)
watch(
  () => props.open,
  (open) => {
    if (open) lockBody()
    else unlockBody()
  },
)

// Si el viewport cambia (rotación/resize) ajustar el bloqueo en consecuencia
watch(isMobileViewport, (mobile) => {
  if (!mobile) unlockBody()
  else if (props.open) lockBody()
})

onMounted(() => {
  // Registrar el media query ya en el navegador
  mq = window.matchMedia('(max-width: 767px)')
  syncViewport()
  mq.addEventListener('change', syncViewport)
  if (props.open) lockBody()   // por si montó ya abierta
})

onUnmounted(() => {
  mq?.removeEventListener('change', syncViewport)
  unlockBody()   // nunca dejar el body bloqueado al desmontar
})
</script>

<template>
  <!-- Teleport: la hoja se monta directo en <body>, por encima de todo -->
  <Teleport to="body">
    <!-- Fondo oscurecido clickeable (cierra la hoja) -->
    <Transition name="sheet-backdrop">
      <button
        v-if="open"
        type="button"
        class="sheet-backdrop"
        aria-label="Close"
        @click="emit('close')"
      />
    </Transition>
    <!-- El panel que sube desde abajo; propaga los gestos de swipe -->
    <Transition name="sheet-panel">
      <div
        v-if="open"
        class="sheet-panel"
        role="dialog"
        aria-modal="true"
        @touchstart.passive="touchStart"
        @touchend.passive="touchEnd"
      >
        <!-- Barrita superior tipo iOS (indica que se puede arrastrar) -->
        <div class="sheet-grabber" aria-hidden="true" />
        <slot />
      </div>
    </Transition>
  </Teleport>
</template>
