<script setup lang="ts">
/**
 * Canvas #2 — Suite constellation
 * Four star-clusters (Biz · Radar · Channel · Sentinel) linked like a data sky over Texas night.
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

type Star = {
  ox: number; // 0–1 of cluster box
  oy: number;
  r: number;
  phase: number;
  speed: number;
  bright: number;
};

type Cluster = {
  id: string;
  cx: number; // 0–1 viewport
  cy: number;
  scale: number;
  color: string;
  stars: Star[];
  edges: [number, number][];
};

const CLUSTER_COLORS = ["#f97316", "#ea580c", "#fb923c", "#f59e0b"] as const;
const CLUSTER_IDS = ["biz", "radar", "channel", "sentinel"] as const;

/** Relative star layouts (normalized in unit square) — abstract “constellations” */
const LAYOUTS: { stars: [number, number][]; edges: [number, number][] }[] = [
  // Biz — search / diamond
  {
    stars: [
      [0.5, 0.12],
      [0.18, 0.42],
      [0.82, 0.42],
      [0.35, 0.72],
      [0.65, 0.72],
      [0.5, 0.92],
    ],
    edges: [
      [0, 1],
      [0, 2],
      [1, 3],
      [2, 4],
      [3, 5],
      [4, 5],
      [1, 2],
    ],
  },
  // Radar — ring / sweep
  {
    stars: [
      [0.5, 0.5],
      [0.5, 0.15],
      [0.82, 0.32],
      [0.85, 0.68],
      [0.5, 0.88],
      [0.15, 0.68],
      [0.18, 0.32],
    ],
    edges: [
      [0, 1],
      [0, 2],
      [0, 3],
      [0, 4],
      [0, 5],
      [0, 6],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
      [5, 6],
      [6, 1],
    ],
  },
  // Channel — wave
  {
    stars: [
      [0.1, 0.55],
      [0.28, 0.35],
      [0.45, 0.58],
      [0.62, 0.32],
      [0.78, 0.55],
      [0.92, 0.4],
      [0.5, 0.78],
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
      [2, 6],
      [3, 6],
    ],
  },
  // Sentinel — shield
  {
    stars: [
      [0.5, 0.1],
      [0.15, 0.35],
      [0.85, 0.35],
      [0.2, 0.7],
      [0.8, 0.7],
      [0.5, 0.92],
      [0.5, 0.48],
    ],
    edges: [
      [0, 1],
      [0, 2],
      [1, 3],
      [2, 4],
      [3, 5],
      [4, 5],
      [1, 6],
      [2, 6],
      [6, 5],
    ],
  },
];

let raf = 0;
let clusters: Cluster[] = [];
let dust: { x: number; y: number; a: number; s: number }[] = [];
let w = 0;
let h = 0;
let dpr = 1;
let t0 = 0;
let reduced = false;

function isCoarse(): boolean {
  return window.matchMedia("(pointer: coarse)").matches;
}

function prefersReduced(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function rebuild(cw: number, ch: number) {
  w = cw;
  h = ch;
  const positions: [number, number][] = [
    [0.28, 0.32],
    [0.72, 0.3],
    [0.3, 0.68],
    [0.7, 0.7],
  ];
  const scale = Math.min(cw, ch) * (isCoarse() ? 0.22 : 0.26);

  clusters = LAYOUTS.map((layout, i) => {
    const [cx, cy] = positions[i];
    const stars: Star[] = layout.stars.map(([ox, oy]) => ({
      ox,
      oy,
      r: 1.4 + Math.random() * 2.2,
      phase: Math.random() * Math.PI * 2,
      speed: 0.7 + Math.random() * 1.3,
      bright: 0.55 + Math.random() * 0.45,
    }));
    return {
      id: CLUSTER_IDS[i],
      cx,
      cy,
      scale,
      color: CLUSTER_COLORS[i],
      stars,
      edges: layout.edges,
    };
  });

  const dustN = isCoarse() ? 40 : 90;
  dust = Array.from({ length: dustN }, () => ({
    x: Math.random() * cw,
    y: Math.random() * ch,
    a: 0.08 + Math.random() * 0.2,
    s: 0.6 + Math.random() * 1.4,
  }));
}

function starXY(c: Cluster, s: Star): { x: number; y: number } {
  const px = (props.pointerX - 0.5) * 18;
  const py = (props.pointerY - 0.5) * 12;
  return {
    x: c.cx * w + (s.ox - 0.5) * c.scale + px * (0.4 + c.cx * 0.3),
    y: c.cy * h + (s.oy - 0.5) * c.scale + py * (0.35 + c.cy * 0.25),
  };
}

function drawBackground(ctx: CanvasRenderingContext2D) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#0c0a09");
  g.addColorStop(0.45, "#12100e");
  g.addColorStop(1, "#1a120c");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  // faint warm haze
  const haze = ctx.createRadialGradient(w * 0.5, h * 0.35, 0, w * 0.5, h * 0.4, h * 0.7);
  haze.addColorStop(0, "rgba(249, 115, 22, 0.06)");
  haze.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = haze;
  ctx.fillRect(0, 0, w, h);
}

