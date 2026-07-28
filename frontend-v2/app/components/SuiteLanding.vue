<script setup lang="ts">
/**
 * Landing cinemática de la suite. Las URLs de producto salen de useSuite()
 * (runtimeConfig), no de constantes de módulo como en la v1.
 */
import '~/assets/css/landing-wow.css'
import {
  STAR_TIP_LABELS,
  STAR_TIP_ORDER,
  SUITE_CREATOR,
  SUITE_PRODUCT_LABELS,
  SUITE_STEPS,
  suiteProductNameStrip,
} from '~/config/suite'
import type { SuiteProduct, SuiteProductId } from '~/config/suite'

const { t } = useI18n()
const { pointer } = usePointerField()
const { products, bizAppPath, getProduct } = useSuite()

const steps = SUITE_STEPS
const productNamesLine = suiteProductNameStrip()
const creator = SUITE_CREATOR

// Record con claves finitas: el acceso por id devuelve string, sin undefined
const PORTAL_COLORS: Record<SuiteProductId, string> = {
  biz: '#f97316',
  radar: '#ea580c',
  channel: '#fb923c',
  sentinel: '#f59e0b',
  flood: '#38bdf8',
  power: '#fbbf24',
  map: '#fdba74',
}

/** El centro de la estrella es Map Hub (la 7ª app). */
const mapCore = computed(() => getProduct('map'))

const STAR_N = 6 // FloodGuard arriba + 5 apps más

/** Estrella 2D fija: la punta 0 siempre arriba = FloodGuard Texas, luego horario. */
type StarTip = {
  id: string
  name: string
  domain: string
  href: string
  external: boolean
  color: string
  left: number
  top: number
  /** Empuje radial (px) para que la burbuja quede fuera del punto de color */
  outX: string
  outY: string
  product: SuiteProduct
}

const STAR_R = 40 // % desde el centro hasta los puntos de las puntas
/** Cuánto (px) se empujan las burbujas hacia fuera desde cada punta. */
const STAR_LABEL_OUT = 48

function tipXY(i: number, n = STAR_N) {
  const rad = ((-90 + i * (360 / n)) * Math.PI) / 180 // 0 = arriba
  const cos = Math.cos(rad)
  const sin = Math.sin(rad)
  return {
    left: 50 + STAR_R * cos,
    top: 50 + STAR_R * sin,
    outX: `${(cos * STAR_LABEL_OUT).toFixed(1)}px`,
    outY: `${(sin * STAR_LABEL_OUT).toFixed(1)}px`,
  }
}

const starTips = computed<StarTip[]>(() => {
  return STAR_TIP_ORDER.map((id, i) => {
    const p = getProduct(id)
    return {
      id: p.id,
      // En las puntas solo va el nombre corto (finder, radar, channel, …)
      name: STAR_TIP_LABELS[p.id],
      domain: STAR_TIP_LABELS[p.id],
      href: p.href,
      external: p.external,
      color: PORTAL_COLORS[p.id],
      product: p,
      ...tipXY(i),
    }
  })
})

/** Geometría SVG (viewBox 0 0 100 100), punta siempre arriba — estrella de 6. */
const starOutlinePoints = (() => {
  const pts: string[] = []
  for (let i = 0; i < STAR_N * 2; i++) {
    const r = i % 2 === 0 ? 40 : 18
    const a = -Math.PI / 2 + (i * Math.PI) / STAR_N
    pts.push(`${(50 + r * Math.cos(a)).toFixed(2)},${(50 + r * Math.sin(a)).toFixed(2)}`)
  }
  return pts.join(' ')
})()

const starTipSvg = Array.from({ length: STAR_N }, (_, i) => {
  const a = -Math.PI / 2 + (i * 2 * Math.PI) / STAR_N
  return { x: 50 + 40 * Math.cos(a), y: 50 + 40 * Math.sin(a) }
})

