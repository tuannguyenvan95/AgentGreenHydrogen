/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        h2dark: {
          950: '#030A0F',
          900: '#061118', // Base Clean Industrial Teal & Graphite
          850: '#091820',
          800: '#0C1E28', // Elevated Card Surface dark slate
          750: '#112936',
          700: '#173647',
          600: '#1F475C',
          500: '#2C627E',
        },
        cryo: {
          cyan: '#06B6D4', // Cryogenic Cyan
          glow: 'rgba(6, 182, 212, 0.25)',
          deep: '#0891B2',
        },
        puregreen: {
          emerald: '#10B981', // ISO 14687 Certified Pure Green
          glow: 'rgba(16, 185, 129, 0.25)',
          dark: '#059669',
        },
        penalty: {
          amber: '#F59E0B', // Partial Carbon Intensity Penalty
          glow: 'rgba(245, 158, 11, 0.25)',
        },
        graybreach: {
          crimson: '#EF4444', // Disqualified Gray Hydrogen
          glow: 'rgba(239, 68, 68, 0.25)',
        },
        solar: {
          lime: '#EAB308',
          glow: 'rgba(234, 179, 8, 0.25)',
        },
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'cryo-glow': '0 0 25px -4px rgba(6, 182, 212, 0.35)',
        'green-glow': '0 0 25px -4px rgba(16, 185, 129, 0.35)',
        'amber-glow': '0 0 25px -4px rgba(245, 158, 11, 0.35)',
        'crimson-glow': '0 0 25px -4px rgba(239, 68, 68, 0.35)',
        'console': 'inset 0 0 30px rgba(6, 182, 212, 0.03), 0 10px 30px -10px rgba(0, 0, 0, 0.8)',
      },
    },
  },
  plugins: [],
};
