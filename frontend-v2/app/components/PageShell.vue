<script setup lang="ts">
// Envoltorio de página: fondo con blobs animadas (.page-shell) + partículas
// opcionales. PageParticles se auto-importa (components.pathPrefix: false).
withDefaults(
  defineProps<{
    /** Muestra las partículas flotantes de marca (por defecto sí). */
    particles?: boolean
  }>(),
  { particles: true },
)
</script>

<template>
  <div class="page-shell">
    <PageParticles v-if="particles" />
    <div class="page-content">
      <slot />
    </div>
  </div>
</template>
