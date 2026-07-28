import type { Ref } from "vue";

type SwipeHandlers = {
  onTouchStart: (event: TouchEvent) => void;
  onTouchEnd: (event: TouchEvent) => void;
};

function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return !!target.closest("input, textarea, select, button, a, label, [contenteditable]");
}

/** Horizontal swipe for mobile pagination (iOS-style). */
export function useTouchSwipe(
  enabled: Ref<boolean>,
  onSwipeLeft: () => void,
  onSwipeRight: () => void,
  minDistance = 72,
): SwipeHandlers {
  let startX = 0;
  let startY = 0;
  let tracking = false;

  function onTouchStart(event: TouchEvent) {
    if (!enabled.value || event.touches.length !== 1) return;
    if (isInteractiveTarget(event.target)) {
      tracking = false;
      return;
    }
    tracking = true;
    startX = event.touches[0].clientX;
    startY = event.touches[0].clientY;
  }

  function onTouchEnd(event: TouchEvent) {
    if (!enabled.value || !tracking || event.changedTouches.length !== 1) return;
    tracking = false;
    const dx = event.changedTouches[0].clientX - startX;
    const dy = event.changedTouches[0].clientY - startY;
    if (Math.abs(dx) < minDistance || Math.abs(dx) < Math.abs(dy) * 1.2) return;
    if (dx < 0) onSwipeLeft();
    else onSwipeRight();
  }

  return { onTouchStart, onTouchEnd };
}