<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import {
  analyzeLeadWebsite,
  fetchAnalysisReportHtml,
  fetchResearchStatus,
  fetchWayback,
  fetchWebsiteAnalyses,
  saveLeadWebsiteUrl,
  searchLeadWebsite,
} from "../lib/leadsApi";
import type { Lead } from "../types/lead";
import type {
  AnalysisStatus,
  WaybackInfo,
  WebsiteAnalysis,
  WebsiteSearchResult,
} from "../types/website-analysis";

const props = defineProps<{
  lead: Lead;
  /** @deprecated API key comes from env via lib/api — kept optional for call-site compat. */
  apiKey?: string;
}>();

const emit = defineEmits<{
  saved: [];
  close: [];
}>();

const { t } = useI18n();

const searchQuery = ref("");
const searchResults = ref<WebsiteSearchResult[]>([]);
const urlDraft = ref("");
const analyses = ref<WebsiteAnalysis[]>([]);
const latestAnalysis = ref<WebsiteAnalysis | null>(null);
const analysisStatus = ref<AnalysisStatus>({ busy: false, lead_id: null, url: null });

const searching = ref(false);
const analyzing = ref(false);
const savingUrl = ref(false);
const loadingHistory = ref(false);
const loadingWayback = ref(false);
const waybackDraft = ref<WaybackInfo | null>(null);
const panelError = ref<string | null>(null);
let waybackTimer: ReturnType<typeof setTimeout> | null = null;

const activeUrl = computed(() => urlDraft.value.trim());

function normalizeUrl(url: string): string {
  return url.trim().replace(/\/$/, "").toLowerCase();
}

