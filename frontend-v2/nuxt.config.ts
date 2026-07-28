// TX BizFinder v2 — Nuxt 4. Misma UI que la SPA v1 pero con SSR (SEO real),
// i18n de Nuxt y PWA vía módulo oficial. El backend FastAPI no cambia.
import tailwindcss from '@tailwindcss/vite'

// Ruta del dashboard de leads. Se lee aquí (y no solo en runtimeConfig) porque
// routeRules y pages:extend se resuelven en build, antes de que exista runtime.
const BIZ_APP_PATH = (() => {
  const p = process.env.NUXT_PUBLIC_SUITE_BIZ_APP_PATH || '/app'
  return p.startsWith('/') ? p : `/${p}`
})()

export default defineNuxtConfig({
  // Fija el comportamiento del framework a esta fecha (sin sorpresas al actualizar)
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  modules: [
    '@nuxtjs/i18n',    // internacionalización EN/ES (reemplaza el useI18n casero)
    '@vite-pwa/nuxt',  // PWA instalable (reemplaza vite-plugin-pwa de la v1)
  ],

  // Hoja global: Tailwind v4 + clases de marca. El tema ya no vive en
  // tailwind.config.js sino en el bloque @theme de este mismo archivo.
  css: ['~/assets/css/style.css'],

  // Tailwind v4 vía su plugin de Vite (sin PostCSS ni autoprefixer: Lightning
  // CSS se encarga del prefijado). Es el modo que requiere Fase 5, porque un
  // Nuxt Layer solo puede compartir tema si éste es CSS-first (@theme).
  vite: {
    plugins: [tailwindcss()],
  },

  // Auto-import de componentes sin prefijo de carpeta (<LeadsDashboard> directo)
  components: [{ path: '~/components', pathPrefix: false }],

  i18n: {
    defaultLocale: 'en',       // inglés por defecto (igual que la v1)
    strategy: 'no_prefix',     // una sola URL por página, sin /es
    locales: [
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'es', name: 'Español', file: 'es.json' },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'txbf_locale',   // sustituye el localStorage txbf-locale de la v1
      alwaysRedirect: false,
      fallbackLocale: 'en',
    },
  },

  // PWA: mismo manifest y estrategia de caché que la v1 (vite.config.ts)
  pwa: {
    registerType: 'autoUpdate',                 // el SW se actualiza solo
    includeAssets: ['favicon.svg', 'apple-touch-icon.png', 'pwa-192.png', 'pwa-512.png'],
    manifest: {
      name: 'TX BizFinder',
      short_name: 'TXBizFinder',
      description: 'Find and qualify Texas small businesses. TABC alcohol data, 500K+ leads.',
      theme_color: '#0c1222',        // navy de la marca (barra del sistema)
      background_color: '#0c1222',
      display: 'standalone',         // sin chrome del navegador al instalarse
      orientation: 'portrait-primary',
      scope: '/',
      start_url: '/',
      id: '/',
      lang: 'en',
      categories: ['business', 'productivity'],
      icons: [
        { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
        { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
        { src: 'maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
      ],
    },
    workbox: {
      // Qué archivos precachea el service worker
      globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2,webmanifest}'],
      runtimeCaching: [
        {
          // La API con NetworkFirst: intenta red (8s) y cae al caché si no hay conexión
          urlPattern: /\/api\/.*/i,
          handler: 'NetworkFirst',
          options: {
            cacheName: 'txbizfinder-api',
            networkTimeoutSeconds: 8,
            expiration: { maxEntries: 32, maxAgeSeconds: 60 * 5 },
          },
        },
      ],
    },
    // Revisa actualizaciones del SW cada hora (sustituye el setInterval de main.ts v1)
    client: { periodicSyncForUpdates: 3600 },
    devOptions: { enabled: false },   // en dev no hace falta SW (evita cachés raras)
  },

  app: {
    head: {
      title: 'TX BizFinder — Find & qualify Texas small businesses',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Search 500K+ Texas small businesses: websites, social presence, TABC alcohol sales. Find leads without a modern website.',
        },
        { name: 'theme-color', content: '#0c1222' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
        // Fuentes de la marca (Fraunces display + DM Sans) — igual que la v1
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:wght@600;700&display=swap',
        },
      ],
    },
  },

  nitro: {
    // Dev: reenvía /api al FastAPI local (mismo proxy que tenía Vite en :5173)
    devProxy: {
      '/api': {
        target: process.env.NUXT_DEV_API_URL || 'http://127.0.0.1:8000/api',
        changeOrigin: true,
      },
    },
  },

  // Producción (Vercel): NUXT_API_PROXY_URL = Oracle API u origen del tunnel
  // (p. ej. https://api.txbizfinder.com). Nitro reenvía /api/** al backend —
  // el navegador habla con el mismo origen y no hay problemas de CORS.
  routeRules: {
    ...(process.env.NUXT_API_PROXY_URL
      ? {
          '/api/**': {
            proxy: `${String(process.env.NUXT_API_PROXY_URL).replace(/\/$/, '')}/api/**`,
          },
        }
      : {}),
    // /leads era la ruta vieja del dashboard
    '/leads': { redirect: BIZ_APP_PATH },
    // Si el dashboard se movió de /app, la ruta vieja redirige a la nueva
    ...(BIZ_APP_PATH !== '/app' ? { '/app': { redirect: BIZ_APP_PATH } } : {}),
  },

  hooks: {
    // La ruta del dashboard es configurable (era BIZ_APP_PATH en el router v1).
    // El file-based routing da /app por el archivo pages/app.vue; si el entorno
    // pide otra ruta, se registra aquí apuntando al MISMO componente.
    'pages:extend'(pages) {
      if (BIZ_APP_PATH === '/app') return
      const appPage = pages.find((p) => p.path === '/app')
      if (appPage) {
        pages.push({ ...appPage, name: 'biz-app', path: BIZ_APP_PATH })
      }
    },
  },

  runtimeConfig: {
    public: {
      // API key que la v1 leía de VITE_ADMIN_API_KEY (ahora NUXT_PUBLIC_ADMIN_API_KEY)
      adminApiKey: process.env.NUXT_PUBLIC_ADMIN_API_KEY || 'admin-dev-key-change-me',

      // Origen absoluto opcional de la API (p. ej. https://api.txbizfinder.com).
      // Vacío → mismo origen `/api/...`, que es lo normal aquí porque Nitro ya
      // hace de proxy (devProxy en dev, routeRules en prod).
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '',

      // Suite en un solo dominio (paths). Sin subdominios ni tunnel a PC.
      // Override opcional con NUXT_PUBLIC_SUITE_* si hace falta.
      suite: {
        wwwUrl: process.env.NUXT_PUBLIC_SUITE_WWW_URL || 'https://www.txbizfinder.com',
        bizAppPath: BIZ_APP_PATH,
        radarUrl: process.env.NUXT_PUBLIC_SUITE_RADAR_URL || 'https://www.txbizfinder.com/radar',
        channelUrl: process.env.NUXT_PUBLIC_SUITE_CHANNEL_URL || 'https://www.txbizfinder.com/channel',
        sentinelUrl: process.env.NUXT_PUBLIC_SUITE_SENTINEL_URL || 'https://www.txbizfinder.com/sentinel',
        floodUrl: process.env.NUXT_PUBLIC_SUITE_FLOOD_URL || 'https://www.txbizfinder.com/flood',
        powerUrl: process.env.NUXT_PUBLIC_SUITE_POWER_URL || 'https://www.txbizfinder.com/power',
        mapUrl: process.env.NUXT_PUBLIC_SUITE_MAP_URL || 'https://www.txbizfinder.com/map',
      },
    },
  },
})
