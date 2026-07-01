<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import AppLogo from "./AppLogo.vue";
import MobileBottomDock from "./MobileBottomDock.vue";
import MobileSheet from "./MobileSheet.vue";
import PageParticles from "./PageParticles.vue";
import LocaleToggle from "./LocaleToggle.vue";
import ThemeToggle from "./ThemeToggle.vue";
import WebsiteResearchPanel from "./WebsiteResearchPanel.vue";
import { useI18n } from "../composables/useI18n";
import { useScrollCompact } from "../composables/useScrollCompact";
import { useTouchSwipe } from "../composables/useTouchSwipe";
import type { LeadSearchPage } from "../types/lead-search";
import type { Lead } from "../types/lead";

const { t } = useI18n();
const API_KEY = import.meta.env.VITE_ADMIN_API_KEY ?? "admin-dev-key-change-me";
const PAGE_SIZE = 50;

const leads = ref<Lead[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const searchQuery = ref("");
const locationFilter = ref("");
const radiusMiles = ref(25);
const useRadiusSearch = ref(false);
const industryFilter = ref("");
const qualifiedOnly = ref(true);
const alcoholOnly = ref(false);
const dbStats = ref({ total: 0, qualified: 0, small_business: 0, sells_alcohol: 0 });
const filteredTotal = ref(0);
const currentPage = ref(1);
const totalPages = ref(1);
const researchLeadId = ref<number | null>(null);

const qualifiedInView = computed(
  () => leads.value.filter((lead) => lead.is_qualified).length,
);

const radiusLabel = computed(() => `${radiusMiles.value} mi`);

const rangeFrom = computed(() =>
  filteredTotal.value === 0 ? 0 : (currentPage.value - 1) * PAGE_SIZE + 1,
);

const rangeTo = computed(() =>
  filteredTotal.value === 0
    ? 0
    : Math.min(currentPage.value * PAGE_SIZE, filteredTotal.value),
);

const resultsSummary = computed(() =>
  t("resultsSummary", {
    from: String(rangeFrom.value),
    to: String(rangeTo.value),
    filtered: String(filteredTotal.value),
    total: String(dbStats.value.total),
  }),
);

const canGoPrev = computed(() => currentPage.value > 1);
const canGoNext = computed(() => currentPage.value < totalPages.value);

const { compact: headerCompact } = useScrollCompact(56);

const activeResearchLead = computed(
  () => leads.value.find((lead) => lead.id === researchLeadId.value) ?? null,
);

const swipeEnabled = computed(() => filteredTotal.value > PAGE_SIZE && !loading.value);

const showScrollTop = ref(false);

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function scrollToSearch() {
  document.getElementById("search-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function appendLocationParams(params: URLSearchParams): void {
  const location = locationFilter.value.trim();
  if (!location) return;

  if (/^\d{5}$/.test(location)) {
    params.set("zip_code", location);
  } else {
    params.set("city", location);
  }
  if (useRadiusSearch.value) {
    params.set("radius_miles", String(radiusMiles.value));
  }
}

function buildSearchParams(forExport = false): URLSearchParams {
  const params = new URLSearchParams();
  if (searchQuery.value) params.set("q", searchQuery.value);
  appendLocationParams(params);
  if (industryFilter.value) params.set("industry", industryFilter.value);
  params.set("qualified_only", String(qualifiedOnly.value));
  params.set("small_business_only", "true");
  if (alcoholOnly.value) params.set("sells_alcohol_only", "true");
  if (forExport) {
    params.set("limit", "5000");
    params.set("offset", "0");
  } else {
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String((currentPage.value - 1) * PAGE_SIZE));
  }
  return params;
}

async function fetchStats(): Promise<void> {
  const response = await fetch("/api/leads/stats", {
    headers: { "X-API-Key": API_KEY },
  });
  if (response.ok) {
    dbStats.value = (await response.json()) as typeof dbStats.value;
  }
}

async function fetchLeads(): Promise<void> {
  loading.value = true;
  error.value = null;

  try {
    const response = await fetch(`/api/leads?${buildSearchParams().toString()}`, {
      headers: { "X-API-Key": API_KEY },
    });
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      const message =
        typeof detail?.detail === "string"
          ? detail.detail
          : `API error: ${response.status}`;
      throw new Error(message);
    }
    const page = (await response.json()) as LeadSearchPage;
    leads.value = page.items;
    filteredTotal.value = page.total;
    totalPages.value = page.pages;
    currentPage.value = page.page;
    researchLeadId.value = null;
  } catch (err) {
    error.value = err instanceof Error ? err.message : t("loadFailed");
    leads.value = [];
    filteredTotal.value = 0;
    totalPages.value = 1;
  } finally {
    loading.value = false;
  }
}

