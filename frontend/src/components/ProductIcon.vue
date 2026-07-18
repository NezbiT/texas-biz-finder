<script setup lang="ts">
import type { SuiteProductId } from "../config/suite";

defineProps<{
  icon: SuiteProductId;
  class?: string;
}>();
</script>

<template>
  <!-- biz: magnifier -->
  <svg
    v-if="icon === 'biz'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" stroke-linecap="round" />
  </svg>
  <!-- radar: concentric + sweep -->
  <svg
    v-else-if="icon === 'radar'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <path d="M12 12l6-4" stroke-linecap="round" />
  </svg>
  <!-- channel: waves + monitor -->
  <svg
    v-else-if="icon === 'channel'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <path d="M4 14c2-3 4-4 8-4s6 1 8 4" stroke-linecap="round" />
    <path d="M4 18c2.5-2 5-3 8-3s5.5 1 8 3" stroke-linecap="round" opacity="0.6" />
    <circle cx="12" cy="8" r="2" fill="currentColor" stroke="none" />
  </svg>
  <!-- sentinel: shield check -->
  <svg
    v-else-if="icon === 'sentinel'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <path d="M12 3l8 4v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V7l8-4z" stroke-linejoin="round" />
    <path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
  <!-- flood: water drop + waves -->
  <svg
    v-else-if="icon === 'flood'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <path d="M12 3c-1.2 4-5 7-5 11a5 5 0 0 0 10 0c0-4-3.8-7-5-11z" stroke-linejoin="round" />
    <path d="M5 20c1.5-1 3-1.5 5-1.5s3.5.5 5 1.5 3 1.5 4 1.5" stroke-linecap="round" opacity="0.7" />
  </svg>
  <!-- power: bolt -->
  <svg
    v-else-if="icon === 'power'"
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <path d="M13 2L4 14h7l-1 8 10-14h-7l1-6z" stroke-linejoin="round" />
  </svg>
  <!-- map: pin / hub -->
  <svg
    v-else
    class="h-5 w-5"
    :class="$props.class"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="2.5" fill="currentColor" stroke="none" />
    <path d="M12 4v2.5M12 17.5V20M4 12h2.5M17.5 12H20" stroke-linecap="round" />
  </svg>
</template>
