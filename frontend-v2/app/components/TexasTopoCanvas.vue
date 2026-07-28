<script setup lang="ts">
/**
 * Fondo de la landing — terreno topográfico (Hill Country abstracto):
 * isolíneas de elevación animadas sobre grafito cálido.
 *
 * Todo el trabajo ocurre en onMounted, así que en SSR solo se emite el
 * <canvas> vacío y nada toca window/document.
 */
const props = withDefaults(
  defineProps<{
    animate?: boolean
    pointerX?: number
    pointerY?: number
  }>(),
  {
    animate: true,
    pointerX: 0.5,
    pointerY: 0.5,
  },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)

let raf = 0
let w = 0
let h = 0
let dpr = 1
let t0 = 0
let reduced = false

/** Campo de ruido por capas de senos (barato, sin dependencias). */
function noise2(x: number, y: number, t: number): number {
  return (
    Math.sin(x * 1.3 + t * 0.35) * 0.45 +
    Math.sin(y * 1.1 - t * 0.28) * 0.4 +
    Math.sin((x + y) * 0.9 + t * 0.22) * 0.35 +
    Math.sin(x * 2.4 - y * 1.7 + t * 0.5) * 0.2 +
    Math.sin(y * 3.1 + x * 0.6 - t * 0.18) * 0.15
  )
}

function isCoarse(): boolean {
  return window.matchMedia('(pointer: coarse)').matches
}

function prefersReduced(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function drawBackground(ctx: CanvasRenderingContext2D) {
  const g = ctx.createLinearGradient(0, 0, 0, h)
  g.addColorStop(0, '#100e0c')
  g.addColorStop(0.45, '#14110e')
  g.addColorStop(1, '#0c0a09')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)

  // Halo cálido que sigue suavemente al puntero
  const hx = w * (0.55 + (props.pointerX - 0.5) * 0.1)
  const hy = h * (0.4 + (props.pointerY - 0.5) * 0.08)
  const haze = ctx.createRadialGradient(hx, hy, 0, hx, hy, Math.max(w, h) * 0.55)
  haze.addColorStop(0, 'rgba(249, 115, 22, 0.09)')
  haze.addColorStop(0.5, 'rgba(245, 158, 11, 0.04)')
  haze.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = haze
  ctx.fillRect(0, 0, w, h)
}

/**
 * Marching squares simplificado: muestrea una rejilla del campo y dibuja
 * polilíneas por nivel interpolando los cruces en cada arista.
 *
 * El campo va en un Float64Array plano en vez de number[][]: el índice de un
 * TypedArray siempre es number (no number|undefined), así que pasa el
 * noUncheckedIndexedAccess del tsconfig de Nuxt sin sembrar aserciones `!`,
 * y de paso evita reservar miles de objetos por frame.
 */
