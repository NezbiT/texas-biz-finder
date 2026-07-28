<script setup lang="ts">
// Portada: la landing de la suite TxBizFinder Intelligence.
// En la v1 esto era la ruta "/" del router; aquí lo da el file-based routing.
const { t } = useI18n()

useSeoMeta({
  title: () => `${t('suiteName')} — ${t('suiteHeroTitle')}`,
  description: () => t('suiteHeroBody'),
  ogTitle: () => `${t('suiteName')} — ${t('suiteHeroTitle')}`,
  ogDescription: () => t('suiteHeroBody'),
})
</script>

<template>
  <SuiteLanding />
</template>
