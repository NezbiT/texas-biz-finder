<script setup lang="ts">
/**
 * Canvas #1 — Plains dusk + wind
 * Texas big-sky: warm sunset, ridge silhouette, grass bending in the breeze.
 */
import { onMounted, onUnmounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    /** When false, freezes the wind (tab hidden / reduced motion). */
    animate?: boolean;
    /** 0–1 pointer field for gentle parallax (optional). */
    pointerX?: number;
    pointerY?: number;
  }>(),
  {
    animate: true,
    pointerX: 0.5,
    pointerY: 0.5,
  },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);

type Blade = {
  x: number;
  baseY: number;
  h: number;
  thick: number;
  phase: number;
  speed: number;
  hue: number;
  lean: number;
};

type Ridge = { y: number; amp: number; freq: number; color: string; speed: number; phase: number };

let raf = 0;
let blades: Blade[] = [];
let ridges: Ridge[] = [];
let w = 0;
let h = 0;
let dpr = 1;
let t0 = 0;
let reduced = false;

function prefersReduced(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function isCoarse(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

function rebuild(cw: number, ch: number) {
  w = cw;
  h = ch;
  const density = isCoarse() ? 0.55 : 1;
  const count = Math.floor((cw / 7) * density);
  blades = [];
  for (let i = 0; i < count; i++) {
    const x = (i / count) * cw + (Math.random() - 0.5) * 6;
    const baseY = ch * (0.72 + Math.random() * 0.26);
    blades.push({
      x,
      baseY,
      h: 18 + Math.random() * 42 * (baseY / ch),
      thick: 0.8 + Math.random() * 1.4,
      phase: Math.random() * Math.PI * 2,
      speed: 0.9 + Math.random() * 1.4,
      hue: 22 + Math.random() * 18, // orange-amber family
      lean: (Math.random() - 0.5) * 0.15,
    });
  }

  ridges = [
    { y: 0.62, amp: 18, freq: 0.004, color: "#1a1410", speed: 0.08, phase: 0.2 },
    { y: 0.68, amp: 14, freq: 0.006, color: "#15110e", speed: 0.12, phase: 1.1 },
    { y: 0.74, amp: 10, freq: 0.009, color: "#100e0c", speed: 0.18, phase: 2.4 },
  ];
}

function drawSky(ctx: CanvasRenderingContext2D, time: number) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#1c1410");
  g.addColorStop(0.35, "#18181b");
  g.addColorStop(0.55, "#2a1810");
  g.addColorStop(0.72, "#c2410c");
  g.addColorStop(0.82, "#f97316");
  g.addColorStop(0.9, "#fdba74");
  g.addColorStop(1, "#1a1008");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  // Soft sun just above the horizon
  const sunX = w * (0.72 + (props.pointerX - 0.5) * 0.04);
  const sunY = h * 0.68 + Math.sin(time * 0.15) * 2;
  const sunR = Math.min(w, h) * 0.12;
  const sg = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, sunR * 2.4);
  sg.addColorStop(0, "rgba(255, 220, 160, 0.55)");
  sg.addColorStop(0.25, "rgba(249, 115, 22, 0.35)");
  sg.addColorStop(0.55, "rgba(234, 88, 12, 0.12)");
  sg.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = sg;
  ctx.beginPath();
  ctx.arc(sunX, sunY, sunR * 2.4, 0, Math.PI * 2);
  ctx.fill();
}

function drawRidges(ctx: CanvasRenderingContext2D, time: number) {
  const px = (props.pointerX - 0.5) * 20;
  for (const r of ridges) {
    const base = h * r.y;
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(0, base);
    for (let x = 0; x <= w; x += 8) {
      const y =
        base +
        Math.sin(x * r.freq + time * r.speed + r.phase) * r.amp +
        Math.sin(x * r.freq * 2.3 + time * r.speed * 0.7) * (r.amp * 0.35) +
        px * (r.y - 0.5);
      ctx.lineTo(x, y);
    }
    ctx.lineTo(w, h);
    ctx.closePath();
    ctx.fillStyle = r.color;
    ctx.fill();
  }
}

