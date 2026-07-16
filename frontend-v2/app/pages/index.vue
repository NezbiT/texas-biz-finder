<script setup lang="ts">
// Página principal (y única) de la v2: el dashboard de leads.
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
