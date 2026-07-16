<script setup lang="ts">
// Raíz de la app v2: aplica tema/idioma al <html> y monta la página activa.
const { theme } = useTheme()    // 'dark' | 'light' desde cookie (SSR-safe)
const { locale } = useI18n()    // idioma activo (en | es)

// Clase `dark` (activa el dark mode de Tailwind) y atributo lang en el <html>;
// al venir de cookie, el HTML del servidor ya sale con el tema correcto
useHead({
  htmlAttrs: {
    class: computed(() => (theme.value === 'dark' ? 'dark' : '')),
    lang: computed(() => locale.value),
    // color-scheme le dice al navegador qué scrollbars/controles nativos usar
    style: computed(() => `color-scheme: ${theme.value}`),
  },
})
</script>

<template>
  <div>
    <!-- Única página (el dashboard); Nuxt enruta por archivos en app/pages -->
    <NuxtPage />
    <!-- Banner "instalar app" (PWA) — flota sobre todo, solo cliente -->
    <ClientOnly>
      <PwaInstallBanner />
    </ClientOnly>
  </div>
</template>
