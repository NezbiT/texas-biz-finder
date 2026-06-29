<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import type { Lead } from "../types/lead";

const API_KEY = import.meta.env.VITE_ADMIN_API_KEY ?? "admin-dev-key-change-me";

const leads = ref<Lead[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const searchQuery = ref("");
const locationFilter = ref("");
const radiusMiles = ref(25);
const useRadiusSearch = ref(false);
const industryFilter = ref("");
const qualifiedOnly = ref(true);
const dbStats = ref({ total: 0, qualified: 0, small_business: 0 });

const qualifiedCount = computed(
  () => leads.value.filter((lead) => lead.is_qualified).length
);

const radiusLabel = computed(() => `${radiusMiles.value} mi`);

const resultsSummary = computed(() => {
  const showing = leads.value.length;
  const pool = qualifiedOnly.value ? dbStats.value.qualified : dbStats.value.small_business;
  return `Mostrando ${showing} de ${pool} disponibles (${dbStats.value.total} en la base de datos)`;
});

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

function buildSearchParams(): URLSearchParams {
  const params = new URLSearchParams();
  if (searchQuery.value) params.set("q", searchQuery.value);
  appendLocationParams(params);
  if (industryFilter.value) params.set("industry", industryFilter.value);
  params.set("qualified_only", String(qualifiedOnly.value));
  params.set("small_business_only", "true");
  params.set("limit", "500");
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
    leads.value = (await response.json()) as Lead[];
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load leads";
    leads.value = [];
  } finally {
    loading.value = false;
  }
}

