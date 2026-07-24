/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Warm sage/parchment reading-room palette — deliberately not the
        // cream-#F4F1EA-plus-terracotta combo that's become an AI-generated
        // default, and not a dark purple-gradient chat theme either.
        paper: "#F1F3EC",       // app background
        ink: "#20261F",         // primary text
        "ink-soft": "#4B5245",  // secondary text / metadata
        card: "#FDFDF9",        // message surfaces
        line: "#DCE0D2",        // hairline borders
        accent: "#C08A2E",      // ochre — user bubbles, send action
        "accent-dark": "#9A6E22",
        "accent-soft": "#F3E6CC",
        danger: "#B4432F",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      keyframes: {
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
        wave: {
          "0%, 60%, 100%": { transform: "translateY(0)" },
          "30%": { transform: "translateY(-4px)" },
        },
      },
      animation: {
        blink: "blink 1s step-start infinite",
        wave: "wave 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
