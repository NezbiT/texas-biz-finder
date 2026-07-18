import { onMounted, onUnmounted, reactive } from "vue";

/**
 * Shared pointer field for glow / tilt / magnetic UI.
 * One listener → many consumers (hero, cards, CTA).
 */
export function usePointerField() {
  const pointer = reactive({
    x: 0.5,
    y: 0.5,
    px: 0,
    py: 0,
    active: false,
  });

  function onMove(e: PointerEvent) {
    const w = window.innerWidth || 1;
    const h = window.innerHeight || 1;
    pointer.px = e.clientX;
    pointer.py = e.clientY;
    pointer.x = e.clientX / w;
    pointer.y = e.clientY / h;
    pointer.active = true;
  }

  function onLeave() {
    pointer.active = false;
  }

  onMounted(() => {
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
  });

  onUnmounted(() => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerleave", onLeave);
  });

  return { pointer };
}
