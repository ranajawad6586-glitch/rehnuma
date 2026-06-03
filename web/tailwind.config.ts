import type { Config } from "tailwindcss";

// Earthen palette (CLAUDE.md s.2) — deliberately NOT blue-classifieds.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        moss: { DEFAULT: "#1f5d4c", dark: "#16463a", light: "#2f7a64" },
        clay: { DEFAULT: "#c2703d", dark: "#a85b2c", light: "#d68a5c" },
        paper: { DEFAULT: "#f4efe4", dark: "#e8e0cd", deep: "#ded3ba" },
        ink: "#2a2722",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "serif"],
        body: ["var(--font-outfit)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 2px 8px rgba(42, 39, 34, 0.08)",
        lift: "0 6px 22px rgba(42, 39, 34, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
