/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0c1222",
          "navy-mid": "#1a2744",
          "navy-soft": "#243352",
          copper: "#c87941",
          "copper-light": "#e8a55c",
          "copper-dark": "#a8612f",
          teal: "#2a9d8f",
          "teal-light": "#3db8a9",
          sage: "#5a7d6a",
          sand: "#f8f6f2",
          cream: "#fdf9f3",
        },
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 24px -4px rgba(12, 18, 34, 0.12)",
        "card-dark": "0 8px 32px -8px rgba(0, 0, 0, 0.45)",
        glow: "0 0 24px -4px rgba(200, 121, 65, 0.35)",
      },
      animation: {
        "fade-up": "fadeUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both",
        "fade-in": "fadeIn 0.4s ease-out both",
        "slide-up": "slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) both",
        "stat-pop": "statPop 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both",
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
        "gradient-shift": "gradientShift 14s ease-in-out infinite",
        "blob-drift": "blobDrift 18s ease-in-out infinite",
        "bounce-in": "bounceIn 0.55s cubic-bezier(0.34, 1.4, 0.64, 1) both",
        "shake": "shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both",
        "glow-pulse": "glowPulse 2.5s ease-in-out infinite",
        "badge-pop": "badgePop 0.4s cubic-bezier(0.34, 1.4, 0.64, 1) both",
        "expand-in": "expandIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
        "number-pop": "numberPop 0.5s cubic-bezier(0.34, 1.4, 0.64, 1) both",
        "spin-slow": "spinSlow 8s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        statPop: {
          "0%": { opacity: "0", transform: "scale(0.88)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.65" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        gradientShift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        blobDrift: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(20px, 14px) scale(1.06)" },
        },
        bounceIn: {
          "0%": { opacity: "0", transform: "scale(0.92) translateY(8px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "20%": { transform: "translateX(-6px)" },
          "40%": { transform: "translateX(6px)" },
          "60%": { transform: "translateX(-4px)" },
          "80%": { transform: "translateX(4px)" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(42, 157, 143, 0)" },
          "50%": { boxShadow: "0 0 20px 2px rgba(42, 157, 143, 0.25)" },
        },
        badgePop: {
          "0%": { opacity: "0", transform: "scale(0.7)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        expandIn: {
          "0%": { opacity: "0", maxHeight: "0", transform: "scaleY(0.95)" },
          "100%": { opacity: "1", maxHeight: "500px", transform: "scaleY(1)" },
        },
        numberPop: {
          "0%": { opacity: "0.4", transform: "scale(0.85) translateY(4px)" },
          "60%": { transform: "scale(1.08) translateY(-2px)" },
          "100%": { opacity: "1", transform: "scale(1) translateY(0)" },
        },
        spinSlow: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
      },
    },
  },
  plugins: [],
};