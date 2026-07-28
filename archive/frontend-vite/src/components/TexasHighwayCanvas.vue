<script setup lang="ts">
/**
 * Canvas #3 — Highway heat
 * Infinite Texas highway into a hot vanishing point: perspective road,
 * dashed lane lines rushing toward you, heat shimmer on the horizon.
 */
import { onMounted, onUnmounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    animate?: boolean;
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

let raf = 0;
let w = 0;
let h = 0;
let dpr = 1;
let t0 = 0;
let reduced = false;
let dashOffset = 0;

function isCoarse(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

function prefersReduced(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function drawSky(ctx: CanvasRenderingContext2D, time: number) {
  const g = ctx.createLinearGradient(0, 0, 0, h * 0.62);
  g.addColorStop(0, "#1a1412");
  g.addColorStop(0.4, "#2a1810");
  g.addColorStop(0.7, "#9a3412");
  g.addColorStop(0.88, "#f97316");
  g.addColorStop(1, "#fdba74");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h * 0.62);

  // Sun / heat core at vanishing region
  const vx = w * (0.5 + (props.pointerX - 0.5) * 0.06);
  const vy = h * 0.58 + Math.sin(time * 0.2) * 2;
  const sun = ctx.createRadialGradient(vx, vy, 0, vx, vy, Math.min(w, h) * 0.22);
  sun.addColorStop(0, "rgba(255, 230, 180, 0.65)");
  sun.addColorStop(0.25, "rgba(249, 115, 22, 0.4)");
  sun.addColorStop(0.55, "rgba(194, 65, 12, 0.15)");
  sun.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = sun;
  ctx.beginPath();
  ctx.arc(vx, vy, Math.min(w, h) * 0.22, 0, Math.PI * 2);
  ctx.fill();
}

function drawGround(ctx: CanvasRenderingContext2D) {
  const g = ctx.createLinearGradient(0, h * 0.58, 0, h);
  g.addColorStop(0, "#3f2a1a");
  g.addColorStop(0.25, "#1c1410");
  g.addColorStop(1, "#0c0a09");
  ctx.fillStyle = g;
  ctx.fillRect(0, h * 0.58, w, h * 0.42);
}

/**
 * Road as trapezoid into vanishing point (vx, vy).
 * Bottom full width-ish, top collapses to a thin segment at horizon.
 */
function roadEdges(vx: number, vy: number) {
  const botL = w * -0.05;
  const botR = w * 1.05;
  const botY = h + 10;
  // road mouth width near horizon
  const topHalf = Math.max(12, w * 0.018);
  return {
    botL,
    botR,
    botY,
    topL: vx - topHalf,
    topR: vx + topHalf,
    topY: vy,
  };
}

function drawRoad(ctx: CanvasRenderingContext2D, vx: number, vy: number) {
  const e = roadEdges(vx, vy);
  // asphalt
  ctx.beginPath();
  ctx.moveTo(e.botL, e.botY);
  ctx.lineTo(e.botR, e.botY);
  ctx.lineTo(e.topR, e.topY);
  ctx.lineTo(e.topL, e.topY);
  ctx.closePath();
  const g = ctx.createLinearGradient(0, e.topY, 0, e.botY);
  g.addColorStop(0, "#2a241f");
  g.addColorStop(0.4, "#1a1614");
  g.addColorStop(1, "#0f0d0c");
  ctx.fillStyle = g;
  ctx.fill();

  // soft shoulder glow
  ctx.strokeStyle = "rgba(249, 115, 22, 0.12)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(e.botL, e.botY);
  ctx.lineTo(e.topL, e.topY);
  ctx.moveTo(e.botR, e.botY);
  ctx.lineTo(e.topR, e.topY);
  ctx.stroke();
}

/** Perspective t in [0,1]: 0 = horizon, 1 = camera */
function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function drawLaneDashes(ctx: CanvasRenderingContext2D, vx: number, vy: number, offset: number) {
  const e = roadEdges(vx, vy);
  // center line of road in perspective
  const steps = isCoarse() ? 28 : 42;
  ctx.lineCap = "butt";

  for (let i = 0; i < steps; i++) {
    // parametric depth with speed offset
    let t0 = (i / steps + offset) % 1;
    let t1 = Math.min(1, t0 + 0.018 + t0 * 0.02);
    // ease so dashes denser near horizon
    const ease = (t: number) => t * t;
    const a = ease(t0);
    const b = ease(t1);

    const y0 = lerp(e.topY, e.botY, a);
    const y1 = lerp(e.topY, e.botY, b);
    const mid0 = lerp(vx, w * 0.5, a);
    const mid1 = lerp(vx, w * 0.5, b);

    // width of dash scales with depth
    const half0 = lerp(1.2, w * 0.012, a);
    const half1 = lerp(1.2, w * 0.012, b);

    const alpha = 0.25 + a * 0.55;
    ctx.fillStyle = `rgba(253, 186, 116, ${alpha})`;
    ctx.beginPath();
    ctx.moveTo(mid0 - half0, y0);
    ctx.lineTo(mid0 + half0, y0);
    ctx.lineTo(mid1 + half1, y1);
    ctx.lineTo(mid1 - half1, y1);
    ctx.closePath();
    ctx.fill();
  }

  // edge dashed guides (subtle)
  for (const side of [-1, 1] as const) {
    for (let i = 0; i < steps; i++) {
      let t0 = (i / steps + offset * 0.85 + 0.1) % 1;
      let t1 = Math.min(1, t0 + 0.012);
      const a = t0 * t0;
      const b = t1 * t1;
      const y0 = lerp(e.topY, e.botY, a);
      const y1 = lerp(e.topY, e.botY, b);
      const edge0 = side < 0 ? lerp(e.topL, e.botL, a) : lerp(e.topR, e.botR, a);
      const edge1 = side < 0 ? lerp(e.topL, e.botL, b) : lerp(e.topR, e.botR, b);
      const inset0 = lerp(2, 10, a) * side;
      const inset1 = lerp(2, 10, b) * side;
      ctx.strokeStyle = `rgba(249, 115, 22, ${0.08 + a * 0.2})`;
      ctx.lineWidth = 1 + a * 1.5;
      ctx.beginPath();
      ctx.moveTo(edge0 + inset0, y0);
      ctx.lineTo(edge1 + inset1, y1);
      ctx.stroke();
    }
  }
}

/** Heat shimmer: wavy distortion band on horizon (cheap fake — redraw sky strip with offset) */
function drawHeatShimmer(ctx: CanvasRenderingContext2D, time: number) {
  if (reduced) return;
  const bandY = h * 0.52;
  const bandH = h * 0.14;
  const slices = isCoarse() ? 24 : 40;
  const sliceH = bandH / slices;

  // grab already-drawn pixels from a temp approach: re-draw shimmer as translucent waves
  ctx.save();
  for (let i = 0; i < slices; i++) {
    const y = bandY + i * sliceH;
    const wave = Math.sin(time * 3.2 + i * 0.55) * (2.5 + (i / slices) * 2);
    const alpha = 0.04 + (1 - Math.abs(i / slices - 0.5) * 2) * 0.06;
    ctx.fillStyle = `rgba(255, 200, 120, ${alpha})`;
    ctx.fillRect(wave, y, w, sliceH + 1);
    // darker counter-wave for heat blur feel
    ctx.fillStyle = `rgba(12, 10, 9, ${alpha * 0.5})`;
    ctx.fillRect(-wave * 0.6, y, w, sliceH + 1);
  }
  ctx.restore();
}

function drawPoles(ctx: CanvasRenderingContext2D, vx: number, vy: number, time: number) {
  // occasional power poles receding into distance
  const poles = isCoarse() ? 5 : 8;
  for (let i = 0; i < poles; i++) {
    const t = ((i / poles + time * 0.04) % 1);
    const a = t * t;
    if (a < 0.08) continue;
    const y = lerp(vy, h * 0.95, a);
    const roadHalf = lerp(w * 0.02, w * 0.48, a);
    for (const side of [-1, 1] as const) {
      const x = vx + side * (roadHalf + lerp(8, 40, a));
      const ph = lerp(6, 55, a);
      ctx.strokeStyle = `rgba(40, 32, 28, ${0.25 + a * 0.45})`;
      ctx.lineWidth = 1 + a * 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x, y - ph);
      ctx.stroke();
      // crossbar
      ctx.beginPath();
      ctx.moveTo(x - ph * 0.15, y - ph * 0.75);
      ctx.lineTo(x + ph * 0.15, y - ph * 0.75);
      ctx.stroke();
    }
  }
}

function drawVignette(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.55, h * 0.1, w * 0.5, h * 0.55, h * 0.9);
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

  const vx = w * (0.5 + (props.pointerX - 0.5) * 0.08);
  const vy = h * (0.58 + (props.pointerY - 0.5) * 0.02);

  if (run) {
    dashOffset = (dashOffset + 0.008) % 1;
  }

  drawSky(ctx, run ? time : 0);
  drawGround(ctx);
  drawRoad(ctx, vx, vy);
  drawLaneDashes(ctx, vx, vy, dashOffset);
  drawPoles(ctx, vx, vy, run ? time : 0);
  drawHeatShimmer(ctx, run ? time : 0);
  drawVignette(ctx);

  if (run) raf = requestAnimationFrame(frame);
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
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  w = cw;
  h = ch;
  if (!props.animate || reduced) {
    cancelAnimationFrame(raf);
    t0 = performance.now();
    frame(t0);
  }
}

function start() {
  cancelAnimationFrame(raf);
  t0 = 0;
  if (props.animate && !reduced) raf = requestAnimationFrame(frame);
  else frame(performance.now());
}

function onVis() {
  if (document.visibilityState === "hidden") cancelAnimationFrame(raf);
  else start();
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
