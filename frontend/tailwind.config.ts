import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      colors: {
        ink: {
          DEFAULT: "#0b1120",
          soft: "#1f2a44",
          muted: "#5b667a",
        },
        mist: "#f7f9ff",
        glass: {
          DEFAULT: "rgba(255,255,255,0.62)",
          strong: "rgba(255,255,255,0.78)",
          line: "rgba(255,255,255,0.7)",
        },
        iris: {
          cyan: "#7ce0ff",
          lavender: "#b8a8ff",
          pink: "#ffb6dc",
          peach: "#ffd4a8",
          indigo: "#7c5cff",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
      boxShadow: {
        glass:
          "0 24px 80px -20px rgba(31, 41, 55, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.85)",
        "glass-soft":
          "0 12px 40px -12px rgba(31, 41, 55, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.7)",
        glow:
          "0 0 0 1px rgba(124, 92, 255, 0.18), 0 22px 60px -18px rgba(124, 92, 255, 0.35)",
        "glow-soft":
          "0 0 0 1px rgba(124, 92, 255, 0.12), 0 14px 38px -16px rgba(124, 92, 255, 0.25)",
        "inner-highlight": "inset 0 1px 0 rgba(255, 255, 255, 0.85)",
      },
      backgroundImage: {
        "iris-gradient":
          "linear-gradient(120deg, #7c5cff 0%, #5b8cff 35%, #5fc8ff 65%, #ff9ed3 100%)",
        "iris-soft":
          "linear-gradient(135deg, rgba(124,92,255,0.16), rgba(95,200,255,0.14) 45%, rgba(255,158,211,0.16))",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-in": "fade-in 420ms cubic-bezier(0.22, 1, 0.36, 1) both",
        "shimmer": "shimmer 2.4s linear infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
