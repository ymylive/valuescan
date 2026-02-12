/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--color-bg) / <alpha-value>)',
        foreground: 'hsl(var(--color-foreground) / <alpha-value>)',
        surface: {
          DEFAULT: 'hsl(var(--color-surface) / <alpha-value>)',
          muted: 'hsl(var(--color-surface-muted) / <alpha-value>)',
        },
        border: 'hsl(var(--color-border) / <alpha-value>)',
        muted: 'hsl(var(--color-muted) / <alpha-value>)',
        focus: 'hsl(var(--color-focus-ring) / <alpha-value>)',
        glass: {
          100: 'rgba(255, 255, 255, 0.05)',
          200: 'rgba(255, 255, 255, 0.1)',
          300: 'rgba(255, 255, 255, 0.2)',
          dark: 'rgba(0, 10, 5, 0.7)',
          border: 'rgba(255, 255, 255, 0.1)',
        },
        primary: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        }
      },
      fontFamily: {
        sans: ['"Space Grotesk"', '"Segoe UI"', '"Noto Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Consolas"', '"Courier New"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        shell: '14px',
      },
      boxShadow: {
        shell: '0 14px 38px -26px rgb(15 23 42 / 0.5)',
        'shell-dark': '0 18px 46px -28px rgb(2 6 23 / 0.82)',
      },
      backgroundImage: {
        'shell-radial': 'radial-gradient(circle at top left, rgba(34, 211, 238, 0.12), transparent 38%), radial-gradient(circle at top right, rgba(59, 130, 246, 0.1), transparent 35%)',
      }
    },
  },
  plugins: [],
}
