<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "../composables/useI18n";
import type { Lead } from "../types/lead";
import type {
  AnalysisStatus,
  WebsiteAnalysis,
  WebsiteSearchResult,
} from "../types/website-analysis";

const props = defineProps<{
  lead: Lead;
  apiKey: string;
}>();

const emit = defineEmits<{
  saved: [];
  close: [];
}>();

const { t } = useI18n();

const searchQuery = ref("");
const searchResults = ref<WebsiteSearchResult[]>([]);
const selectedUrl = ref("");
const customUrl = ref("");
const analyses = ref<WebsiteAnalysis[]>([]);
const latestAnalysis = ref<WebsiteAnalysis | null>(null);
const analysisStatus = ref<AnalysisStatus>({ busy: false, lead_id: null, url: null });

const searching = ref(false);
const analyzing = ref(false);
const savingUrl = ref(false);
const loadingHistory = ref(false);
const panelError = ref<string | null>(null);

const activeUrl = computed(() => selectedUrl.value || customUrl.value.trim());

const headers = computed(() => ({ "X-API-Key": props.apiKey, "Content-Type": "application/json" }));

async function parseError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null);
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.message) return String(body.detail.message);
  return `API error ${response.status}`;
}

async function refreshStatus(): Promise<void> {
  const response = await fetch("/api/leads/website-research/status", { headers: headers.value });
  if (response.ok) {
    analysisStatus.value = (await response.json()) as AnalysisStatus;
  }
}

async function loadHistory(): Promise<void> {
  loadingHistory.value = true;
  try {
    const response = await fetch(`/api/leads/${props.lead.id}/website-analyses`, {
      headers: headers.value,
    });
    if (!response.ok) throw new Error(await parseError(response));
    analyses.value = (await response.json()) as WebsiteAnalysis[];
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
    const response = await fetch(`/api/leads/${props.lead.id}/website-search`, {
      method: "POST",
      headers: headers.value,
      body: JSON.stringify({ max_results: 8 }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { query: string; results: WebsiteSearchResult[] };
    searchQuery.value = payload.query;
    searchResults.value = payload.results;
    if (props.lead.website_url) {
      selectedUrl.value = props.lead.website_url;
    }
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("searchingDdg");
  } finally {
    searching.value = false;
  }
}

function selectResult(result: WebsiteSearchResult): void {
  selectedUrl.value = result.url;
  customUrl.value = "";
}

async function saveUrlOnly(): Promise<void> {
  const url = activeUrl.value;
  if (!url) return;
  savingUrl.value = true;
  panelError.value = null;
  try {
    const response = await fetch(`/api/leads/${props.lead.id}/website-url`, {
      method: "PATCH",
      headers: headers.value,
      body: JSON.stringify({ url }),
    });
    if (!response.ok) throw new Error(await parseError(response));
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
    const response = await fetch(`/api/leads/${props.lead.id}/website-analyze`, {
      method: "POST",
      headers: headers.value,
      body: JSON.stringify({ url, save_to_lead: true }),
    });
    if (response.status === 409) {
      throw new Error(t("playwrightConflict"));
    }
    if (!response.ok) throw new Error(await parseError(response));
    latestAnalysis.value = (await response.json()) as WebsiteAnalysis;
    await loadHistory();
    emit("saved");
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : t("analyzing");
  } finally {
    analyzing.value = false;
    await refreshStatus();
  }
}

async function openReport(analysisId: number): Promise<void> {
  try {
    const response = await fetch(
      `/api/leads/${props.lead.id}/website-analyses/${analysisId}/report`,
      { headers: headers.value },
    );
    if (!response.ok) throw new Error(await parseError(response));
    const html = await response.text();
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
    selectedUrl.value = props.lead.website_url ?? "";
    customUrl.value = "";
    searchResults.value = [];
    searchQuery.value = "";
    panelError.value = null;
    await loadHistory();
    await refreshStatus();
  },
  { immediate: true },
);

onMounted(async () => {
  await refreshStatus();
});
</script>

<template>
  <section class="research-panel">
    <div class="flex flex-wrap items-start justify-between gap-3">
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
      class="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-800 dark:text-amber-200"
    >
      <span class="inline-block h-2 w-2 animate-pulse-soft rounded-full bg-amber-500 align-middle" />
      {{ t("playwrightBusy") }}
      <span v-if="analysisStatus.url" class="ml-1">— {{ analysisStatus.url }}</span>
    </p>

    <div class="mt-4 flex flex-wrap gap-2">
      <button type="button" class="btn-primary" :disabled="searching" @click="searchWebsite">
        {{ searching ? t("searchingDdg") : t("searchDdg") }}
      </button>
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

    <p v-if="searchQuery" class="mt-3 text-xs text-brand-navy/50 dark:text-slate-500">
      {{ t("queryLabel") }}: {{ searchQuery }}
    </p>
    <p v-if="panelError" class="mt-3 text-sm text-rose-600 dark:text-rose-300">{{ panelError }}</p>

    <TransitionGroup v-if="searchResults.length" name="lead" tag="div" class="mt-4 space-y-2">
      <p key="label" class="text-sm font-medium text-brand-navy dark:text-slate-200">
        {{ t("resultsLabel") }}
      </p>
      <button
        v-for="result in searchResults"
        :key="result.url"
        type="button"
        class="block w-full rounded-xl border px-4 py-3 text-left transition-all duration-100"
        :class="
          selectedUrl === result.url
            ? 'border-brand-copper bg-brand-copper/10 shadow-sm dark:border-brand-copper-light'
            : 'border-brand-navy/10 bg-white hover:border-brand-teal/40 dark:border-white/10 dark:bg-brand-navy/50'
        "
        @click="selectResult(result)"
      >
        <p class="font-medium text-brand-navy dark:text-white">{{ result.title }}</p>
        <p class="text-xs accent-link">{{ result.url }}</p>
        <p class="mt-1 text-sm text-brand-navy/60 dark:text-slate-400">{{ result.snippet }}</p>
      </button>
    </TransitionGroup>

    <div class="mt-4">
      <label class="text-sm text-brand-navy/70 dark:text-slate-300">{{ t("pasteUrl") }}</label>
      <input
        v-model="customUrl"
        type="url"
        :placeholder="t('urlPlaceholder')"
        class="input-field mt-2"
        @input="selectedUrl = ''"
      />
    </div>

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