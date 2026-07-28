import { onMounted, onUnmounted, ref } from "vue";

/** Collapse header after scroll — common mobile app pattern (2025–2026). */
export function useScrollCompact(threshold = 48) {
  const compact = ref(false);

  function onScroll() {
    compact.value = window.scrollY > threshold;
  }

  onMounted(() => {
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  });

  onUnmounted(() => {
    window.removeEventListener("scroll", onScroll);
  });

  return { compact };
}