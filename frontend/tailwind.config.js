/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        electric: {
          50: '#e6f5ff',
          100: '#cdeafe',
          200: '#9cd5fd',
          300: '#6ac0fb',
          400: '#39aaf9',
          500: '#0ea5e9', // electric blue core
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e'
        },
        slatey: {
          50: '#f7f8fa',
          100: '#eef1f5',
          200: '#e3e7ee',
          300: '#d6dde7',
          400: '#c4cbd6',
          500: '#9aa3b2',
          600: '#6b7280',
          700: '#4b5563',
          800: '#374151',
          900: '#1f2937'
        },
        success: {
          DEFAULT: '#84cc16', // muted lime
        },
        warning: {
          DEFAULT: '#f59e0b', // warm orange
        },
      },
      borderRadius: {
        glass: '20px',
      },
      boxShadow: {
        glass: 'inset 0 1px 0 rgba(255,255,255,0.45), 0 8px 24px rgba(0,0,0,0.08)',
      },
      transitionDuration: {
        120: '120ms',
      },
    },
  },
  plugins: [],
}

