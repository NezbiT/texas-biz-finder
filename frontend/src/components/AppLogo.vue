<script setup lang="ts">
import { useId } from "vue";

withDefaults(
  defineProps<{
    size?: "sm" | "md" | "lg";
  }>(),
  { size: "md" },
);

const uid = useId().replace(/:/g, "");

const sizes = {
  sm: "logo-wrap--sm",
  md: "logo-wrap--md",
  lg: "logo-wrap--lg",
};
</script>

<template>
  <div :class="['logo-wrap', sizes[size]]" role="img" aria-label="TX BizFinder — search Texas businesses">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo-svg">
      <defs>
        <linearGradient :id="`logo-bg-${uid}`" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop stop-color="#101a30" />
          <stop offset="1" stop-color="#0d2824" />
        </linearGradient>
        <linearGradient :id="`logo-ring-${uid}`" x1="8" y1="8" x2="36" y2="36" gradientUnits="userSpaceOnUse">
          <stop stop-color="#00f5d4" />
          <stop offset="1" stop-color="#2a9d8f" />
        </linearGradient>
        <linearGradient :id="`logo-handle-${uid}`" x1="30" y1="30" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop stop-color="#2a9d8f" />
          <stop offset="1" stop-color="#e8a55c" />
        </linearGradient>
      </defs>

      <rect x="3" y="3" width="42" height="42" rx="11" :fill="`url(#logo-bg-${uid})`" />
      <rect
        x="3.5"
        y="3.5"
        width="41"
        height="41"
        rx="10.5"
        :stroke="`url(#logo-ring-${uid})`"
        stroke-width="1.2"
        stroke-opacity="0.7"
        class="logo-border"
      />

      <!-- Magnifying glass lens -->
      <circle
        cx="20"
        cy="20"
        r="13"
        :stroke="`url(#logo-ring-${uid})`"
        stroke-width="2.5"
        fill="#0c1528"
        class="logo-lens"
      />
      <circle
        cx="20"
        cy="20"
        r="13"
        stroke="#00f5d4"
        stroke-width="1.5"
        stroke-dasharray="6 10"
        stroke-linecap="round"
        fill="none"
        opacity="0.55"
        class="logo-scan"
      />

      <!-- TX inside lens — clear readable mark -->
      <text
        x="20"
        y="24.5"
        text-anchor="middle"
        font-family="'DM Sans', system-ui, sans-serif"
        font-size="12.5"
        font-weight="700"
        letter-spacing="-0.5"
        fill="#f4f7fb"
        class="logo-tx"
      >
        TX
      </text>

      <!-- Handle -->
      <path
        d="M30.5 30.5L41.5 41.5"
        :stroke="`url(#logo-handle-${uid})`"
        stroke-width="3.5"
        stroke-linecap="round"
        class="logo-handle"
      />

      <!-- Found ping -->
      <circle cx="20" cy="20" r="2.2" fill="#00f5d4" class="logo-ping" />
    </svg>
  </div>
</template>

<style scoped>
.logo-wrap {
  display: inline-flex;
  flex-shrink: 0;
  animation: logo-float 4s ease-in-out infinite;
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.logo-wrap:hover {
  animation-play-state: paused;
  transform: scale(1.08);
}

.logo-wrap--sm {
  width: 2.25rem;
  height: 2.25rem;
}

.logo-wrap--md {
  width: 2.75rem;
  height: 2.75rem;
}

.logo-wrap--lg {
  width: 3.5rem;
  height: 3.5rem;
}

.logo-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.logo-lens {
  animation: lens-glow 2.8s ease-in-out infinite;
}

.logo-scan {
  transform-origin: 20px 20px;
  animation: scan-spin 6s linear infinite;
}

.logo-tx {
  animation: tx-pop 3s ease-in-out infinite;
}

.logo-handle {
  transform-origin: 30px 30px;
  animation: handle-tilt 2.4s ease-in-out infinite;
}

.logo-ping {
  transform-origin: 20px 20px;
  animation: ping-pulse 2s ease-out infinite;
}

.logo-border {
  animation: border-shimmer 5s ease-in-out infinite;
}

@keyframes logo-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

@keyframes lens-glow {
  0%,
  100% {
    filter: drop-shadow(0 0 0 rgba(0, 245, 212, 0));
  }
  50% {
    filter: drop-shadow(0 0 6px rgba(0, 245, 212, 0.45));
  }
}

@keyframes scan-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes tx-pop {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.92;
    transform: scale(1.04);
  }
}

@keyframes handle-tilt {
  0%,
  100% {
    transform: rotate(0deg);
  }
  50% {
    transform: rotate(4deg);
  }
}

@keyframes ping-pulse {
  0% {
    transform: scale(0.85);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.35);
    opacity: 0;
  }
  100% {
    transform: scale(0.85);
    opacity: 0;
  }
}

@keyframes border-shimmer {
  0%,
  100% {
    stroke-opacity: 0.55;
  }
  50% {
    stroke-opacity: 0.95;
  }
}

@media (prefers-reduced-motion: reduce) {
  .logo-wrap,
  .logo-lens,
  .logo-scan,
  .logo-tx,
  .logo-handle,
  .logo-ping,
  .logo-border {
    animation: none !important;
  }

  .logo-wrap:hover {
    transform: none;
  }
}
</style>