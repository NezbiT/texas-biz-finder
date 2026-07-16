<script setup lang="ts">
// Interruptor EN/ES con "píldora" deslizante que marca el idioma activo.
// v2: usa el i18n de Nuxt (setLocale persiste en la cookie txbf_locale).
const { locale, setLocale, t } = useI18n()

// Posición/ancho de la píldora según el idioma activo (izquierda=EN, derecha=ES)
const pillStyle = computed(() => ({
  left: locale.value === 'en' ? '2px' : 'calc(50% - 2px)',
  width: 'calc(50% - 2px)',
}))
</script>

<template>
  <div class="locale-toggle" role="group" :aria-label="locale === 'en' ? 'Language' : 'Idioma'">
    <!-- La píldora animada de fondo (decorativa) -->
    <span class="locale-pill" :style="pillStyle" aria-hidden="true" />
    <!-- Botón EN: blanco si activo, gris si no -->
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
    <!-- Botón ES -->
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
