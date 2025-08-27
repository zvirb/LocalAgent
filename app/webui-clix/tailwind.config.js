/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0d1117',
          fg: '#f0f6fc',
          cursor: '#58a6ff',
          selection: '#264f78',
        },
        accent: {
          primary: '#58a6ff',
          secondary: '#a5a5a5',
          success: '#3fb950',
          warning: '#d29922',
          error: '#f85149',
          info: '#79c0ff'
        },
        surface: {
          100: '#161b22',
          200: '#21262d',
          300: '#30363d',
          400: '#484f58',
          500: '#6e7681',
        },
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#58a6ff',
          600: '#4493f8',
          700: '#316dca',
          800: '#1f2937',
          900: '#0d1117',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Roboto', 'sans-serif'],
      },
      fontSize: {
        'terminal-xs': ['11px', { lineHeight: '1.4' }],
        'terminal-sm': ['12px', { lineHeight: '1.4' }],
        'terminal-base': ['14px', { lineHeight: '1.4' }],
        'terminal-lg': ['16px', { lineHeight: '1.4' }],
        'terminal-xl': ['18px', { lineHeight: '1.4' }],
      },
      animation: {
        'cursor-blink': 'cursor-blink 1s infinite',
        'fade-in': 'fade-in 0.2s ease-out',
        'fade-out': 'fade-out 0.2s ease-in',
        'slide-in': 'slide-in 0.3s ease-out',
        'slide-out': 'slide-out 0.3s ease-in',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        'bounce-soft': 'bounce 1s infinite',
      },
      keyframes: {
        'cursor-blink': {
          '0%, 50%': { opacity: '1' },
          '51%, 100%': { opacity: '0' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        'slide-in': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-out': {
          '0%': { transform: 'translateX(0)', opacity: '1' },
          '100%': { transform: 'translateX(-100%)', opacity: '0' },
        },
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        DEFAULT: '8px',
        md: '12px',
        lg: '16px',
        xl: '24px',
        '2xl': '40px',
        '3xl': '64px',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      screens: {
        'xs': '475px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
        '3xl': '1920px',
        // Touch device specific
        'touch': { 'raw': '(hover: none) and (pointer: coarse)' },
        // High DPI
        'retina': { 'raw': '(-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi)' },
      },
      aspectRatio: {
        '4/3': '4 / 3',
        '21/9': '21 / 9',
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
    require('@tailwindcss/aspect-ratio'),
    require('@tailwindcss/typography'),
    // Custom plugin for terminal-specific utilities
    function({ addUtilities, theme }) {
      const newUtilities = {
        '.terminal-scrollbar': {
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: theme('colors.surface.100'),
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: theme('colors.surface.400'),
            borderRadius: '4px',
            '&:hover': {
              background: theme('colors.surface.500'),
            },
          },
          // Firefox scrollbar
          'scrollbar-width': 'thin',
          'scrollbar-color': `${theme('colors.surface.400')} ${theme('colors.surface.100')}`,
        },
        '.terminal-glow': {
          'box-shadow': `0 0 20px ${theme('colors.accent.primary')}40, inset 0 0 20px ${theme('colors.terminal.bg')}`,
        },
        '.drag-overlay': {
          'background': `linear-gradient(45deg, ${theme('colors.accent.primary')}20, ${theme('colors.accent.success')}20)`,
          'border': `2px dashed ${theme('colors.accent.primary')}`,
        },
        '.glass-morphism': {
          'background': 'rgba(22, 27, 34, 0.8)',
          'backdrop-filter': 'blur(12px)',
          'border': '1px solid rgba(255, 255, 255, 0.1)',
        }
      };
      addUtilities(newUtilities);
    }
  ],
};