/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1A6B6B',
        accent: '#E8A020',
      },
      fontFamily: {
        dyslexic: ['Lexend', 'OpenDyslexic', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