/** Conexiones suaves: anillo exterior + diagonales de dos en dos. */
const starLinks = (() => {
  const tips = starTipSvg
  const links: { d: string; kind: 'ring' | 'star' }[] = []
  for (let i = 0; i < STAR_N; i++) {
    const a = tips[i]
    const ring = tips[(i + 1) % STAR_N]
    const star = tips[(i + 2) % STAR_N]
    if (!a || !ring || !star) continue
    links.push({
      kind: 'ring',
      d: `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} L ${ring.x.toFixed(2)} ${ring.y.toFixed(2)}`,
    })
    links.push({
      kind: 'star',
      d: `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} L ${star.x.toFixed(2)} ${star.y.toFixed(2)}`,
    })
  }
  return links
})()

const isCoarse = ref(false)
const isFinePointer = ref(true)

function detectPointer() {
  isCoarse.value = window.matchMedia('(pointer: coarse)').matches
  isFinePointer.value = window.matchMedia('(hover: hover) and (pointer: fine)').matches
}

const cursorStyle = computed(() => {
  if (!isFinePointer.value) return { display: 'none' }
  return {
    transform: `translate3d(${pointer.px}px, ${pointer.py}px, 0)`,
    opacity: pointer.active ? 1 : 0,
  }
})

const stageParallax = computed(() => {
  if (!isFinePointer.value || !pointer.active) {
    return { transform: 'translate3d(0,0,0)' }
  }
  const x = (pointer.x - 0.5) * 18
  const y = (pointer.y - 0.5) * 12
  return { transform: `translate3d(${x}px, ${y}px, 0)` }
})

const primaryCta = ref<HTMLElement | null>(null)
const primaryStyle = ref<Record<string, string>>({})

function onPrimaryMove(e: PointerEvent) {
  if (!isFinePointer.value) return
  const el = primaryCta.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const cx = r.left + r.width / 2
  const cy = r.top + r.height / 2
  const dx = (e.clientX - cx) * 0.14
  const dy = (e.clientY - cy) * 0.16
  primaryStyle.value = { transform: `translate3d(${dx}px, ${dy}px, 0)` }
}

function onPrimaryLeave() {
  primaryStyle.value = { transform: 'translate3d(0,0,0)' }
}

/** Tilt 3D solo con puntero fino (ratón de escritorio). */
function onPortalMove(e: PointerEvent) {
  if (!isFinePointer.value) return
  const el = e.currentTarget as HTMLElement | null
  if (!el) return
  const r = el.getBoundingClientRect()
  const px = (e.clientX - r.left) / r.width
  const py = (e.clientY - r.top) / r.height
  el.style.setProperty('--mx', `${px * 100}%`)
  el.style.setProperty('--my', `${py * 100}%`)
  el.style.setProperty('--rx', `${(0.5 - py) * 10}deg`)
  el.style.setProperty('--ry', `${(px - 0.5) * 12}deg`)
}

function onPortalLeave(e: PointerEvent) {
  const el = e.currentTarget as HTMLElement | null
  if (!el) return
  el.style.setProperty('--rx', '0deg')
  el.style.setProperty('--ry', '0deg')
  el.style.setProperty('--mx', '50%')
  el.style.setProperty('--my', '50%')
  el.classList.remove('is-active')
}

/** Feedback al pulsar en táctil (en iOS/Android el :hover se queda pegado). */
function onPressStart(e: PointerEvent) {
  const el = e.currentTarget as HTMLElement | null
  if (!el) return
  if (e.pointerType === 'touch' || e.pointerType === 'pen') {
    el.classList.add('is-active', 'is-pressed')
  }
}

function onPressEnd(e: PointerEvent) {
  const el = e.currentTarget as HTMLElement | null
  if (!el) return
  el.classList.remove('is-active', 'is-pressed')
}

const marqueeItems = computed(() => {
  const base = products.value.map((p) => SUITE_PRODUCT_LABELS[p.id])
  const hook = t('suiteMarqueeHook')
  return [...base, hook, ...base, hook]
})