function drawHorizonLine(ctx: CanvasRenderingContext2D, time: number) {
  const y = h * 0.7 + Math.sin(time * 0.4) * 1.5;
  const g = ctx.createLinearGradient(0, y, w, y);
  g.addColorStop(0, "rgba(249,115,22,0)");
  g.addColorStop(0.35, "rgba(253,186,116,0.35)");
  g.addColorStop(0.5, "rgba(255,220,160,0.7)");
  g.addColorStop(0.65, "rgba(253,186,116,0.35)");
  g.addColorStop(1, "rgba(249,115,22,0)");
  ctx.strokeStyle = g;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(w, y);
  ctx.stroke();
}

function drawGrass(ctx: CanvasRenderingContext2D, time: number) {
  const wind = Math.sin(time * 0.7) * 0.55 + Math.sin(time * 1.3) * 0.25;
  const gust = Math.sin(time * 0.21 + 1.2) * 0.2;
  for (const b of blades) {
    const sway =
      (wind + gust) * (0.55 + b.speed * 0.2) +
      Math.sin(time * b.speed + b.phase + b.x * 0.01) * 0.45;
    const tipX = b.x + (sway + b.lean) * b.h * 0.85;
    const tipY = b.baseY - b.h;
    const midX = b.x + (sway + b.lean) * b.h * 0.35;
    const midY = b.baseY - b.h * 0.5;

    ctx.beginPath();
    ctx.moveTo(b.x, b.baseY);
    ctx.quadraticCurveTo(midX, midY, tipX, tipY);
    ctx.strokeStyle = `hsla(${b.hue}, 70%, ${28 + (b.baseY / h) * 12}%, ${0.35 + (b.baseY / h) * 0.35})`;
    ctx.lineWidth = b.thick;
    ctx.lineCap = "round";
    ctx.stroke();
  }
}

function drawVignette(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.4, h * 0.15, w * 0.5, h * 0.45, h * 0.85);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(9,9,11,0.55)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

function frame(now: number) {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  if (!t0) t0 = now;
  const time = (now - t0) / 1000;
  const run = props.animate && !reduced;

  drawSky(ctx, run ? time : 0);
  drawRidges(ctx, run ? time : 0);
  drawHorizonLine(ctx, run ? time : 0);
  drawGrass(ctx, run ? time : 0);
  drawVignette(ctx);

  if (run) {
    raf = requestAnimationFrame(frame);
  }
}

function resize() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const parent = canvas.parentElement;
  const cw = parent?.clientWidth || window.innerWidth;
  const ch = parent?.clientHeight || window.innerHeight;
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(cw * dpr);
  canvas.height = Math.floor(ch * dpr);
  canvas.style.width = `${cw}px`;
  canvas.style.height = `${ch}px`;
  const ctx = canvas.getContext("2d");
  if (ctx) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  rebuild(cw, ch);
  // one static paint if not animating
  if (!props.animate || reduced) {
    cancelAnimationFrame(raf);
    t0 = performance.now();
    frame(t0);
  }
}

function start() {
  cancelAnimationFrame(raf);
  t0 = 0;
  if (props.animate && !reduced) {
    raf = requestAnimationFrame(frame);
  } else {
    frame(performance.now());
  }
}

function onVis() {
  if (document.visibilityState === "hidden") {
    cancelAnimationFrame(raf);
  } else {
    start();
  }
}

onMounted(() => {
  reduced = prefersReduced();
  resize();
  start();
  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", onVis);
});

onUnmounted(() => {
  cancelAnimationFrame(raf);
  window.removeEventListener("resize", resize);
  document.removeEventListener("visibilitychange", onVis);
});

watch(
  () => props.animate,
  () => start(),
);
</script>

<template>
  <canvas ref="canvasRef" class="land-wow__canvas" aria-hidden="true" />
</template>
