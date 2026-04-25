import type { Config } from "tailwindcss";

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        /** Skyscanner core (cards, text) */
        "ss-navy": "#071D3D",
        "ss-navy-light": "#0F2F52",
        "ss-navy-deep": "#051018",
        "ss-accent": "#0062E3",
        "ss-accent-hover": "#0050C4",
        /** Results page canvas */
        "ss-page": "#EBECEE",
        "ss-orange": "#FF6600",
        vibe: {
          ink: "#071D3D",
          mist: "#e8edf4",
          line: "#c5d4e8",
        },
      },
      borderRadius: {
        ss: "10px",
      },
      boxShadow: {
        card: "0 2px 8px rgb(0 0 0 / 8%), 0 8px 24px rgb(7 29 61 / 6%)",
        "card-hover": "0 4px 12px rgb(0 0 0 / 10%), 0 12px 32px rgb(7 29 61 / 8%)",
        glow: "0 0 28px -4px rgb(0 98 227 / 28%)",
      },
      backgroundImage: {
        "btn-primary":
          "linear-gradient(180deg, #0b6ef0 0%, #0062e3 55%, #0058cc 100%)",
      },
    },
  },
  plugins: [],
} satisfies Config;
