<script setup lang="ts">
import { SUITE_CREATOR, suiteProductNameStrip } from '~/config/suite'

const { t } = useI18n()
const productNames = suiteProductNameStrip()
const creator = SUITE_CREATOR
</script>

<template>
  <footer class="border-t border-brand-navy/8 py-10 dark:border-white/8">
    <div
      class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6"
    >
      <BrandMark :title="t('suiteName')" :subtitle="t('suiteFooterTag')" size="sm" />
      <div class="text-center sm:text-right">
        <p class="font-mono text-xs text-brand-navy/45 dark:text-slate-500">
          {{ productNames }}
        </p>
        <p class="mt-1.5 text-xs text-brand-navy/55 dark:text-slate-400">
          {{ t('suiteCreatedBy') }}
          <a
            :href="creator.url"
            class="font-semibold text-brand-navy underline-offset-2 hover:underline dark:text-slate-200"
            target="_blank"
            rel="noopener noreferrer"
          >{{ t('suiteCreatorName') }}</a>
          ·
          <a
            :href="creator.url"
            class="underline-offset-2 hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >{{ creator.host }}</a>
        </p>
      </div>
    </div>
  </footer>
</template>
