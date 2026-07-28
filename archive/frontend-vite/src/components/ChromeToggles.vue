<script setup lang="ts">
/**
 * Shared locale + theme controls used by suite landing and app chrome.
 */
import LocaleToggle from "./LocaleToggle.vue";
import ThemeToggle from "./ThemeToggle.vue";
</script>

<template>
  <div class="flex items-center gap-2">
    <slot name="before" />
    <LocaleToggle />
    <ThemeToggle />
    <slot name="after" />
  </div>
</template>
