// TX BizFinder v2 — Nuxt 4. Misma UI que la SPA v1 pero con SSR (SEO real),
// i18n de Nuxt y PWA vía módulo oficial. El backend FastAPI no cambia.
export default defineNuxtConfig({
  // Fija el comportamiento del framework a esta fecha (sin sorpresas al actualizar)
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },

  modules: [
    '@nuxtjs/i18n',    // internacionalización EN/ES (reemplaza el useI18n casero)
    '@vite-pwa/nuxt',  // PWA instalable (reemplaza vite-plugin-pwa de la v1)
  ],

  // Hoja global: la MISMA style.css de la v1 (Tailwind v3 + clases de marca)
  css: ['~/assets/css/style.css'],

  // Tailwind v3 clásico vía PostCSS (la v1 usaba el mismo stack; el tema vive
  // en tailwind.config.js). Autoprefixer añade prefijos de navegador.
  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  },

  // Auto-import de componentes sin prefijo de carpeta (<LeadsDashboard> directo)
  components: [{ path: '~/components', pathPrefix: false }],

  i18n: {
    defaultLocale: 'en',       // inglés por defecto (igual que la v1)
    strategy: 'no_prefix',     // una sola URL por página, sin /es
    lazy: false,
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
    periodicSyncForUpdates: 3600,
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
      '/api': { target: 'http://127.0.0.1:8000/api', changeOrigin: true },
    },
  },

  // Producción: si NUXT_API_PROXY_URL está definido (p. ej. la URL de Render),
  // Nitro reenvía /api/** a ese backend — el navegador siempre habla con el
  // mismo origen y no hay problemas de CORS.
  routeRules: process.env.NUXT_API_PROXY_URL
    ? { '/api/**': { proxy: `${process.env.NUXT_API_PROXY_URL}/api/**` } }
    : {},

  runtimeConfig: {
    public: {
      // API key que la v1 leía de VITE_ADMIN_API_KEY (ahora NUXT_PUBLIC_ADMIN_API_KEY)
      adminApiKey: process.env.NUXT_PUBLIC_ADMIN_API_KEY || 'admin-dev-key-change-me',
    },
  },
})
