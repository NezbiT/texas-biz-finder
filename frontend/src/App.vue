<script setup lang="ts">
import { watch } from "vue";
import { useRoute } from "vue-router";
import PwaInstallBanner from "./components/PwaInstallBanner.vue";
import { useI18n } from "./composables/useI18n";
import type { MessageKey } from "./i18n/en";

const route = useRoute();
const { t, locale } = useI18n();

function syncDocumentTitle() {
  const key = (route.meta.titleKey as MessageKey | undefined) ?? "landingDocTitle";
  document.title = t(key);
}

watch([() => route.fullPath, locale], syncDocumentTitle, { immediate: true });
</script>

<template>
  <RouterView />
  <PwaInstallBanner />
</template>