function hrefForResult(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return "#";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function isSelectedResult(result: WebsiteSearchResult): boolean {
  if (!urlDraft.value.trim()) return false;
  return normalizeUrl(result.url) === normalizeUrl(urlDraft.value);
}

async function refreshStatus(): Promise<void> {
  try {
    analysisStatus.value = await fetchResearchStatus();
  } catch {
    /* non-blocking */
  }
}

async function loadHistory(): Promise<void> {
  loadingHistory.value = true;
  try {
    analyses.value = await fetchWebsiteAnalyses(props.lead.id);
    latestAnalysis.value = analyses.value[0] ?? null;
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("loadingHistory");
  } finally {
    loadingHistory.value = false;
  }
}

async function searchWebsite(): Promise<void> {
  searching.value = true;
  panelError.value = null;
  searchResults.value = [];
  try {
    const payload = await searchLeadWebsite(props.lead.id, { max_results: 8 });
    searchQuery.value = payload.query;
    searchResults.value = payload.results;
    if (!urlDraft.value.trim() && props.lead.website_url) {
      urlDraft.value = props.lead.website_url;
    }
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("searchingDdg");
  } finally {
    searching.value = false;
  }
}

function selectResult(result: WebsiteSearchResult): void {
  urlDraft.value = result.url;
  waybackDraft.value = result.wayback ?? null;
}

async function fetchWaybackForUrl(url: string): Promise<void> {
  const target = url.trim();
  if (!target) {
    waybackDraft.value = null;
    return;
  }
  loadingWayback.value = true;
  try {
    waybackDraft.value = await fetchWayback(target);
  } catch {
    waybackDraft.value = null;
  } finally {
    loadingWayback.value = false;
  }
}

function formatWaybackAge(info: WaybackInfo): string | null {
  if (info.age_years == null) return null;
  return t("waybackYears", { years: String(info.age_years) });
}

async function saveUrlOnly(): Promise<void> {
  const url = activeUrl.value;
  if (!url) return;
  savingUrl.value = true;
  panelError.value = null;
  try {
    await saveLeadWebsiteUrl(props.lead.id, { url });
    emit("saved");
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("savingUrl");
  } finally {
    savingUrl.value = false;
  }
}

async function analyzeWebsite(): Promise<void> {
  const url = activeUrl.value;
  if (!url) {
    panelError.value = t("selectUrlFirst");
    return;
  }

  await refreshStatus();
  if (analysisStatus.value.busy) {
    panelError.value = t("analysisBusy");
    return;
  }

  analyzing.value = true;
  panelError.value = null;
  try {
    latestAnalysis.value = await analyzeLeadWebsite(props.lead.id, {
      url,
      save_to_lead: true,
    });
    await loadHistory();
    emit("saved");
  } catch (err) {
    if (err instanceof Error && err.message === "CONFLICT_BUSY") {
      panelError.value = t("playwrightConflict");
    } else {
      panelError.value = err instanceof Error ? err.message : t("analyzing");
    }
  } finally {
    analyzing.value = false;
    await refreshStatus();
  }
}

async function openReport(analysisId: number): Promise<void> {
  try {
    const html = await fetchAnalysisReportHtml(props.lead.id, analysisId);
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("downloadReport");
  }
}

watch(
  () => props.lead.id,
  async () => {
    urlDraft.value = props.lead.website_url ?? "";
    waybackDraft.value = null;
    searchResults.value = [];
    searchQuery.value = "";
    panelError.value = null;
    await loadHistory();
    await refreshStatus();
    if (urlDraft.value.trim()) {
      void fetchWaybackForUrl(urlDraft.value);
    }
  },
  { immediate: true },
);

watch(urlDraft, (value) => {
  if (waybackTimer) clearTimeout(waybackTimer);
  const match = searchResults.value.find(
    (r) => normalizeUrl(r.url) === normalizeUrl(value),
  );
  if (match?.wayback) {
    waybackDraft.value = match.wayback;
    return;
  }
  waybackTimer = setTimeout(() => {
    void fetchWaybackForUrl(value);
  }, 450);
});

onMounted(async () => {
  await refreshStatus();
});
</script>

<template>
  <section class="research-panel animate-slide-up">
    <div class="flex flex-wrap items-start justify-between gap-3 animate-fade-up">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.18em] accent-text">
          {{ t("researchTitle") }}
        </p>
        <h3 class="text-lg font-semibold text-brand-navy dark:text-white">
          {{ t("researchHeading") }}
        </h3>
        <p class="mt-1 text-sm text-brand-navy/60 dark:text-slate-400">
          {{ t("researchDesc") }}
        </p>
      </div>
      <button type="button" class="btn-secondary px-3 py-1.5 text-xs" @click="emit('close')">
        {{ t("close") }}
      </button>
    </div>

    <p
      v-if="analysisStatus.busy"
      class="busy-banner mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200"
    >
      <span class="inline-block h-2 w-2 animate-pulse-soft rounded-full bg-amber-500 align-middle" />
      {{ t("playwrightBusy") }}
      <span v-if="analysisStatus.url" class="ml-1">— {{ analysisStatus.url }}</span>
    </p>

    <div class="mt-4">
      <button
        type="button"
        class="btn-primary animate-fade-up"
        style="animation-delay: 80ms"
        :class="{ 'btn-primary-loading': searching }"
        :disabled="searching"
        @click="searchWebsite"
      >
        {{ searching ? t("searchingDdg") : t("searchDdg") }}
      </button>
    </div>

    <p v-if="searchQuery" class="mt-3 text-xs text-brand-navy/50 dark:text-slate-500">
      {{ t("queryLabel") }}: {{ searchQuery }}
    </p>
    <p v-if="panelError" class="error-shake mt-3 text-sm text-rose-600 dark:text-rose-300">
      {{ panelError }}
    </p>

    <TransitionGroup v-if="searchResults.length" name="lead" tag="div" class="mt-4 space-y-2">
      <p key="label" class="text-sm font-medium text-brand-navy dark:text-slate-200">
        {{ t("resultsLabel") }}
      </p>
      <p key="hint" class="text-xs text-brand-navy/50 dark:text-slate-500">
        {{ t("resultsOpenHint") }}
      </p>
      <article
        v-for="(result, index) in searchResults"
        :key="result.url"
        class="research-result-card animate-fade-up"
        :class="{ selected: isSelectedResult(result) }"
        :style="{ animationDelay: `${index * 60}ms` }"
      >
        <p class="font-medium text-brand-navy dark:text-white">{{ result.title }}</p>
        <a
          :href="hrefForResult(result.url)"
          target="_blank"
          rel="noopener noreferrer"
          class="research-result-link mt-1 inline-block text-xs"
          @click.stop
        >
          {{ result.url }}
          <span class="sr-only">{{ t("openLink") }}</span>
        </a>
        <p class="mt-1 text-sm text-brand-navy/60 dark:text-slate-400">{{ result.snippet }}</p>
        <p
          v-if="result.wayback?.available"
          class="mt-2 text-xs text-brand-teal dark:text-brand-teal-light"
        >
          {{ t("waybackFirstSeen") }}: {{ result.wayback.first_seen }}
          <span v-if="result.wayback.age_years != null">
            · {{ formatWaybackAge(result.wayback) }}
          </span>
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <a
            :href="hrefForResult(result.url)"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-secondary px-3 py-1.5 text-xs"
            @click.stop
          >
            {{ t("openLink") }}
          </a>
          <button
            type="button"
            class="btn-primary px-3 py-1.5 text-xs"
            :class="{ 'ring-2 ring-brand-copper ring-offset-2 dark:ring-offset-brand-navy': isSelectedResult(result) }"
            @click="selectResult(result)"
          >
            {{ isSelectedResult(result) ? t("selectedUrl") : t("useThisUrl") }}
          </button>
        </div>
      </article>
    </TransitionGroup>

    <div class="mt-4">
      <label class="text-sm font-medium text-brand-navy dark:text-slate-200" for="website-url-draft">
        {{ t("pasteUrl") }}
      </label>
      <p class="mt-1 text-xs text-brand-navy/50 dark:text-slate-500">
        {{ t("editUrlHint") }}
      </p>
      <input
        id="website-url-draft"
        v-model="urlDraft"
        type="url"
        :placeholder="t('urlPlaceholder')"
        class="input-field mt-2"
        autocomplete="url"
        inputmode="url"
      />
    </div>

    <div
      v-if="activeUrl && (loadingWayback || waybackDraft)"
      class="mt-4 rounded-xl border border-brand-navy/10 bg-white/70 p-4 dark:border-white/10 dark:bg-brand-navy/40"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-brand-teal">
        {{ t("waybackTitle") }}
      </p>
      <p v-if="loadingWayback" class="mt-2 text-sm text-brand-navy/60 dark:text-slate-400">
        {{ t("waybackLoading") }}
      </p>
      <template v-else-if="waybackDraft">
        <p v-if="!waybackDraft.available" class="mt-2 text-sm text-brand-navy/60 dark:text-slate-400">
          {{ t("waybackNone") }}
        </p>
        <template v-else>
          <div class="mt-3 grid gap-2 text-sm text-brand-navy/75 dark:text-slate-300 sm:grid-cols-2">
            <p>{{ t("waybackFirstSeen") }}: {{ waybackDraft.first_seen ?? "—" }}</p>
            <p>{{ t("waybackLastSeen") }}: {{ waybackDraft.last_seen ?? "—" }}</p>
            <p>{{ t("waybackSnapshots") }}: {{ waybackDraft.snapshot_count.toLocaleString() }}</p>
            <p v-if="formatWaybackAge(waybackDraft)">
              {{ t("waybackAge") }}: {{ formatWaybackAge(waybackDraft) }}
            </p>
          </div>
          <div class="mt-3 flex flex-wrap gap-3 text-xs">
            <a
              :href="waybackDraft.timeline_url"
              target="_blank"
              rel="noopener noreferrer"
              class="accent-link"
            >
              {{ t("waybackTimeline") }}
            </a>
            <a
              v-if="waybackDraft.first_snapshot_url"
              :href="waybackDraft.first_snapshot_url"
              target="_blank"
              rel="noopener noreferrer"
              class="accent-link"
            >
              {{ t("waybackFirstLink") }}
            </a>
            <a
              v-if="waybackDraft.last_snapshot_url"
              :href="waybackDraft.last_snapshot_url"
              target="_blank"
              rel="noopener noreferrer"
              class="accent-link"
            >
              {{ t("waybackLastLink") }}
            </a>
          </div>
        </template>
      </template>
    </div>

    <div class="mt-4 flex flex-wrap gap-2">
      <button
        type="button"
        class="btn-secondary"
        :disabled="!activeUrl || savingUrl"
        @click="saveUrlOnly"
      >
        {{ savingUrl ? t("savingUrl") : t("saveUrl") }}
      </button>
      <button
        type="button"
        class="btn-accent"
        :disabled="!activeUrl || analyzing || analysisStatus.busy"
        @click="analyzeWebsite"
      >
        {{ analyzing ? t("analyzing") : t("analyzePlaywright") }}
      </button>
    </div>
    <p class="mt-2 text-xs text-brand-navy/50 dark:text-slate-500">
      {{ t("saveUrlHint") }}
    </p>

    <Transition name="panel">
      <div
        v-if="latestAnalysis"
        class="mt-6 rounded-xl border border-brand-navy/10 bg-white/80 p-4 dark:border-white/10 dark:bg-brand-navy/50"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h4 class="font-semibold text-brand-navy dark:text-white">{{ t("latestAnalysis") }}</h4>
          <span
            class="badge"
            :class="
              latestAnalysis.status === 'completed'
                ? 'badge-qualified'
                : 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
            "
          >
            {{ latestAnalysis.status }}
          </span>
        </div>
        <p class="mt-2 text-sm text-brand-navy/75 dark:text-slate-300">
          {{ latestAnalysis.summary }}
        </p>
        <div class="mt-3 grid gap-2 text-sm text-brand-navy/70 dark:text-slate-300 md:grid-cols-2">
          <p>{{ t("load") }}: {{ latestAnalysis.load_time_ms ?? "n/a" }} ms</p>
          <p>
            {{ t("lastModified") }}:
            {{ latestAnalysis.last_modified ?? t("modifiedUnknown") }}
          </p>
          <p>{{ t("titleSeo") }}: {{ latestAnalysis.seo_title ?? "—" }}</p>
          <p>H1: {{ latestAnalysis.seo_h1 ?? "—" }}</p>
          <template v-if="latestAnalysis.metrics?.wayback">
            <p>
              {{ t("waybackFirstSeen") }}:
              {{ (latestAnalysis.metrics.wayback as WaybackInfo).first_seen ?? "—" }}
            </p>
            <p>
              {{ t("waybackLastSeen") }}:
              {{ (latestAnalysis.metrics.wayback as WaybackInfo).last_seen ?? "—" }}
            </p>
          </template>
        </div>
        <p v-if="latestAnalysis.technologies.length" class="mt-2 text-sm accent-text">
          {{ t("stack") }}: {{ latestAnalysis.technologies.join(", ") }}
        </p>
        <ul
          v-if="latestAnalysis.seo_issues.length"
          class="mt-2 list-disc pl-5 text-sm text-amber-700 dark:text-amber-200"
        >
          <li v-for="issue in latestAnalysis.seo_issues" :key="issue">{{ issue }}</li>
        </ul>
        <p v-if="latestAnalysis.error_message" class="mt-2 text-sm text-rose-600 dark:text-rose-300">
          {{ latestAnalysis.error_message }}
        </p>
        <button
          type="button"
          class="btn-secondary mt-3 px-3 py-1.5 text-xs"
          @click="openReport(latestAnalysis.id)"
        >
          {{ t("downloadReport") }}
        </button>
      </div>
    </Transition>

    <div v-if="analyses.length > 1" class="mt-6">
      <h4 class="text-sm font-medium text-brand-navy dark:text-slate-200">
        {{ t("history", { count: String(analyses.length) }) }}
      </h4>
      <ul class="mt-2 space-y-2 text-sm text-brand-navy/60 dark:text-slate-400">
        <li
          v-for="item in analyses.slice(1, 6)"
          :key="item.id"
          class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-brand-navy/10 px-3 py-2 dark:border-white/5"
        >
          <span>{{ new Date(item.created_at).toLocaleString() }} — {{ item.url }}</span>
          <button type="button" class="accent-link text-xs" @click="openReport(item.id)">
            {{ t("report") }}
          </button>
        </li>
      </ul>
    </div>

    <p v-if="loadingHistory" class="mt-4 text-xs text-brand-navy/45 dark:text-slate-500">
      {{ t("loadingHistory") }}
    </p>
  </section>
</template>