<script setup lang="ts">
// Banner "Instalar TX BizFinder": aparece cuando el navegador permite instalar
// la PWA (evento beforeinstallprompt) o, en iOS, tras unos segundos con
// instrucciones manuales (iOS no dispara ese evento).

// El evento de Chrome/Edge con los métodos de instalación
type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const { t } = useI18n()
const visible = ref(false)                                    // ¿mostrar el banner?
const isIos = ref(false)                                      // ¿es iPhone/iPad?
const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null)   // evento guardado

// Clave de localStorage: si el usuario dijo "ahora no", no insistir
const DISMISS_KEY = 'txbf-pwa-dismiss'

// ¿Ya está corriendo como app instalada? (entonces no ofrecer instalar)
function isStandalone(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true)
  )
}

// Captura el evento de instalación: se previene el mini-prompt nativo y se
// guarda para dispararlo cuando el usuario toque nuestro botón
function onBeforeInstall(event: Event) {
  event.preventDefault()
  deferredPrompt.value = event as BeforeInstallPromptEvent
  visible.value = true
}

onMounted(() => {
  // No molestar si ya lo descartó o ya está instalada
  if (localStorage.getItem(DISMISS_KEY) || isStandalone()) return

  // Detección de iOS (excluyendo el viejo IE en Windows Phone via MSStream)
  isIos.value =
    /iPad|iPhone|iPod/.test(navigator.userAgent) &&
    !(window as Window & { MSStream?: unknown }).MSStream

  window.addEventListener('beforeinstallprompt', onBeforeInstall)

  // En iOS no existe beforeinstallprompt: mostrar el hint manual tras 4s
  if (isIos.value) {
    window.setTimeout(() => {
      if (!isStandalone()) visible.value = true
    }, 4000)
  }
})

onUnmounted(() => {
  window.removeEventListener('beforeinstallprompt', onBeforeInstall)
})

// Dispara el diálogo nativo de instalación y espera la decisión del usuario
async function installApp() {
  const prompt = deferredPrompt.value
  if (!prompt) return
  await prompt.prompt()
  await prompt.userChoice
  deferredPrompt.value = null
  visible.value = false
}

// "Ahora no": recordar la decisión para no volver a mostrar el banner
function dismiss() {
  localStorage.setItem(DISMISS_KEY, '1')
  visible.value = false
}
</script>

<template>
  <Transition name="sheet-panel">
    <div v-if="visible" class="pwa-install-banner" role="dialog" aria-labelledby="pwa-install-title">
      <div class="pwa-install-inner">
        <!-- Icono de la app (el mismo apple-touch-icon del manifest) -->
        <img src="/apple-touch-icon.png" alt="" class="pwa-install-icon" width="48" height="48" />
        <div class="min-w-0 flex-1">
          <p id="pwa-install-title" class="text-sm font-semibold text-brand-navy dark:text-white">
            {{ t("pwaInstallTitle") }}
          </p>
          <!-- iOS ve instrucciones manuales; el resto, el texto normal -->
          <p class="mt-0.5 text-xs text-brand-navy/60 dark:text-slate-400">
            {{ isIos ? t("pwaIosHint") : t("pwaInstallBody") }}
          </p>
        </div>
        <div class="flex shrink-0 flex-col gap-1.5 sm:flex-row">
          <!-- Botón instalar solo si el navegador nos dio el prompt -->
          <button
            v-if="deferredPrompt"
            type="button"
            class="btn-primary px-3 py-1.5 text-xs"
            @click="installApp"
          >
            {{ t("pwaInstallBtn") }}
          </button>
          <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="dismiss">
            {{ t("pwaInstallDismiss") }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
/* Banner flotante centrado abajo; respeta la safe-area del iPhone y deja
   espacio para el dock móvil (5.75rem) */
.pwa-install-banner {
  position: fixed;
  left: 50%;
  bottom: calc(5.75rem + env(safe-area-inset-bottom, 0px));
  z-index: 55;
  width: min(92vw, 24rem);
  transform: translateX(-50%);
  animation: dock-rise 0.5s cubic-bezier(0.34, 1.45, 0.64, 1) both;
}

/* En desktop no hay dock: el banner baja casi al borde */
@media (min-width: 768px) {
  .pwa-install-banner {
    bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  }
}

/* Tarjeta interior: vidrio esmerilado con borde teal */
.pwa-install-inner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-radius: 1.1rem;
  border: 1px solid rgba(42, 157, 143, 0.35);
  background: rgba(255, 255, 255, 0.92);
  padding: 0.75rem;
  box-shadow: 0 12px 40px -10px rgba(12, 18, 34, 0.35);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

/* Variante oscura del vidrio */
.dark .pwa-install-inner {
  background: rgba(26, 39, 68, 0.94);
}

/* Esquinas y sombra del icono de la app */
.pwa-install-icon {
  border-radius: 0.75rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
</style>
