import { computed, ref } from "vue";
import { en, type MessageKey } from "../i18n/en";
import { es } from "../i18n/es";

type Locale = "en" | "es";

const catalogs = { en, es } as const;

function readStoredLocale(): Locale {
  try {
    const stored = localStorage.getItem("txbf-locale") || localStorage.getItem("tbf-locale");
    return stored === "es" ? "es" : "en";
  } catch {
    return "en";
  }
}

const locale = ref<Locale>(readStoredLocale());

function applyLocale(next: Locale): void {
  locale.value = next;
  document.documentElement.lang = next;
  try {
    localStorage.setItem("txbf-locale", next);
  } catch {
    /* private browsing */
  }
}

applyLocale(locale.value);

function interpolate(text: string, params?: Record<string, string | number>): string {
  if (!params) return text;
  return Object.entries(params).reduce(
    (acc, [key, value]) => acc.replaceAll(`{${key}}`, String(value)),
    text,
  );
}

export function useI18n() {
  const messages = computed(() => catalogs[locale.value]);

  function t(key: MessageKey, params?: Record<string, string | number>): string {
    return interpolate(messages.value[key], params);
  }

  function setLocale(next: Locale): void {
    applyLocale(next);
  }

  function toggleLocale(): void {
    applyLocale(locale.value === "en" ? "es" : "en");
  }

  return { locale, t, setLocale, toggleLocale };
}