function goToPage(page: number): void {
  const next = Math.min(Math.max(1, page), totalPages.value);
  if (next === currentPage.value) return;
  currentPage.value = next;
  void fetchLeads();
}

function goPrevPage(): void {
  if (canGoPrev.value) goToPage(currentPage.value - 1);
}

function goNextPage(): void {
  if (canGoNext.value) goToPage(currentPage.value + 1);
}

const touchSwipe = useTouchSwipe(swipeEnabled, goNextPage, goPrevPage);

function toggleResearch(leadId: number): void {
  researchLeadId.value = researchLeadId.value === leadId ? null : leadId;
}

async function onResearchSaved(): Promise<void> {
  await fetchLeads();
  await fetchStats();
}

async function exportCsv(): Promise<void> {
  const response = await fetch(`/api/leads/export/csv?${buildSearchParams(true).toString()}`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!response.ok) return;

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "texas_leads.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

watch(
  [searchQuery, locationFilter, industryFilter, qualifiedOnly, alcoholOnly, useRadiusSearch, radiusMiles],
  () => {
    currentPage.value = 1;
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      void fetchLeads();
    }, 300);
  },
);

function onWindowScroll() {
  showScrollTop.value = window.scrollY > 320;
}

onMounted(async () => {
  onWindowScroll();
  window.addEventListener("scroll", onWindowScroll, { passive: true });
  await Promise.all([fetchStats(), fetchLeads()]);
});

onUnmounted(() => {
  window.removeEventListener("scroll", onWindowScroll);
});
</script>

