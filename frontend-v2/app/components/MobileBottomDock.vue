<script setup lang="ts">
// Dock inferior fijo para móvil: ← página anterior | contador | página siguiente →.
// El botón central hace scroll al panel de búsqueda (emit 'search').
defineProps<{
  currentPage: number     // página actual
  totalPages: number      // total de páginas
  canPrev: boolean        // ¿se puede retroceder?
  canNext: boolean        // ¿se puede avanzar?
  loading: boolean        // deshabilita los botones mientras carga
  filteredTotal: number   // total de resultados (para el contador)
}>()

// Eventos hacia el dashboard padre
const emit = defineEmits<{
  prev: []
  next: []
  search: []
}>()

const { t } = useI18n()
</script>

<template>
  <nav
    class="mobile-dock"
    :aria-label="t('pageOf', { page: String(currentPage), pages: String(totalPages) })"
  >
    <!-- ← Página anterior -->
    <button
      type="button"
      class="dock-btn"
      :disabled="!canPrev || loading"
      :aria-label="t('prevPage')"
      @click="emit('prev')"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <path d="M15 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <!-- Centro: "Página X de Y" + total de coincidencias; toca para ir a la búsqueda -->
    <button type="button" class="dock-center" :disabled="loading" @click="emit('search')">
      <span class="dock-page stat-number" :key="currentPage">
        {{ t("pageOf", { page: String(currentPage), pages: String(totalPages) }) }}
      </span>
      <span class="dock-count">{{ filteredTotal.toLocaleString() }} {{ t("dockMatches") }}</span>
    </button>

    <!-- Página siguiente → -->
    <button
      type="button"
      class="dock-btn"
      :disabled="!canNext || loading"
      :aria-label="t('nextPage')"
      @click="emit('next')"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
        <path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>
  </nav>
</template>
