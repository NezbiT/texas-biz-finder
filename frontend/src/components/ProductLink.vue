<script setup lang="ts">
/**
 * Internal RouterLink vs external <a> — one place for suite CTAs.
 * Forwards attrs/listeners so tilt / analytics stay on the host.
 */
import { RouterLink } from "vue-router";
import type { SuiteProduct } from "../config/suite";

defineProps<{
  product: Pick<SuiteProduct, "href" | "external">;
  class?: string;
}>();
</script>

<template>
  <RouterLink
    v-if="!product.external"
    :to="product.href"
    :class="$props.class"
    v-bind="$attrs"
  >
    <slot />
  </RouterLink>
  <a
    v-else
    :href="product.href"
    target="_blank"
    rel="noopener noreferrer"
    :class="$props.class"
    v-bind="$attrs"
  >
    <slot />
  </a>
</template>