const stats = computed(() => [
  { value: '500K+', label: t('suiteStatLeads') },
  { value: String(products.value.length), label: t('suiteStatApps') },
  { value: '∞', label: t('suiteStatLayers') },
  { value: '100%', label: t('suiteStatVibe') },
])

const entered = ref(false)
const tabVisible = ref(true)
const starBoost = ref(false)
let boostTimer: ReturnType<typeof setTimeout> | null = null

/** Baja a la estrella y acelera un momento la animación de conexiones. */
function spinTheStack() {
  document.getElementById('suite-star')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  starBoost.value = true
  if (boostTimer) clearTimeout(boostTimer)
  boostTimer = setTimeout(() => {
    starBoost.value = false
  }, 2200)
}

function onVis() {
  tabVisible.value = document.visibilityState === 'visible'
}

onMounted(() => {
  detectPointer()
  window.matchMedia('(pointer: coarse)').addEventListener('change', detectPointer)
  window.matchMedia('(hover: hover) and (pointer: fine)').addEventListener('change', detectPointer)
  document.addEventListener('visibilitychange', onVis)
  requestAnimationFrame(() => {
    entered.value = true
  })
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVis)
  if (boostTimer) clearTimeout(boostTimer)
})

function portalColor(p: SuiteProduct) {
  return PORTAL_COLORS[p.id]
}
</script>

