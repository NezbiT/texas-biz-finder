import type { Ref } from 'vue'

/** Los dos handlers que el componente engancha a touchstart/touchend. */
type SwipeHandlers = {
  onTouchStart: (event: TouchEvent) => void
  onTouchEnd: (event: TouchEvent) => void
}

/** ¿El toque empezó sobre un control interactivo? (no robarle el gesto). */
function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false
  return !!target.closest('input, textarea, select, button, a, label, [contenteditable]')
}

/** Swipe horizontal para paginar en móvil (estilo iOS). */
export function useTouchSwipe(
  enabled: Ref<boolean>,        // permite desactivar el gesto (p. ej. mientras carga)
  onSwipeLeft: () => void,      // swipe hacia la izquierda = página siguiente
  onSwipeRight: () => void,     // swipe hacia la derecha = página anterior
  minDistance = 72,             // px mínimos para considerar que fue un swipe
): SwipeHandlers {
  let startX = 0        // posición inicial del dedo
  let startY = 0
  let tracking = false  // ¿estamos siguiendo un gesto válido?

  function onTouchStart(event: TouchEvent) {
    // Solo gestos de un dedo, con el swipe habilitado
    if (!enabled.value || event.touches.length !== 1) return
    // Si tocó un input/botón, ese elemento se queda con el gesto
    if (isInteractiveTarget(event.target)) {
      tracking = false
      return
    }
    tracking = true
    startX = event.touches[0].clientX
    startY = event.touches[0].clientY
  }

  function onTouchEnd(event: TouchEvent) {
    if (!enabled.value || !tracking || event.changedTouches.length !== 1) return
    tracking = false
    // Desplazamiento total del dedo en X e Y
    const dx = event.changedTouches[0].clientX - startX
    const dy = event.changedTouches[0].clientY - startY
    // Debe ser suficientemente largo Y claramente horizontal (no un scroll)
    if (Math.abs(dx) < minDistance || Math.abs(dx) < Math.abs(dy) * 1.2) return
    if (dx < 0) onSwipeLeft()
    else onSwipeRight()
  }

  return { onTouchStart, onTouchEnd }
}
