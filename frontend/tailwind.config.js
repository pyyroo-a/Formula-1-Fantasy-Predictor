/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // PitWall "race engineering" palette — near-black panels, red accent.
        pw: {
          bg:     "#05070c", // page background
          panel:  "#0a0d14", // card / panel surface
          panel2: "#0b0e14", // header / alt surface
          red:    "#ff5c5c", // primary accent
          muted:  "#828a99", // secondary text / labels
          safe:   "#4ade80", // safe pick / positive
          risk:   "#eab308", // risky pick / caution
          rain:   "#5b93ff", // rain / info
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "Menlo", "Monaco", "Consolas", "Liberation Mono", "monospace"],
      },
    },
  },
  plugins: [],
}