function drawContours(ctx: CanvasRenderingContext2D, time: number) {
  const step = isCoarse() ? 18 : 12
  const cols = Math.ceil(w / step) + 1
  const rows = Math.ceil(h / step) + 1

  // El puntero desplaza el origen del campo (parallax)
  const ox = (props.pointerX - 0.5) * 1.2
  const oy = (props.pointerY - 0.5) * 0.9

  const field = new Float64Array(cols * rows)
  let minV = Infinity
  let maxV = -Infinity
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const nx = (i / cols) * 4.5 + ox
      const ny = (j / rows) * 4.5 + oy
      // Caída radial suave: el centro se lee como cuenca / elevación
      const cx = i / cols - 0.5
      const cy = j / rows - 0.5
      const ridge = Math.exp(-(cx * cx * 2.2 + cy * cy * 1.6)) * 0.8
      const v = noise2(nx, ny, time * 0.55) + ridge
      field[j * cols + i] = v
      if (v < minV) minV = v
      if (v > maxV) maxV = v
    }
  }

  const range = maxV - minV || 1
  const levels = isCoarse() ? 10 : 14

  // Puntos de cruce de la celda actual: hasta 4 pares (x,y)
  const pts = new Float64Array(8)

  for (let L = 0; L < levels; L++) {
    const iso = minV + ((L + 1) / (levels + 1)) * range
    // Color: profundo y frío abajo → cálido en las cumbres
    const t = L / (levels - 1)
    const alpha = 0.12 + t * 0.28
    const r = Math.floor(180 + t * 75)
    const g = Math.floor(80 + t * 70)
    const b = Math.floor(30 + t * 20)
    ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`
    ctx.lineWidth = t > 0.7 ? 1.35 : 1

    ctx.beginPath()
    for (let j = 0; j < rows - 1; j++) {
      for (let i = 0; i < cols - 1; i++) {
        // Los índices siempre caen dentro del array; el `?? 0` solo satisface
        // el noUncheckedIndexedAccess del tsconfig, no llega a dispararse.
        const v00 = field[j * cols + i] ?? 0
        const v10 = field[j * cols + i + 1] ?? 0
        const v01 = field[(j + 1) * cols + i] ?? 0
        const v11 = field[(j + 1) * cols + i + 1] ?? 0
        const x = i * step
        const y = j * step

        let n = 0
        const edge = (va: number, vb: number, x0: number, y0: number, x1: number, y1: number) => {
          if ((va < iso && vb >= iso) || (vb < iso && va >= iso)) {
            const u = (iso - va) / (vb - va || 1e-6)
            pts[n * 2] = x0 + (x1 - x0) * u
            pts[n * 2 + 1] = y0 + (y1 - y0) * u
            n++
          }
        }
        edge(v00, v10, x, y, x + step, y) // arriba
        edge(v10, v11, x + step, y, x + step, y + step) // derecha
        edge(v01, v11, x, y + step, x + step, y + step) // abajo
        edge(v00, v01, x, y, x, y + step) // izquierda

        if (n >= 2) {
          // Conecta los dos primeros (caso típico de un contorno simple)
          ctx.moveTo(pts[0] ?? 0, pts[1] ?? 0)
          ctx.lineTo(pts[2] ?? 0, pts[3] ?? 0)
          if (n >= 4) {
            ctx.moveTo(pts[4] ?? 0, pts[5] ?? 0)
            ctx.lineTo(pts[6] ?? 0, pts[7] ?? 0)
          }
        }
      }
    }
    ctx.stroke()
  }
}

/** Cotas de elevación dispersas (decorativas). */
function drawSpotHeights(ctx: CanvasRenderingContext2D, time: number) {
  if (isCoarse()) return
  const spots = 7
  ctx.font = '10px ui-monospace, monospace'
  ctx.textAlign = 'center'
  for (let i = 0; i < spots; i++) {
    const px = ((i * 0.137 + 0.12 + Math.sin(time * 0.1 + i) * 0.02) % 0.86) * w
    const py = ((i * 0.211 + 0.18 + Math.cos(time * 0.12 + i) * 0.02) % 0.72) * h
    const elev = 200 + Math.floor((noise2(px * 0.01, py * 0.01, time * 0.3) + 1.5) * 180)
    ctx.fillStyle = 'rgba(253, 186, 116, 0.28)'
    ctx.beginPath()
    ctx.arc(px, py, 1.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillStyle = 'rgba(253, 186, 116, 0.22)'
    ctx.fillText(String(elev), px, py - 6)
  }
}

function drawVignette(ctx: CanvasRenderingContext2D) {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.45, h * 0.1, w * 0.5, h * 0.5, h * 0.85)
  g.addColorStop(0, 'rgba(0,0,0,0)')
  g.addColorStop(1, 'rgba(9,9,11,0.58)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, w, h)
}

function frame(now: number) {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  if (!t0) t0 = now
  const time = (now - t0) / 1000
  const run = props.animate && !reduced

  drawBackground(ctx)
  drawContours(ctx, run ? time : 0)
  drawSpotHeights(ctx, run ? time : 0)
  drawVignette(ctx)

  if (run) raf = requestAnimationFrame(frame)
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const parent = canvas.parentElement
  const cw = parent?.clientWidth || window.innerWidth
  const ch = parent?.clientHeight || window.innerHeight
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.floor(cw * dpr)
  canvas.height = Math.floor(ch * dpr)
  canvas.style.width = `${cw}px`
  canvas.style.height = `${ch}px`
  const ctx = canvas.getContext('2d')
  if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  w = cw
  h = ch
  if (!props.animate || reduced) {
    cancelAnimationFrame(raf)
    t0 = performance.now()
    frame(t0)
  }
}

function start() {
  cancelAnimationFrame(raf)
  t0 = 0
  if (props.animate && !reduced) raf = requestAnimationFrame(frame)
  else frame(performance.now())
}

function onVis() {
  if (document.visibilityState === 'hidden') cancelAnimationFrame(raf)
  else start()
}

onMounted(() => {
  reduced = prefersReduced()
  resize()
  start()
  window.addEventListener('resize', resize, { passive: true })
  document.addEventListener('visibilitychange', onVis)
})

onUnmounted(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', onVis)
})

watch(
  () => props.animate,
  () => start(),
)
</script>

<template>
  <canvas ref="canvasRef" class="land-wow__canvas" aria-hidden="true" />
</template>
