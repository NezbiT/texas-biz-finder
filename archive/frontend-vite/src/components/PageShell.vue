<script setup lang="ts">
import PageParticles from "./PageParticles.vue";

withDefaults(
  defineProps<{
    /** Show floating brand particles (default true). */
    particles?: boolean;
  }>(),
  { particles: true },
);
</script>

<template>
  <div class="page-shell">
    <PageParticles v-if="particles" />
    <div class="page-content">
      <slot />
    </div>
  </div>
</template>