<template>
  <div
    class="land-wow"
    :class="{
      'land-wow--entered': entered,
      'land-wow--dim': !tabVisible,
      'land-wow--coarse': isCoarse,
    }"
  >
    <div class="land-wow__stage" :style="stageParallax" aria-hidden="true">
      <!-- Fondo: terreno topográfico -->
      <TexasTopoCanvas
        :animate="tabVisible"
        :pointer-x="pointer.x"
        :pointer-y="pointer.y"
      />
      <div class="land-wow__noise" />
    </div>
    <div
      class="land-wow__cursor"
      :class="{ 'is-off': !pointer.active }"
      :style="cursorStyle"
      aria-hidden="true"
    />

    <div class="land-wow__content">
      <header class="land-wow__nav">
        <a href="#top" class="land-wow__brand">
          <AppLogo size="sm" />
          <div class="land-wow__brand-text">
            <span class="land-wow__brand-kicker">{{ t('suiteBadge') }}</span>
            <span class="land-wow__brand-name">{{ t('suiteName') }}</span>
          </div>
        </a>
        <nav class="land-wow__nav-links" :aria-label="t('suiteName')">
          <a href="#portals">{{ t('suiteNavProducts') }}</a>
          <a href="#layers">{{ t('suiteNavHow') }}</a>
        </nav>
        <div class="land-wow__nav-actions">
          <ChromeToggles>
            <template #after>
              <NuxtLink
                :to="bizAppPath"
                class="land-wow__btn land-wow__btn--primary land-wow__nav-cta"
              >
                {{ t('suiteEnter') }}
              </NuxtLink>
            </template>
          </ChromeToggles>
        </div>
      </header>

      <section id="top" class="land-wow__hero">
        <div class="land-wow__pill">
          <span class="land-wow__pill-dot" aria-hidden="true" />
          {{ t('suiteBadge') }}
        </div>

        <h1 class="land-wow__title">
          <span class="land-wow__title-line">{{ t('suiteHeroTitle') }}</span>
          <span class="land-wow__title-line land-wow__title-line--glow">{{
            t('suiteHeroTitleGlow')
          }}</span>
        </h1>

        <p class="land-wow__lede">{{ t('suiteHeroBody') }}</p>

        <div class="land-wow__cta-row">
          <div
            ref="primaryCta"
            style="width: 100%"
            @pointermove="onPrimaryMove"
            @pointerleave="onPrimaryLeave"
          >
            <NuxtLink
              :to="bizAppPath"
              class="land-wow__btn land-wow__btn--primary"
              :style="primaryStyle"
              @pointerdown="onPressStart"
              @pointerup="onPressEnd"
              @pointercancel="onPressEnd"
              @pointerleave="onPressEnd"
            >
              {{ t('suiteCtaPrimary') }}
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.4"
                aria-hidden="true"
              >
                <path d="M5 12h14M13 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </NuxtLink>
          </div>
          <button
            type="button"
            class="land-wow__btn land-wow__btn--ghost"
            :aria-pressed="starBoost"
            @click="spinTheStack"
            @pointerdown="onPressStart"
            @pointerup="onPressEnd"
            @pointercancel="onPressEnd"
            @pointerleave="onPressEnd"
          >
            {{ t('suiteCtaSecondary') }}
          </button>
        </div>

        <!-- Estrella 2D (punta arriba) + enlaces en cada punta -->
        <div
          id="suite-star"
          class="land-wow__constellation"
          :class="{ 'land-wow__constellation--boost': starBoost }"
          aria-label="Suite star"
        >
          <div class="land-wow__star-scene">
            <svg
              class="land-wow__star-svg"
              viewBox="0 0 100 100"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="starFill2d" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#f97316" stop-opacity="0.16" />
                  <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.1" />
                </linearGradient>
              </defs>
              <polygon
                class="land-wow__star-shape"
                :points="starOutlinePoints"
                fill="url(#starFill2d)"
                stroke="rgba(253, 186, 116, 0.55)"
                stroke-width="1"
                stroke-linejoin="round"
              />
              <path
                v-for="(link, i) in starLinks"
                :key="i"
                class="land-wow__star-link"
                :class="
                  link.kind === 'star'
                    ? 'land-wow__star-link--diag'
                    : 'land-wow__star-link--ring'
                "
                :d="link.d"
                fill="none"
              />
            </svg>
            <div class="land-wow__sats">
              <!-- Núcleo central: MAP Hub -->
              <ProductLink
                :product="mapCore"
                class="land-wow__sat land-wow__sat--core"
                :style="{ '--sat-color': PORTAL_COLORS.map }"
                @pointerdown="onPressStart"
                @pointerup="onPressEnd"
                @pointercancel="onPressEnd"
                @pointerleave="onPressEnd"
              >
                <span class="land-wow__sat-bubble land-wow__sat-bubble--core">
                  <span class="land-wow__sat-name">MAP</span>
                </span>
              </ProductLink>

              <ProductLink
                v-for="tip in starTips"
                :key="tip.id"
                :product="tip.product"
                class="land-wow__sat"
                :class="{ 'land-wow__sat--top': tip.id === 'flood' }"
                :style="{
                  '--sat-color': tip.color,
                  '--out-x': tip.outX,
                  '--out-y': tip.outY,
                  left: `${tip.left}%`,
                  top: `${tip.top}%`,
                }"
                @pointerdown="onPressStart"
                @pointerup="onPressEnd"
                @pointercancel="onPressEnd"
                @pointerleave="onPressEnd"
              >
                <span class="land-wow__sat-dot" aria-hidden="true" />
                <span class="land-wow__sat-bubble">
                  <span class="land-wow__sat-name">{{ tip.name }}</span>
                </span>
              </ProductLink>
            </div>
          </div>
        </div>
      </section>

      <div class="land-wow__marquee" aria-hidden="true">
        <div class="land-wow__marquee-track">
          <span v-for="(item, i) in marqueeItems" :key="i" class="land-wow__marquee-item">
            <span>◆</span> {{ item }}
          </span>
        </div>
      </div>

      <div class="land-wow__stats">
        <RevealBlock v-for="(s, i) in stats" :key="s.label" :delay-class="`d${i + 1}`">
          <div class="land-wow__stat">
            <div class="land-wow__stat-value">{{ s.value }}</div>
            <div class="land-wow__stat-label">{{ s.label }}</div>
          </div>
        </RevealBlock>
      </div>

      <section id="portals" class="land-wow__section">
        <RevealBlock>
          <div class="land-wow__section-head">
            <div class="land-wow__section-kicker">01 — portals</div>
            <h2 class="land-wow__section-title">{{ t('suiteProductsTitle') }}</h2>
            <p class="land-wow__section-sub">{{ t('suiteProductsSubtitle') }}</p>
          </div>
        </RevealBlock>

        <div class="land-wow__portals">
          <RevealBlock
            v-for="(p, i) in products"
            :key="p.id"
            :delay-class="`d${(i % 4) + 1}`"
          >
            <ProductLink
              :product="p"
              class="land-wow__portal"
              :style="{ '--portal-color': portalColor(p) }"
              @pointermove="onPortalMove"
              @pointerleave="onPortalLeave"
              @pointerdown="onPressStart"
              @pointerup="onPressEnd"
              @pointercancel="onPressEnd"
            >
              <div class="land-wow__portal-top">
                <div class="land-wow__portal-icon">
                  <ProductIcon :icon="p.id" />
                </div>
              </div>
              <h3 class="land-wow__portal-name">{{ t(p.nameKey) }}</h3>
              <p class="land-wow__portal-blurb">{{ t(p.blurbKey) }}</p>
              <span class="land-wow__portal-cta">
                {{ t(p.ctaKey) }}
                <span aria-hidden="true">{{ p.external && p.sameOrigin === false ? '↗' : '→' }}</span>
              </span>
            </ProductLink>
          </RevealBlock>
        </div>
      </section>

      <section id="layers" class="land-wow__section land-wow__section--tight">
        <RevealBlock>
          <div class="land-wow__section-head">
            <div class="land-wow__section-kicker">02 — layers</div>
            <h2 class="land-wow__section-title">{{ t('suiteHowTitle') }}</h2>
            <p class="land-wow__section-sub">{{ t('suiteHowBody') }}</p>
          </div>
        </RevealBlock>

        <div class="land-wow__journey">
          <RevealBlock v-for="(step, i) in steps" :key="step.title" :delay-class="`d${i + 1}`">
            <article class="land-wow__step">
              <div class="land-wow__step-n">0{{ i + 1 }}</div>
              <h3 class="land-wow__step-title">{{ t(step.title) }}</h3>
              <p class="land-wow__step-body">{{ t(step.body) }}</p>
            </article>
          </RevealBlock>
        </div>
      </section>

      <footer class="land-wow__footer">
        <div class="land-wow__brand">
          <AppLogo size="sm" />
          <div class="land-wow__brand-text">
            <span class="land-wow__brand-name">{{ t('suiteName') }}</span>
            <span
              class="land-wow__brand-kicker"
              style="letter-spacing: 0.06em; text-transform: none; font-size: 0.72rem; opacity: 0.75"
            >
              {{ t('suiteFooterTag') }}
            </span>
          </div>
        </div>
        <div class="land-wow__footer-meta" style="display: flex; flex-direction: column; gap: 0.35rem; align-items: flex-end; text-align: right">
          <p style="margin: 0">{{ productNamesLine }}</p>
          <p style="margin: 0; opacity: 0.9">
            {{ t('suiteCreatedBy') }}
            <a
              :href="creator.url"
              target="_blank"
              rel="noopener noreferrer"
              style="color: inherit; font-weight: 600; text-decoration: underline; text-underline-offset: 2px"
            >{{ t('suiteCreatorName') }}</a>
            ·
            <a
              :href="creator.url"
              target="_blank"
              rel="noopener noreferrer"
              style="color: inherit; text-decoration: underline; text-underline-offset: 2px"
            >{{ creator.host }}</a>
          </p>
        </div>
      </footer>
    </div>
  </div>
</template>
