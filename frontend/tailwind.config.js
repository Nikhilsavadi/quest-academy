/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        questPurple: '#7c3aed',
        questAmber: '#f59e0b',
        questGreen: '#10b981',
      },
      animation: {
        'float-up': 'floatUp 600ms ease-out forwards',
        'shake': 'shake 200ms ease-in-out',
        'pulse-streak': 'pulseStreak 1s ease-in-out',
        'badge-pop': 'badgePop 500ms ease-out',
        'level-burst': 'levelBurst 800ms ease-out',
        'confetti': 'confetti 1.5s ease-out forwards',
        'flash-green': 'flashGreen 300ms ease-out',
        'flash-red': 'flashRed 300ms ease-out',
      },
      keyframes: {
        floatUp: {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(-40px)', opacity: '0' },
        },
        shake: {
          '0%,100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-6px)' },
          '75%': { transform: 'translateX(6px)' },
        },
        pulseStreak: {
          '0%,100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
        },
        badgePop: {
          '0%': { transform: 'scale(0)' },
          '60%': { transform: 'scale(1.2)' },
          '100%': { transform: 'scale(1)' },
        },
        levelBurst: {
          '0%': { transform: 'scale(0.5)', opacity: '0' },
          '50%': { transform: 'scale(1.1)', opacity: '1' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        confetti: {
          '0%': { transform: 'translateY(-20vh) rotate(0deg)', opacity: '1' },
          '100%': { transform: 'translateY(110vh) rotate(720deg)', opacity: '0' },
        },
        flashGreen: {
          '0%,100%': { backgroundColor: 'transparent' },
          '50%': { backgroundColor: '#10b98144' },
        },
        flashRed: {
          '0%,100%': { backgroundColor: 'transparent' },
          '50%': { backgroundColor: '#ef444444' },
        },
      },
    },
  },
  plugins: [],
}
