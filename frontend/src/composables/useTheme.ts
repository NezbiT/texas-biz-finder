import { onMounted, ref, watch } from "vue";

export type ThemeMode = "light" | "dark";

const theme = ref<ThemeMode>("dark");

function applyTheme(mode: ThemeMode): void {
  theme.value = mode;
  document.documentElement.classList.toggle("dark", mode === "dark");
  document.documentElement.style.colorScheme = mode;
  localStorage.setItem("tbf-theme", mode);
}

export function useTheme() {
  onMounted(() => {
    const stored = localStorage.getItem("tbf-theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial: ThemeMode =
      stored === "light" || stored === "dark" ? stored : prefersDark ? "dark" : "light";
    applyTheme(initial);
  });

  function toggleTheme(): void {
    applyTheme(theme.value === "dark" ? "light" : "dark");
  }

  function setTheme(mode: ThemeMode): void {
    applyTheme(mode);
  }

  const isDark = ref(theme.value === "dark");
  watch(theme, (value) => {
    isDark.value = value === "dark";
  });

  return { theme, isDark, toggleTheme, setTheme };
}