<script setup lang="ts">
import { useI18n } from "../composables/useI18n";

const { locale, setLocale, t } = useI18n();
</script>

<template>
  <div
    class="flex items-center rounded-xl border border-brand-navy/10 bg-white p-0.5 dark:border-white/15 dark:bg-white/5"
    role="group"
    :aria-label="locale === 'en' ? 'Language' : 'Idioma'"
  >
    <button
      type="button"
      class="rounded-lg px-2.5 py-1.5 text-xs font-bold transition-all duration-100"
      :class="
        locale === 'en'
          ? 'bg-brand-copper text-white shadow-sm'
          : 'text-brand-navy/60 hover:text-brand-navy dark:text-slate-400 dark:hover:text-slate-200'
      "
      :aria-label="t('langEn')"
      :title="t('langEn')"
      @click="setLocale('en')"
    >
      EN
    </button>
    <button
      type="button"
      class="rounded-lg px-2.5 py-1.5 text-xs font-bold transition-all duration-100"
      :class="
        locale === 'es'
          ? 'bg-brand-copper text-white shadow-sm'
          : 'text-brand-navy/60 hover:text-brand-navy dark:text-slate-400 dark:hover:text-slate-200'
      "
      :aria-label="t('langEs')"
      :title="t('langEs')"
      @click="setLocale('es')"
    >
      ES
    </button>
  </div>
</template>