/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // PitWall's timing tower look (the 2026 redesign). One red accent, the rest
        // stays quiet so the numbers do the talking
        pw: {
          bg:      "#0F1217", // page
          panel:   "#141821", // panels and cards
          raised:  "#181C24", // switchers, input boxes, stat boxes
          line:    "#1E232C", // row dividers
          edge:    "#232833", // borders
          text:    "#E9ECF1", // main text
          muted:   "#8B93A3", // small text and labels
          red:     "#FF4D4D", // the accent: logo, active tab, 2x, best step, buttons
          safe:    "#5BE38A", // high confidence, PLAY, gains
          caution: "#F2C94C", // medium confidence, CONSIDER
          low:     "#FF7A7A", // low confidence, places lost, transfers out
          info:    "#7FA6FF", // AFTER QUALI, provisional
        },
      },
      fontFamily: {
        sans: ["Archivo", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
