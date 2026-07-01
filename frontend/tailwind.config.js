const tokens = require("./src/static/tokens");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: tokens.brand.primary,
        brandDark: tokens.brand.dark,
        brandMuted: tokens.brand.muted,
        brandLight: tokens.brand.light,
        brandTint: tokens.brand.tint,
        navHover: tokens.nav.hover,
        navActive: tokens.nav.active,
        success: tokens.semantic.success,
        successFg: tokens.semantic.successFg,
        successBg: tokens.semantic.successBg,
        tableBorder: tokens.border.table,
        inputBorder: tokens.border.input,
        inputBorderActive: tokens.input.borderActive,
        focusRing: tokens.select.focusRing,
        status: tokens.status,
      },
      borderRadius: {
        // Additive only — DEFAULT left untouched so existing `rounded` usages
        // are pixel-equivalent. Radius adoption is UI-1 pass 2.
        md: `${tokens.radius.md}px`,
        pill: `${tokens.radius.pill}px`,
      },
      backgroundImage: {
        "image-login": "url('/images/bg-image-login.png')",
      },
      maxWidth: {
        "8xl": "90rem",
        "9xl": "120rem",
        "10xl": "150rem",
      },
    },
    container: {
      center: true,
      padding: {
        DEFAULT: "1rem",
        sm: "2rem", // 640px
        md: "3rem", // 768px
        lg: "3rem", // 1024px
        xl: "4rem", // 1280px
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: true,
  },
};
