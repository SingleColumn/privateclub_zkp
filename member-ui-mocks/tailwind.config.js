/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0f1115',
          elevated: '#181b22',
          border: '#2a2e38',
        },
        accent: {
          DEFAULT: '#4ade80',
          muted: '#22c55e',
        },
        danger: '#ef4444',
        warning: '#eab308',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