function drawDust(ctx: CanvasRenderingContext2D, time: number) {
  for (const d of dust) {
    const tw = 0.5 + 0.5 * Math.sin(time * d.s + d.x * 0.01);
    ctx.fillStyle = `rgba(253, 186, 116, ${d.a * tw})`;
    ctx.beginPath();
    ctx.arc(d.x, d.y, d.s * 0.6, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawBridge(ctx: CanvasRenderingContext2D, time: number) {
  // faint links between constellation centers (suite network)
  ctx.lineWidth = 1;
  for (let i = 0; i < clusters.length; i++) {
    for (let j = i + 1; j < clusters.length; j++) {
      const a = clusters[i];
      const b = clusters[j];
      const ax = a.cx * w;
      const ay = a.cy * h;
      const bx = b.cx * w;
      const by = b.cy * h;
      const pulse = 0.04 + 0.03 * Math.sin(time * 0.6 + i + j);
      const grad = ctx.createLinearGradient(ax, ay, bx, by);
      grad.addColorStop(0, `rgba(249, 115, 22, ${pulse})`);
      grad.addColorStop(0.5, `rgba(253, 186, 116, ${pulse * 1.4})`);
      grad.addColorStop(1, `rgba(245, 158, 11, ${pulse})`);
      ctx.strokeStyle = grad;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }
  }
}

function drawCluster(ctx: CanvasRenderingContext2D, c: Cluster, time: number) {
  const pts = c.stars.map((s) => starXY(c, s));

  // edges
  ctx.lineWidth = 1.15;
  ctx.lineCap = "round";
  for (const [ia, ib] of c.edges) {
    const a = pts[ia];
    const b = pts[ib];
    if (!a || !b) continue;
    const alpha = 0.18 + 0.1 * Math.sin(time * 0.8 + ia + ib);
    ctx.strokeStyle = hexAlpha(c.color, alpha);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }

  // nodes
  c.stars.forEach((s, i) => {
    const p = pts[i];
    if (!p) return;
    const pulse = 0.55 + 0.45 * Math.sin(time * s.speed + s.phase);
    const r = s.r * (0.75 + pulse * 0.55) * s.bright;
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 4);
    glow.addColorStop(0, hexAlpha(c.color, 0.55 * pulse));
    glow.addColorStop(0.4, hexAlpha(c.color, 0.18 * pulse));
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(p.x, p.y, r * 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = hexAlpha("#fdba74", 0.75 + 0.25 * pulse);
    ctx.beginPath();
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
    ctx.fill();
  });
}

function hexAlpha(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, a))})`;
}

function drawVignette(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.45, h * 0.12, w * 0.5, h * 0.5, h * 0.82);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(9,9,11,0.62)");
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
  drawDust(ctx, run ? time : 0);
  drawBridge(ctx, run ? time : 0);
  for (const c of clusters) drawCluster(ctx, c, run ? time : 0);
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
  rebuild(cw, ch);
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
