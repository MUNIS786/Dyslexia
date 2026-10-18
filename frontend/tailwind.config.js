/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Modern Light Design System Tokens
        brand: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1',
          600: '#4F46E5', // Primary brand indigo (12.8:1 contrast on white)
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
        },
        primary: {
          DEFAULT: '#4F46E5', // Accessible Indigo
          hover: '#4338CA',
          light: '#EEF2FF',
          legacy: '#1A6B6B', // Preserved for legacy components
        },
        secondary: {
          DEFAULT: '#0D9488', // Calming supportive teal
          hover: '#0F766E',
          light: '#F0FDFA',
        },
        accent: {
          DEFAULT: '#F59E0B', // Warm encouragement amber
          hover: '#D97706',
          light: '#FEF3C7',
          legacy: '#E8A020',
        },
        surface: '#FFFFFF',
        canvas: '#F8FAFC',
      },
      fontFamily: {
        dyslexic: ['Lexend', 'OpenDyslexic', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'card-hover': '0 4px 6px -1px rgba(0, 0, 0, 0.06), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
        'modal': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}

