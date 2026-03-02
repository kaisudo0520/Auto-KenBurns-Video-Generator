/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0a0f',
        'bg-secondary': '#12121a',
        'bg-tertiary': '#1a1a24',
        'bg-elevated': '#22222e',
        'accent-cyan': '#06b6d4',
        'accent-violet': '#8b5cf6',
        'accent-fuchsia': '#d946ef',
        'accent-amber': '#f59e0b',
      },
      fontFamily: {
        'display': ['Outfit', 'sans-serif'],
        'mono': ['Space Mono', 'monospace'],
      },
      animation: {
        'gradient': 'gradient 3s ease infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow-pulse 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'fade-in-up': 'fadeInUp 0.4s ease-out forwards',
        'fade-in-left': 'fadeInLeft 0.4s ease-out forwards',
        'fade-in-right': 'fadeInRight 0.4s ease-out forwards',
        'scale-in': 'scaleIn 0.3s ease-out forwards',
      },
      keyframes: {
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(6, 182, 212, 0.4), 0 0 40px rgba(139, 92, 246, 0.2)' },
          '50%': { boxShadow: '0 0 30px rgba(139, 92, 246, 0.5), 0 0 60px rgba(217, 70, 239, 0.3)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeInUp: {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInLeft: {
          from: { opacity: '0', transform: 'translateX(-20px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        fadeInRight: {
          from: { opacity: '0', transform: 'translateX(20px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 40px rgba(6, 182, 212, 0.3)',
        'glow-violet': '0 0 40px rgba(139, 92, 246, 0.3)',
        'glow-fuchsia': '0 0 40px rgba(217, 70, 239, 0.3)',
        'glow-lg': '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 30px rgba(139, 92, 246, 0.15)',
      },
    },
  },
  plugins: [],
}
