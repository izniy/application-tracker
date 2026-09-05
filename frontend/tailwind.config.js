/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#070B16",
        deck: "#0D1424",
        panel: "#121B30",
        line: "#1F2A45",
        ink: "#E8EEF9",
        dim: "#7C8AA6",
        signal: "#5EE7FF",
        amber: "#FFB547",
        rose: "#FF6B8B",
        mint: "#4ADE80",
      },
      fontFamily: {
        display: ["Sora", "system-ui", "sans-serif"],
        body: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
