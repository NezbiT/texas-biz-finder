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
        "fade-up": "fadeUp 0.14s cubic-bezier(0.33, 1, 0.68, 1) both",
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
        shimmer: "shimmer 2.2s linear infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.65" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
    },
  },
  plugins: [],
};