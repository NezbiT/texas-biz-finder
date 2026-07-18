<script setup lang="ts">
import type { SuiteProduct } from "../config/suite";
import { useI18n } from "../composables/useI18n";
import ProductIcon from "./ProductIcon.vue";
import ProductLink from "./ProductLink.vue";

defineProps<{
  product: SuiteProduct;
  index?: number;
}>();

const { t } = useI18n();
</script>

<template>
  <article
    class="group relative overflow-hidden rounded-2xl border border-brand-navy/10 bg-white/70 p-6 shadow-card transition dark:border-white/10 dark:bg-brand-navy-mid/40"
    :class="product.ring"
    :style="index != null ? { animationDelay: `${index * 60}ms` } : undefined"
  >
    <div
      class="pointer-events-none absolute inset-0 bg-gradient-to-br opacity-80"
      :class="product.accent"
    />
    <div class="relative">
      <div class="mb-4 flex items-start justify-between gap-3">
        <div
          class="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-navy text-white shadow-sm dark:bg-white/10"
        >
          <ProductIcon :icon="product.id" />
        </div>
        <span
          class="rounded-full border border-brand-navy/10 bg-white/70 px-2.5 py-0.5 font-mono text-[0.65rem] text-brand-navy/60 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
        >
          {{ product.domain }}
        </span>
      </div>

      <h3 class="font-display text-xl font-bold text-brand-navy dark:text-white">
        {{ t(product.nameKey) }}
      </h3>
      <p class="mt-2 min-h-[3.25rem] text-sm leading-relaxed text-brand-navy/70 dark:text-slate-300">
        {{ t(product.blurbKey) }}
      </p>

      <div class="mt-5">
        <ProductLink
          :product="product"
          class="inline-flex items-center gap-2 text-sm font-semibold text-brand-teal transition group-hover:gap-3 dark:text-brand-teal-light"
        >
          {{ t(product.ctaKey) }}
          <span aria-hidden="true">{{ product.external ? "↗" : "→" }}</span>
        </ProductLink>
      </div>
    </div>
  </article>
</template>
