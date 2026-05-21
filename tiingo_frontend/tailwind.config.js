/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { 500: '#22c55e', 600: '#16a34a' },
        surface: { 800: '#1e293b', 900: '#0f172a', 950: '#020617' },
      },
    },
  },
  plugins: [],
};
