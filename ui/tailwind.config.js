/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'neu-bg': '#e0e5ec',
        'neu-dark': '#a3b1c6',
        'neu-light': '#ffffff',
        'neu-accent': '#f59e0b',
      },
      boxShadow: {
        'neu-out': '8px 8px 16px #a3b1c6, -8px -8px 16px #ffffff',
        'neu-in': 'inset 8px 8px 16px #a3b1c6, inset -8px -8px 16px #ffffff',
        'neu-out-sm': '4px 4px 8px #a3b1c6, -4px -4px 8px #ffffff',
        'neu-in-sm': 'inset 4px 4px 8px #a3b1c6, inset -4px -4px 8px #ffffff',
      },
      borderRadius: {
        'neu': '20px',
        'neu-sm': '12px',
      },
      animation: {
        'gradient-shift': 'gradient-shift 15s ease infinite',
        'spin-slow': 'spin 8s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'pulse': 'pulse 4s ease-in-out infinite',
      },
      keyframes: {
        'gradient-shift': {
          '0%, 100%': {
            'background-position': '0% 50%',
          },
          '50%': {
            'background-position': '100% 50%',
          },
        },
        'float': {
          '0%, 100%': {
            transform: 'translateY(0px)',
          },
          '50%': {
            transform: 'translateY(-20px)',
          },
        },
      },
    },
  },
  plugins: [],
}
