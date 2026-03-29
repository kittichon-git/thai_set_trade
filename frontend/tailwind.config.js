/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      animation: {
        'flash-up': 'flash-green 0.8s ease-out',
        'flash-down': 'flash-red 0.8s ease-out',
        'pulse-live': 'pulse-live 1.5s ease-in-out infinite',
        'slide-down': 'slide-down 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
      },
      keyframes: {
        'flash-green': {
          '0%, 100%': { background: 'transparent' },
          '50%': { background: 'rgba(16, 185, 129, 0.2)' },
        },
        'flash-red': {
          '0%, 100%': { background: 'transparent' },
          '50%': { background: 'rgba(239, 68, 68, 0.2)' },
        },
        'pulse-live': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.25' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
