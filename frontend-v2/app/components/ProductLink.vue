<script setup lang="ts">
/**
 * NuxtLink interno (/app) vs <a> a otro path de la suite (full page, same tab)
 * vs enlace externo real (opcional nueva pestaña).
 */
import type { SuiteProduct } from '~/config/suite'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  product: Pick<SuiteProduct, 'href' | 'external' | 'sameOrigin'>
}>()

/** Suite siblings en txbizfinder.com/xxx → same tab full navigation. */
const openInNewTab = computed(
  () => props.product.external && props.product.sameOrigin === false,
)
</script>

<template>
  <NuxtLink v-if="!product.external" :to="product.href" v-bind="$attrs">
    <slot />
  </NuxtLink>
  <a
    v-else
    :href="product.href"
    :target="openInNewTab ? '_blank' : undefined"
    :rel="openInNewTab ? 'noopener noreferrer' : undefined"
    v-bind="$attrs"
  >
    <slot />
  </a>
</template>
