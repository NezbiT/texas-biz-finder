import { onMounted, onUnmounted, ref, type Ref } from "vue";

/** Scroll-reveal: toggles `.is-in` when element enters viewport. */
export function useReveal(rootMargin = "0px 0px -8% 0px") {
  const el: Ref<HTMLElement | null> = ref(null);
  const visible = ref(false);
  let io: IntersectionObserver | null = null;

  onMounted(() => {
    if (!el.value || typeof IntersectionObserver === "undefined") {
      visible.value = true;
      return;
    }
    io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          visible.value = true;
          io?.disconnect();
        }
      },
      { rootMargin, threshold: 0.12 },
    );
    io.observe(el.value);
  });

  onUnmounted(() => io?.disconnect());

  return { el, visible };
}
