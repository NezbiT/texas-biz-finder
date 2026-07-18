<script setup lang="ts">
import { useReveal } from "../composables/useReveal";

withDefaults(
  defineProps<{
    delayClass?: string;
  }>(),
  { delayClass: "" },
);

const { el, visible } = useReveal();
</script>

<template>
  <div ref="el" class="land-wow__reveal" :class="[delayClass, { 'is-in': visible }]">
    <slot />
  </div>
</template>
