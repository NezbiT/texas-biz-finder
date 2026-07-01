<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "../composables/useI18n";

const { locale, setLocale, t } = useI18n();

const pillStyle = computed(() => ({
  left: locale.value === "en" ? "2px" : "calc(50% - 2px)",
  width: "calc(50% - 2px)",
}));
</script>

<template>
  <div class="locale-toggle" role="group" :aria-label="locale === 'en' ? 'Language' : 'Idioma'">
    <span class="locale-pill" :style="pillStyle" aria-hidden="true" />
    <button
      type="button"
      class="locale-btn"
      :class="
        locale === 'en'
          ? 'text-white'
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
      class="locale-btn"
      :class="
        locale === 'es'
          ? 'text-white'
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