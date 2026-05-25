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
        'neu-accent': '#6366f1',
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
    },
  },
  plugins: [],
}