async function exportCsv(): Promise<void> {
  const response = await fetch(`/api/leads/export/csv?${buildSearchParams().toString()}`, {
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

onMounted(async () => {
  await fetchStats();
  await fetchLeads();
});
</script>

<template>
  <div class="min-h-screen bg-hero-gradient">
    <header class="border-b border-white/10 bg-slate-950/40 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <div>
          <p class="text-xs uppercase tracking-[0.2em] text-violet-300">
            Texas Lead Intelligence
          </p>
          <h1 class="text-2xl font-semibold text-white">TexasBizFinder</h1>
        </div>
        <div class="rounded-full bg-white/10 px-4 py-2 text-sm text-slate-200">
          {{ dbStats.total }} leads en DB
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <section
        class="mb-8 rounded-2xl border border-white/10 bg-card-gradient p-6 shadow-xl"
      >
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Buscar: auto, repair, nombre..."
            class="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:border-violet-400 focus:outline-none"
          />
          <input
            v-model="locationFilter"
            type="text"
            placeholder="Ciudad o ZIP (ej. La Porte, 77571)"
            class="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:border-violet-400 focus:outline-none"
          />
          <input
            v-model="industryFilter"
            type="text"
            placeholder="Industry"
            class="rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:border-violet-400 focus:outline-none"
          />
          <label
            class="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900/60 px-4 py-3 text-sm text-slate-200"
          >
            <input v-model="qualifiedOnly" type="checkbox" class="accent-violet-500" />
            Qualified only
          </label>
        </div>

        <div class="mt-4 rounded-xl border border-white/10 bg-slate-900/40 p-4">
          <label class="flex items-center gap-2 text-sm text-slate-200">
            <input v-model="useRadiusSearch" type="checkbox" class="accent-violet-500" />
            Filtrar por radio (ciudad/ZIP + millas)
          </label>
          <template v-if="useRadiusSearch">
            <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
              <span class="text-sm text-slate-200">
                Radio: <span class="font-medium text-violet-300">{{ radiusLabel }}</span>
              </span>
              <span class="text-xs text-slate-400">Hasta 50 millas — solo leads con coordenadas</span>
            </div>
            <input
              v-model.number="radiusMiles"
              type="range"
              min="1"
              max="50"
              step="1"
              class="mt-3 w-full accent-violet-500"
            />
          </template>
          <p v-else class="mt-2 text-xs text-slate-400">
            Sin radio: busca por nombre de ciudad o ZIP en todos los registros.
          </p>
        </div>

        <div class="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            class="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500"
            :disabled="loading"
            @click="fetchLeads"
          >
            {{ loading ? "Searching..." : "Search leads" }}
          </button>
          <button
            type="button"
            class="rounded-xl border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
            @click="exportCsv"
          >
            Export CSV
          </button>
        </div>

        <p v-if="error" class="mt-4 text-sm text-rose-300">{{ error }}</p>
        <p v-else class="mt-4 text-sm text-slate-300">{{ resultsSummary }}</p>
        <p class="mt-1 text-xs text-slate-500">
          Desmarca "Qualified only" para ver más. Para más datos:
          <code class="text-violet-300">python -m scripts.ingest_texas_data --limit 500</code>
        </p>
      </section>

      <section class="space-y-4">
        <article
          v-for="lead in leads"
          :key="lead.id"
          class="rounded-2xl border border-white/10 bg-slate-900/50 p-5 backdrop-blur transition hover:border-violet-400/40"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-white">{{ lead.name }}</h2>
              <p class="text-sm text-slate-300">
                {{ lead.city }}, {{ lead.state }}
                <span v-if="lead.zip_code"> · {{ lead.zip_code }}</span>
                <span v-if="lead.county"> · {{ lead.county }} County</span>
              </p>
              <p v-if="lead.industry" class="mt-1 text-sm text-violet-200">
                {{ lead.industry }}
              </p>
            </div>
            <div class="text-right">
              <span
                v-if="lead.distance_miles !== null"
                class="mb-2 block rounded-full bg-violet-500/20 px-3 py-1 text-xs font-medium text-violet-200"
              >
                {{ lead.distance_miles }} mi away
              </span>
              <span
                class="inline-block rounded-full px-3 py-1 text-xs font-medium"
                :class="
                  lead.is_qualified
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'bg-slate-700 text-slate-300'
                "
              >
                Score {{ lead.qualification_score }}
              </span>
            </div>
          </div>

          <div class="mt-4 grid gap-2 text-sm text-slate-300 md:grid-cols-2 lg:grid-cols-4">
            <p>
              Website:
              <span :class="lead.has_website ? 'text-slate-200' : 'text-amber-300'">
                {{ lead.has_website ? "Yes" : "No" }}
              </span>
            </p>
            <p>
              Modern:
              <span :class="lead.has_modern_website ? 'text-emerald-300' : 'text-amber-300'">
                {{ lead.has_modern_website ? "Yes" : "No" }}
              </span>
            </p>
            <p v-if="lead.website_tech_stack">
              Stack:
              <span class="text-violet-200">{{ lead.website_tech_stack }}</span>
            </p>
            <p v-if="lead.website_antiquity_years !== null && lead.website_antiquity_years > 0">
              Antiquity:
              <span class="text-amber-300">~{{ lead.website_antiquity_years }} years</span>
            </p>
            <p v-else-if="lead.has_website && lead.website_antiquity_years === 0">
              Antiquity:
              <span class="text-emerald-300">Current</span>
            </p>
            <p>
              Facebook:
              <span :class="lead.has_active_facebook ? 'text-emerald-300' : 'text-amber-300'">
                {{ lead.has_active_facebook ? "Active" : "Inactive" }}
              </span>
            </p>
            <p>
              Instagram:
              <span :class="lead.has_active_instagram ? 'text-emerald-300' : 'text-amber-300'">
                {{ lead.has_active_instagram ? "Active" : "Inactive" }}
              </span>
            </p>
          </div>

          <p v-if="lead.website_analysis_notes" class="mt-3 text-xs text-slate-400">
            {{ lead.website_analysis_notes }}
          </p>
          <p v-if="lead.qualification_notes" class="mt-1 text-xs text-slate-500">
            {{ lead.qualification_notes }}
          </p>
        </article>

        <p v-if="!loading && leads.length === 0" class="text-center text-slate-400">
          No leads match your filters. Try another city, ZIP, or radius.
        </p>
      </section>
    </main>
  </div>
</template>