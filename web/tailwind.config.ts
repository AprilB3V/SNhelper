import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['DM Sans', 'sans-serif'], mono: ['DM Mono', 'monospace'], display: ['Space Grotesk', 'sans-serif'] },
    },
  },
  plugins: [],
} satisfies Config
