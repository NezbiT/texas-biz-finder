<script setup lang="ts">
// El dashboard de leads. Era la ruta BIZ_APP_PATH del router v1 (por defecto
// /app); si NUXT_PUBLIC_SUITE_BIZ_APP_PATH apunta a otra ruta, el hook
// pages:extend de nuxt.config añade ese path a esta misma página.
// La página es fina a propósito: SEO aquí, lógica en <LeadsDashboard>.
const { t } = useI18n()

// Metadatos SEO — la razón principal de migrar a Nuxt: con SSR los buscadores
// ven título, descripción y contenido real (la SPA v1 servía HTML vacío)
useSeoMeta({
  title: () => `${t('appName')} — ${t('tagline')}`,
  description:
    'Search 500K+ Texas small businesses: websites, social presence, TABC alcohol sales. Find leads without a modern website.',
  ogTitle: () => `${t('appName')} — ${t('tagline')}`,
  ogDescription:
    'Search 500K+ Texas small businesses: websites, social presence, TABC alcohol sales.',
})
</script>

<template>
  <LeadsDashboard />
</template>
