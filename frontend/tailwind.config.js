/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        astro: {
          bg: "#070b14",
          surface: "#0f172a",
          card: "#131d36",
          border: "#1e293b",
          accent: "#38bdf8",
          secondary: "#818cf8",
          infrared: "#f43f5e",
        }
      }
    },
  },
  plugins: [],
}
