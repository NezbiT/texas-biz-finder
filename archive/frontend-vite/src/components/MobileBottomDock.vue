<script setup lang="ts">
import { useI18n } from "../composables/useI18n";

defineProps<{
  currentPage: number;
  totalPages: number;
  canPrev: boolean;
  canNext: boolean;
  loading: boolean;
  filteredTotal: number;
}>();

const emit = defineEmits<{
  prev: [];
  next: [];
  search: [];
}>();

const { t } = useI18n();
</script>

<template>
  <nav
    class="mobile-dock"
    :aria-label="t('pageOf', { page: String(currentPage), pages: String(totalPages) })"
  >
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

    <button type="button" class="dock-center" :disabled="loading" @click="emit('search')">
      <span class="dock-page stat-number" :key="currentPage">
        {{ t("pageOf", { page: String(currentPage), pages: String(totalPages) }) }}
      </span>
      <span class="dock-count">{{ filteredTotal.toLocaleString() }} {{ t("dockMatches") }}</span>
    </button>

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