<script setup lang="ts">
// Bloque que aparece al entrar en pantalla. El observer vive en useReveal y
// solo corre en cliente, así que en SSR esto renderiza sin la clase `is-in`.
withDefaults(
  defineProps<{
    delayClass?: string
  }>(),
  { delayClass: '' },
)

const { el, visible } = useReveal()
</script>

<template>
  <div ref="el" class="land-wow__reveal" :class="[delayClass, { 'is-in': visible }]">
    <slot />
  </div>
</template>
