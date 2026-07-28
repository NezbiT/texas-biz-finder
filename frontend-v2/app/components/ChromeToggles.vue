<script setup lang="ts">
/**
 * Controles de idioma + tema, compartidos por la landing de la suite y el
 * chrome de la app. LocaleToggle y ThemeToggle se auto-importan.
 */
</script>

<template>
  <div class="flex items-center gap-2">
    <slot name="before" />
    <LocaleToggle />
    <ThemeToggle />
    <slot name="after" />
  </div>
</template>
