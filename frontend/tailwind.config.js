/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f2f2fd',
          100: '#e6e6fb',
          200: '#cdccf7',
          300: '#a6a3f0',
          400: '#8480e8',
          500: '#6a63e0',
          600: '#564fd1',
          700: '#4741ab',
          800: '#383488',
          900: '#26236b',
        }
      }
    },
  },
  plugins: [],
}
