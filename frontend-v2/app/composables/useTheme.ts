/**
 * Tema claro/oscuro para v2. Cambio clave vs v1: se persiste en COOKIE en vez
 * de localStorage — así el servidor (SSR) conoce el tema y renderiza el HTML
 * ya con la clase `dark`, sin flash de tema incorrecto al cargar.
 */
type ThemeMode = 'light' | 'dark'

export function useTheme() {
  // useCookie = ref reactivo sincronizado con la cookie (funciona en server y cliente)
  const theme = useCookie<ThemeMode>('txbf_theme', {
    default: () => 'dark',        // oscuro por defecto (identidad de la marca)
    maxAge: 60 * 60 * 24 * 365,   // recuerda 1 año
  })

  // Alterna oscuro ↔ claro (botón sol/luna)
  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  // Fija un tema concreto (por si algún componente lo necesita)
  function setTheme(mode: ThemeMode): void {
    theme.value = mode
  }

  // Derivado booleano por comodidad
  const isDark = computed(() => theme.value === 'dark')

  return { theme, isDark, toggleTheme, setTheme }
}
