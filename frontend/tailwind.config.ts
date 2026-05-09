import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        mist: "#f7f9ff",
        glass: "rgba(255,255,255,0.64)"
      },
      boxShadow: {
        glass: "0 18px 70px rgba(51, 65, 85, 0.14), inset 0 1px 0 rgba(255,255,255,0.7)",
        glow: "0 0 0 1px rgba(111, 132, 255, 0.26), 0 16px 50px rgba(120, 86, 255, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
