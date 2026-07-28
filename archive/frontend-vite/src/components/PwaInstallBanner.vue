<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useI18n } from "../composables/useI18n";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const { t } = useI18n();
const visible = ref(false);
const isIos = ref(false);
const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null);

const DISMISS_KEY = "txbf-pwa-dismiss";

function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator && (navigator as Navigator & { standalone?: boolean }).standalone === true)
  );
}

function onBeforeInstall(event: Event) {
  event.preventDefault();
  deferredPrompt.value = event as BeforeInstallPromptEvent;
  visible.value = true;
}

onMounted(() => {
  if (localStorage.getItem(DISMISS_KEY) || isStandalone()) return;

  isIos.value =
    /iPad|iPhone|iPod/.test(navigator.userAgent) &&
    !(window as Window & { MSStream?: unknown }).MSStream;

  window.addEventListener("beforeinstallprompt", onBeforeInstall);

  if (isIos.value) {
    window.setTimeout(() => {
      if (!isStandalone()) visible.value = true;
    }, 4000);
  }
});

onUnmounted(() => {
  window.removeEventListener("beforeinstallprompt", onBeforeInstall);
});

async function installApp() {
  const prompt = deferredPrompt.value;
  if (!prompt) return;
  await prompt.prompt();
  await prompt.userChoice;
  deferredPrompt.value = null;
  visible.value = false;
}

function dismiss() {
  localStorage.setItem(DISMISS_KEY, "1");
  visible.value = false;
}
</script>

<template>
  <Transition name="sheet-panel">
    <div v-if="visible" class="pwa-install-banner" role="dialog" aria-labelledby="pwa-install-title">
      <div class="pwa-install-inner">
        <img src="/apple-touch-icon.png" alt="" class="pwa-install-icon" width="48" height="48" />
        <div class="min-w-0 flex-1">
          <p id="pwa-install-title" class="text-sm font-semibold text-brand-navy dark:text-white">
            {{ t("pwaInstallTitle") }}
          </p>
          <p class="mt-0.5 text-xs text-brand-navy/60 dark:text-slate-400">
            {{ isIos ? t("pwaIosHint") : t("pwaInstallBody") }}
          </p>
        </div>
        <div class="flex shrink-0 flex-col gap-1.5 sm:flex-row">
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
.pwa-install-banner {
  position: fixed;
  left: 50%;
  bottom: calc(5.75rem + env(safe-area-inset-bottom, 0px));
  z-index: 55;
  width: min(92vw, 24rem);
  transform: translateX(-50%);
  animation: dock-rise 0.5s cubic-bezier(0.34, 1.45, 0.64, 1) both;
}

@media (min-width: 768px) {
  .pwa-install-banner {
    bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
  }
}

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

.dark .pwa-install-inner {
  background: rgba(26, 39, 68, 0.94);
}

.pwa-install-icon {
  border-radius: 0.75rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}
</style>