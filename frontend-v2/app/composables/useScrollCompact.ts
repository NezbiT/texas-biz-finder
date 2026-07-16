/**
 * Header que se compacta al hacer scroll — patrón común de apps móviles.
 * Devuelve `compact` (true cuando el usuario pasó el umbral de scroll).
 */
export function useScrollCompact(threshold = 48) {
  const compact = ref(false)

  // Actualiza el flag comparando el scroll actual contra el umbral
  function onScroll() {
    compact.value = window.scrollY > threshold
  }

  // Los listeners de window solo existen en el navegador (onMounted = cliente)
  onMounted(() => {
    onScroll()   // estado inicial correcto si la página carga ya scrolleada
    window.addEventListener('scroll', onScroll, { passive: true })
  })

  // Siempre limpiar los listeners al desmontar (evita fugas de memoria)
  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
  })

  return { compact }
}
