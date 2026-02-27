/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Industrial CAD Theme - Dark Mode Primary
        industrial: {
          bg: {
            primary: '#0E1A26',    // Deep navy - main background
            secondary: '#132738',   // Slightly lighter for cards
            surface: '#123A5F',    // Surface/Cards - elevated UI (US-16001 spec)
            elevated: '#1A3348',    // Elevated surfaces
            hover: '#1F3D52',      // Hover states
          },
          text: {
            primary: '#F4F7FA',    // High contrast white
            secondary: '#9FB2C8',  // Muted gray-blue
            muted: '#6B7F95',      // Very muted
          },
          border: {
            DEFAULT: '#2A3A4A',    // Subtle lines
            strong: '#3D5269',     // Stronger borders
          },
          accent: {
            ai: '#21C4F3',         // Bright cyan - AI accent
            blue: '#1F6FDB',       // Trustworthy blue
            success: '#2EE6C8',    // Confirmations/success
            warning: '#F59E0B',    // Warnings
            error: '#E53935',      // Errors
          },
        },
        // Brand colors from AssemblematicAI logo
        brand: {
          navy: '#0d1526',      // Dark navy background
          cyan: '#22d3ee',      // Bright cyan accent (AI)
          blue: '#3b82f6',      // Primary blue
          'blue-dark': '#1d4ed8',
          'blue-darker': '#1e3a8a',
          silver: '#94a3b8',    // Gear silver
          'silver-dark': '#64748b',
        },
        // Primary palette (blue)
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Accent palette (cyan)
        accent: {
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
        },
        // Surface colors (dark theme)
        surface: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#0d1526',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #0d1526 0%, #1e293b 100%)',
        'gradient-accent': 'linear-gradient(135deg, #3b82f6 0%, #22d3ee 100%)',
      },
    },
  },
  plugins: [],
};
