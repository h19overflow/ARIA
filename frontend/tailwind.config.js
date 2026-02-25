/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas:   '#101010',
        base:     '#141414',
        surface:  '#1a1a1a',
        elevated: '#212121',
        overlay:  '#2a2a2a',
        phase0:   '#7c6af7',
        phase1:   '#a855f7',
        phase2:   '#10b981',
        orange:   '#ee4f27',
        success:  '#22c55e',
        warning:  '#f59e0b',
        error:    '#ef4444',
        info:     '#3b82f6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'slide-up':    'slideInUp 0.2s ease-out',
        'slide-right': 'slideInRight 0.2s ease-out',
        'fade-in':     'fadeIn 0.3s ease-out',
        'pulse-dot':   'pulseDot 1.5s ease-in-out infinite',
        'spin-slow':   'spin 2s linear infinite',
        'glow-pulse':  'glowPulse 2s ease-in-out infinite',
        'node-appear': 'nodeAppear 0.25s ease-out',
        'shimmer':     'shimmer 1.6s linear infinite',
      },
      keyframes: {
        slideInUp:    { from: { transform: 'translateY(8px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        slideInRight: { from: { transform: 'translateX(-8px)', opacity: '0' }, to: { transform: 'translateX(0)', opacity: '1' } },
        fadeIn:       { from: { opacity: '0' }, to: { opacity: '1' } },
        pulseDot:     { '0%, 100%': { opacity: '1' }, '50%': { opacity: '0.3' } },
        glowPulse:    { '0%, 100%': { opacity: '0.6', transform: 'scale(1)' }, '50%': { opacity: '1', transform: 'scale(1.05)' } },
        nodeAppear:   { from: { opacity: '0', transform: 'scale(0.92)' }, to: { opacity: '1', transform: 'scale(1)' } },
        shimmer:      { from: { backgroundPosition: '-200% center' }, to: { backgroundPosition: '200% center' } },
      },
      boxShadow: {
        'glow-indigo': '0 0 20px rgba(99,102,241,0.3)',
        'glow-violet': '0 0 20px rgba(168,85,247,0.3)',
        'glow-green':  '0 0 20px rgba(16,185,129,0.3)',
        'glow-orange': '0 0 20px rgba(255,109,90,0.3)',
      },
    },
  },
  plugins: [],
}