<template>
  <div class="page-shell">
    <PageParticles />
    <div class="page-content">
    <header class="app-header" :class="{ 'header-compact': headerCompact }">
      <div
        class="header-inner mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6"
      >
        <div class="flex min-w-0 items-center gap-3 animate-slide-up" style="animation-delay: 0ms">
          <AppLogo :size="headerCompact ? 'sm' : 'md'" class="header-logo" />
          <div class="min-w-0">
            <p
              class="header-tagline animate-fade-in text-[0.65rem] font-semibold uppercase tracking-[0.22em] accent-text"
              style="animation-delay: 120ms"
            >
              {{ t("tagline") }}
            </p>
            <h1
              class="header-title animate-fade-up truncate font-display text-2xl font-bold tracking-tight text-brand-navy dark:text-white"
              style="animation-delay: 180ms"
            >
              {{ t("appName") }}
            </h1>
          </div>
        </div>

        <div class="flex items-center gap-2 sm:gap-3">
          <div class="stat-pill animate-stat-pop hidden sm:block" style="animation-delay: 220ms">
            <span class="text-brand-navy/60 dark:text-slate-400">{{ t("statsTexas") }}</span>
            <span :key="dbStats.total" class="stat-number ml-1.5 font-semibold">{{
              dbStats.total.toLocaleString()
            }}</span>
          </div>
          <div class="stat-pill animate-stat-pop hidden md:block" style="animation-delay: 280ms">
            <span class="text-brand-navy/60 dark:text-slate-400">{{ t("statsQualified") }}</span>
            <span
              :key="dbStats.qualified"
              class="stat-number ml-1.5 font-semibold text-brand-teal dark:text-brand-teal-light"
            >
              {{ dbStats.qualified.toLocaleString() }}
            </span>
          </div>
          <div
            v-if="dbStats.sells_alcohol > 0"
            class="stat-pill animate-stat-pop hidden lg:block"
            style="animation-delay: 340ms"
          >
            <span class="text-brand-navy/60 dark:text-slate-400">{{ t("statsAlcohol") }}</span>
            <span :key="dbStats.sells_alcohol" class="stat-number ml-1.5 font-semibold accent-text">
              {{ dbStats.sells_alcohol.toLocaleString() }}
            </span>
          </div>
          <div class="animate-fade-in" style="animation-delay: 400ms">
            <LocaleToggle />
          </div>
          <div class="animate-fade-in" style="animation-delay: 450ms">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>

    <main
      class="main-mobile-pad mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8"
      @touchstart.passive="touchSwipe.onTouchStart"
      @touchend.passive="touchSwipe.onTouchEnd"
    >
      <div
        v-if="loading"
        class="pull-indicator md:hidden"
        aria-hidden="true"
      >
        <span class="pull-dot" />
      </div>

      <section
        id="search-panel"
        class="surface-card animate-slide-up mb-6 p-4 sm:mb-8 sm:p-6"
        :class="{ 'search-card-loading': loading }"
        style="animation-delay: 100ms"
      >
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <input
            v-model="searchQuery"
            type="search"
            :placeholder="t('searchPlaceholder')"
            class="input-field animate-fade-up"
            style="animation-delay: 160ms"
          />
          <input
            v-model="locationFilter"
            type="text"
            :placeholder="t('locationPlaceholder')"
            class="input-field animate-fade-up"
            style="animation-delay: 210ms"
          />
          <input
            v-model="industryFilter"
            type="text"
            :placeholder="t('industryPlaceholder')"
            class="input-field animate-fade-up"
            style="animation-delay: 260ms"
          />
          <label
            class="input-field animate-fade-up flex cursor-pointer items-center gap-2"
            style="animation-delay: 310ms"
          >
            <input
              v-model="qualifiedOnly"
              type="checkbox"
              class="h-4 w-4 rounded accent-brand-copper"
            />
            <span>{{ t("qualifiedOnly") }}</span>
          </label>
        </div>

        <div
          class="filter-panel mt-4 rounded-xl border border-brand-navy/10 bg-brand-sand/60 p-4 transition-colors duration-150 dark:border-white/10 dark:bg-brand-navy/40"
        >
          <div class="flex flex-wrap gap-x-6 gap-y-3">
            <label class="flex cursor-pointer items-center gap-2 text-sm">
              <input
                v-model="alcoholOnly"
                type="checkbox"
                class="h-4 w-4 rounded accent-brand-copper"
              />
              <span>{{ t("alcoholOnly") }}</span>
            </label>
            <label class="flex cursor-pointer items-center gap-2 text-sm">
              <input
                v-model="useRadiusSearch"
                type="checkbox"
                class="h-4 w-4 rounded accent-brand-teal"
              />
              {{ t("radiusFilter") }}
            </label>
          </div>
          <p v-if="alcoholOnly" class="mt-2 text-xs text-brand-navy/50 dark:text-slate-400">
            {{ t("alcoholOnlyHint") }}
          </p>
          <Transition name="panel">
            <div v-if="useRadiusSearch" class="mt-3">
              <div class="flex flex-wrap items-center justify-between gap-3 text-sm">
                <span>
                  {{ t("radiusLabel") }}:
                  <span class="font-semibold accent-text">{{ radiusLabel }}</span>
                </span>
                <span class="text-xs text-brand-navy/50 dark:text-slate-400">
                  {{ t("radiusHint") }}
                </span>
              </div>
              <input
                v-model.number="radiusMiles"
                type="range"
                min="1"
                max="50"
                step="1"
                class="mt-3 w-full accent-brand-copper"
              />
            </div>
          </Transition>
          <p v-if="!useRadiusSearch" class="mt-2 text-xs text-brand-navy/50 dark:text-slate-400">
            {{ t("noRadiusHint") }}
          </p>
        </div>

        <div class="mt-4 flex flex-wrap gap-3 animate-fade-up" style="animation-delay: 380ms">
          <button
            type="button"
            class="btn-primary"
            :class="{ 'btn-primary-loading': loading }"
            :disabled="loading"
            @click="fetchLeads"
          >
            <span
              v-if="loading"
              class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
            />
            {{ loading ? t("searching") : t("searchLeads") }}
          </button>
          <button type="button" class="btn-secondary" @click="exportCsv">
            {{ t("exportCsv") }}
          </button>
        </div>

        <p v-if="error" class="error-shake mt-4 text-sm text-rose-600 dark:text-rose-300">{{ error }}</p>
        <Transition v-else name="summary" mode="out-in">
          <p
            :key="resultsSummary"
            class="mt-4 text-sm text-brand-navy/70 dark:text-slate-300"
          >
            {{ resultsSummary }}
            <span v-if="qualifiedInView > 0" class="ml-2 accent-text">
              · {{ t("qualifiedInView", { count: String(qualifiedInView) }) }}
            </span>
          </p>
        </Transition>
        <p class="mt-1 text-xs text-brand-navy/45 dark:text-slate-500">
          {{ t("filtersAuto") }}
          <code class="accent-link">python -m scripts.ingest_texas_data --limit 500</code>
        </p>
      </section>

      <div v-if="loading && leads.length === 0" class="space-y-4">
        <div
          v-for="n in 3"
          :key="n"
          class="skeleton h-36 animate-fade-up"
          :style="{ animationDelay: `${n * 80}ms` }"
        />
      </div>

      <template v-else-if="leads.length > 0">
        <p
          v-if="swipeEnabled"
          class="swipe-hint mb-3 flex items-center justify-center gap-2 text-xs text-brand-navy/45 dark:text-slate-500 md:hidden"
        >
          <span class="swipe-chevron swipe-chevron-left" aria-hidden="true">‹</span>
          {{ t("swipeHint") }}
          <span class="swipe-chevron swipe-chevron-right" aria-hidden="true">›</span>
        </p>

        <TransitionGroup name="lead" tag="section" class="mobile-leads-stack space-y-4">
        <article
          v-for="(lead, index) in leads"
          :key="lead.id"
          class="lead-card lead-card-stagger"
          :style="{ animationDelay: `${Math.min(index * 45, 500)}ms` }"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-brand-navy dark:text-white">
                {{ lead.name }}
              </h2>
              <p class="text-sm text-brand-navy/65 dark:text-slate-300">
                {{ lead.city }}, {{ lead.state }}
                <span v-if="lead.zip_code"> · {{ lead.zip_code }}</span>
                <span v-if="lead.county"> · {{ lead.county }} {{ t("county") }}</span>
              </p>
              <p v-if="lead.industry" class="mt-1 text-sm font-medium accent-text">
                {{ lead.industry }}
              </p>
            </div>
            <div class="text-right">
              <span
                v-if="lead.distance_miles !== null"
                class="badge-distance badge-animate mb-2 block"
              >
                {{ lead.distance_miles }} mi
              </span>
              <span
                v-if="lead.website_analysis_notes?.includes('TABC')"
                class="badge-animate badge mb-2 block bg-brand-copper/15 text-brand-copper dark:text-brand-copper-light"
              >
                TABC
              </span>
              <span :class="lead.is_qualified ? 'badge-qualified' : 'badge-neutral badge-animate'">
                {{ t("score") }} {{ lead.qualification_score }}
              </span>
            </div>
          </div>

          <div
            class="mt-4 grid gap-2 text-sm text-brand-navy/75 dark:text-slate-300 md:grid-cols-2 lg:grid-cols-4"
          >
            <p>
              {{ t("website") }}:
              <span :class="lead.has_website ? 'font-medium' : 'text-amber-600 dark:text-amber-300'">
                {{ lead.has_website ? t("yes") : t("no") }}
              </span>
            </p>
            <p>
              {{ t("modern") }}:
              <span
                :class="lead.has_modern_website ? 'text-emerald-600 dark:text-emerald-300' : 'text-amber-600 dark:text-amber-300'"
              >
                {{ lead.has_modern_website ? t("yes") : t("no") }}
              </span>
            </p>
            <p v-if="lead.website_tech_stack">
              {{ t("stack") }}:
              <span class="accent-link">{{ lead.website_tech_stack }}</span>
            </p>
            <p v-if="lead.website_antiquity_years !== null && lead.website_antiquity_years > 0">
              {{ t("antiquity") }}:
              <span class="text-amber-600 dark:text-amber-300">
                {{ t("antiquityYears", { years: String(lead.website_antiquity_years) }) }}
              </span>
            </p>
            <p v-else-if="lead.has_website && lead.website_antiquity_years === 0">
              {{ t("antiquity") }}:
              <span class="text-emerald-600 dark:text-emerald-300">{{ t("antiquityCurrent") }}</span>
            </p>
            <p>
              {{ t("facebook") }}:
              <span
                :class="lead.has_active_facebook ? 'text-emerald-600 dark:text-emerald-300' : 'text-amber-600 dark:text-amber-300'"
              >
                {{ lead.has_active_facebook ? t("active") : t("inactive") }}
              </span>
            </p>
            <p>
              {{ t("instagram") }}:
              <span
                :class="lead.has_active_instagram ? 'text-emerald-600 dark:text-emerald-300' : 'text-amber-600 dark:text-amber-300'"
              >
                {{ lead.has_active_instagram ? t("active") : t("inactive") }}
              </span>
            </p>
          </div>

          <p
            v-if="lead.website_analysis_notes"
            class="mt-3 text-xs text-brand-navy/55 dark:text-slate-400"
          >
            {{ lead.website_analysis_notes }}
          </p>
          <p v-if="lead.qualification_notes" class="mt-1 text-xs text-brand-navy/45 dark:text-slate-500">
            {{ lead.qualification_notes }}
          </p>

          <div class="mt-4 flex flex-wrap gap-2">
            <button type="button" class="btn-accent" @click="toggleResearch(lead.id)">
              {{ researchLeadId === lead.id ? t("hideResearch") : t("researchWebsite") }}
            </button>
            <a
              v-if="lead.website_url"
              :href="lead.website_url"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-secondary px-3 py-1.5 text-xs"
            >
              {{ t("openUrl") }}
            </a>
          </div>

          <Transition name="panel" mode="out-in">
            <div v-if="researchLeadId === lead.id" class="research-inline hidden md:block">
              <WebsiteResearchPanel
                :key="lead.id"
                :lead="lead"
                :api-key="API_KEY"
                @saved="onResearchSaved"
                @close="researchLeadId = null"
              />
            </div>
          </Transition>
        </article>
        </TransitionGroup>
      </template>

      <div
        v-else-if="!loading && leads.length === 0"
        class="empty-state animate-fade-up py-16 text-center text-brand-navy/50 dark:text-slate-400"
      >
        <svg
          class="mx-auto mb-4 h-14 w-14 text-brand-teal/40 dark:text-brand-teal-light/40"
          viewBox="0 0 48 48"
          fill="none"
          aria-hidden="true"
        >
          <circle
            cx="20"
            cy="20"
            r="12"
            stroke="currentColor"
            stroke-width="2"
            class="animate-spin-slow"
            stroke-dasharray="4 6"
          />
          <path d="M30 30L40 40" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
          <text
            x="20"
            y="24"
            text-anchor="middle"
            font-size="9"
            font-weight="700"
            fill="currentColor"
          >
            TX
          </text>
        </svg>
        <p>{{ t("emptyLeads") }}</p>
      </div>

      <nav
        v-if="filteredTotal > PAGE_SIZE"
        :key="currentPage"
        class="pagination-nav mt-8 hidden flex-wrap items-center justify-center gap-3 md:flex"
        :aria-label="t('pageOf', { page: String(currentPage), pages: String(totalPages) })"
      >
        <button
          type="button"
          class="btn-secondary px-4 py-2 text-sm"
          :disabled="!canGoPrev || loading"
          @click="goPrevPage"
        >
          {{ t("prevPage") }}
        </button>
        <span :key="`page-${currentPage}`" class="stat-pill stat-number text-sm">
          {{ t("pageOf", { page: String(currentPage), pages: String(totalPages) }) }}
        </span>
        <button
          type="button"
          class="btn-secondary px-4 py-2 text-sm"
          :disabled="!canGoNext || loading"
          @click="goNextPage"
        >
          {{ t("nextPage") }}
        </button>
      </nav>

      <MobileBottomDock
        v-if="filteredTotal > 0"
        class="md:hidden"
        :current-page="currentPage"
        :total-pages="totalPages"
        :can-prev="canGoPrev"
        :can-next="canGoNext"
        :loading="loading"
        :filtered-total="filteredTotal"
        @prev="goPrevPage"
        @next="goNextPage"
        @search="scrollToSearch"
      />

      <button
        v-if="showScrollTop"
        type="button"
        class="scroll-fab md:hidden"
        :aria-label="t('scrollTop')"
        @click="scrollToTop"
      >
        <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M12 19V5M5 12l7-7 7 7" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <MobileSheet :open="activeResearchLead !== null" @close="researchLeadId = null">
        <WebsiteResearchPanel
          v-if="activeResearchLead"
          :lead="activeResearchLead"
          :api-key="API_KEY"
          @saved="onResearchSaved"
          @close="researchLeadId = null"
        />
      </MobileSheet>
    </main>
    </div>
  </div>
</template>