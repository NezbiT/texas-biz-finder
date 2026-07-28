/**
 * Scroll-reveal: pone `visible` a true cuando el elemento entra en pantalla.
 * Todo ocurre en onMounted, así que en SSR no se ejecuta nada; el fallback
 * (sin IntersectionObserver) muestra el contenido de inmediato para no dejar
 * bloques invisibles si el navegador no soporta la API.
 */
export function useReveal(rootMargin = '0px 0px -8% 0px') {
  const el = ref<HTMLElement | null>(null)
  const visible = ref(false)
  let io: IntersectionObserver | null = null

  onMounted(() => {
    if (!el.value || typeof IntersectionObserver === 'undefined') {
      visible.value = true
      return
    }
    io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          visible.value = true
          io?.disconnect()
        }
      },
      { rootMargin, threshold: 0.12 },
    )
    io.observe(el.value)
  })

  onUnmounted(() => io?.disconnect())

  return { el, visible }
}
