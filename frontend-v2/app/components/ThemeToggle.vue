<script setup lang="ts">
// Botón de tema: muestra un sol en modo oscuro (te llevará a claro) y una
// luna en modo claro. La transición cruza los iconos con fade.
const { theme, toggleTheme } = useTheme()
const { t } = useI18n()
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="theme === 'dark' ? t('themeLight') : t('themeDark')"
    :title="theme === 'dark' ? t('themeLight') : t('themeDark')"
    @click="toggleTheme"
  >
    <!-- mode=out-in: el icono saliente termina su animación antes de entrar el nuevo -->
    <Transition name="theme-icon" mode="out-in">
      <!-- Sol (visible en modo oscuro) -->
      <svg
        v-if="theme === 'dark'"
        key="sun"
        class="h-5 w-5 text-brand-copper-light"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
      >
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" stroke-linecap="round" />
      </svg>
      <!-- Luna (visible en modo claro) -->
      <svg
        v-else
        key="moon"
        class="h-5 w-5 text-brand-teal"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
      >
        <path
          d="M21 14.5A8.5 8.5 0 1 1 9.5 3a6.8 6.8 0 0 0 11.5 11.5Z"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </Transition>
  </button>
</template>
