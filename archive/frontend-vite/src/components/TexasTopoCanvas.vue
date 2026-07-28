<script setup lang="ts">
/**
 * Canvas #4 — Topo / contour terrain
 * Hill Country abstract: animated elevation isolines over warm graphite ground.
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

/** Simple layered value-noise-ish field (no deps). */
function noise2(x: number, y: number, t: number): number {
  // sum of sines — cheap pseudo-noise for contours
  return (
    Math.sin(x * 1.3 + t * 0.35) * 0.45 +
    Math.sin(y * 1.1 - t * 0.28) * 0.4 +
    Math.sin((x + y) * 0.9 + t * 0.22) * 0.35 +
    Math.sin(x * 2.4 - y * 1.7 + t * 0.5) * 0.2 +
    Math.sin(y * 3.1 + x * 0.6 - t * 0.18) * 0.15
  );
}

function isCoarse(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

function prefersReduced(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function drawBackground(ctx: CanvasRenderingContext2D) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#100e0c");
  g.addColorStop(0.45, "#14110e");
  g.addColorStop(1, "#0c0a09");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  // warm ambient
  const hx = w * (0.55 + (props.pointerX - 0.5) * 0.1);
  const hy = h * (0.4 + (props.pointerY - 0.5) * 0.08);
  const haze = ctx.createRadialGradient(hx, hy, 0, hx, hy, Math.max(w, h) * 0.55);
  haze.addColorStop(0, "rgba(249, 115, 22, 0.09)");
  haze.addColorStop(0.5, "rgba(245, 158, 11, 0.04)");
  haze.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = haze;
  ctx.fillRect(0, 0, w, h);
}

/**
 * Marching-squares-lite: sample a grid of field values, draw polylines
 * along iso-levels by interpolating edges.
 */
function drawContours(ctx: CanvasRenderingContext2D, time: number) {
  const step = isCoarse() ? 18 : 12;
  const cols = Math.ceil(w / step) + 1;
  const rows = Math.ceil(h / step) + 1;

  // parallax shifts the field origin
  const ox = (props.pointerX - 0.5) * 1.2;
  const oy = (props.pointerY - 0.5) * 0.9;

  // sample field
  const field: number[][] = [];
  let minV = Infinity;
  let maxV = -Infinity;
  for (let j = 0; j < rows; j++) {
    field[j] = [];
    for (let i = 0; i < cols; i++) {
      const nx = (i / cols) * 4.5 + ox;
      const ny = (j / rows) * 4.5 + oy;
      // slight radial falloff so center feels like a basin / rise
      const cx = i / cols - 0.5;
      const cy = j / rows - 0.5;
      const ridge = Math.exp(-(cx * cx * 2.2 + cy * cy * 1.6)) * 0.8;
      const v = noise2(nx, ny, time * 0.55) + ridge;
      field[j][i] = v;
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
    }
  }

  const range = maxV - minV || 1;
  const levels = isCoarse() ? 10 : 14;

  for (let L = 0; L < levels; L++) {
    const iso = minV + ((L + 1) / (levels + 1)) * range;
    // color: cooler depth → warmer peaks
    const t = L / (levels - 1);
    const alpha = 0.12 + t * 0.28;
    const r = Math.floor(180 + t * 75);
    const g = Math.floor(80 + t * 70);
    const b = Math.floor(30 + t * 20);
    ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
    ctx.lineWidth = t > 0.7 ? 1.35 : 1;

    ctx.beginPath();
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        const v00 = field[j][i];
        const v10 = field[j][i + 1];
        const v01 = field[j + 1][i];
        const v11 = field[j + 1][i + 1];
        const x = i * step;
        const y = j * step;

        // edges: bottom, right, top, left of cell — collect crossings
        const pts: { x: number; y: number }[] = [];
        const edge = (
          va: number,
          vb: number,
          x0: number,
          y0: number,
          x1: number,
          y1: number,
        ) => {
          if ((va < iso && vb >= iso) || (vb < iso && va >= iso)) {
            const u = (iso - va) / (vb - va || 1e-6);
            pts.push({ x: x0 + (x1 - x0) * u, y: y0 + (y1 - y0) * u });
          }
        };
        edge(v00, v10, x, y, x + step, y); // top
        edge(v10, v11, x + step, y, x + step, y + step); // right
        edge(v01, v11, x, y + step, x + step, y + step); // bottom
        edge(v00, v01, x, y, x, y + step); // left

        if (pts.length >= 2) {
          // connect first two (typical case for simple contours)
          ctx.moveTo(pts[0].x, pts[0].y);
          ctx.lineTo(pts[1].x, pts[1].y);
          if (pts.length >= 4) {
            ctx.moveTo(pts[2].x, pts[2].y);
            ctx.lineTo(pts[3].x, pts[3].y);
          }
        }
      }
    }
    ctx.stroke();
  }
}

/** Sparse elevation ticks (cosmetic) */
function drawSpotHeights(ctx: CanvasRenderingContext2D, time: number) {
  if (isCoarse()) return;
  const spots = 7;
  ctx.font = "10px ui-monospace, monospace";
  ctx.textAlign = "center";
  for (let i = 0; i < spots; i++) {
    const px = ((i * 0.137 + 0.12 + Math.sin(time * 0.1 + i) * 0.02) % 0.86) * w;
    const py = ((i * 0.211 + 0.18 + Math.cos(time * 0.12 + i) * 0.02) % 0.72) * h;
    const elev = 200 + Math.floor((noise2(px * 0.01, py * 0.01, time * 0.3) + 1.5) * 180);
    ctx.fillStyle = "rgba(253, 186, 116, 0.28)";
    ctx.beginPath();
    ctx.arc(px, py, 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "rgba(253, 186, 116, 0.22)";
    ctx.fillText(String(elev), px, py - 6);
  }
}

function drawVignette(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.45, h * 0.1, w * 0.5, h * 0.5, h * 0.85);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(9,9,11,0.58)");
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

  drawBackground(ctx);
  drawContours(ctx, run ? time : 0);
  drawSpotHeights(ctx, run ? time : 0);
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
