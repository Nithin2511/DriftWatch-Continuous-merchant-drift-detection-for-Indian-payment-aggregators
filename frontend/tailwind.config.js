/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        razorpay: {
          50: '#f0f7ff',
          100: '#e0effe',
          500: '#0c83ff',
          600: '#0066e6',
          700: '#0052cc',
          800: '#003d99',
          900: '#002966',
          dark: '#0a101d',
          card: '#0f172a',
          border: '#1e293b',
        }
      }
    },
  },
  plugins: [],
}
