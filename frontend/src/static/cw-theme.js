const tokens = require("./tokens");

const cwThemeVars = {
  "--edm-primary": tokens.brand.primary, // #3E5EB9
  "--edm-primary-hover": tokens.button.primaryHover, // #2C4383
  "--edm-primary-tint": tokens.brand.tint, // #ECEFF8
  "--edm-blue-700": tokens.brand.dark, // #1A274E
  "--edm-blue-100": tokens.brand.p100, // #C3CDE9
  "--edm-warning": tokens.semantic.warning, // #FAAD14
  "--edm-success": tokens.semantic.success, // #12B76A
  "--edm-danger": tokens.semantic.error, // #FF4D4F
  "--edm-text-primary": tokens.text.heading, // #020618
  "--edm-text-secondary": tokens.text.muted, // #3E4958
  "--edm-text-tertiary": tokens.text.tertiary, // #606060
  "--edm-page-bg": tokens.neutral.bg, // #FFFFFF
  "--edm-surface": tokens.neutral.white, // #FFFFFF
  "--edm-border-soft": tokens.table.border, // #EAECF0
  "--edm-border-strong": tokens.border.input, // #D0D5DD
  "--edm-font-sans": tokens.font.body, // var(--font-roboto)
};

module.exports = { cwThemeVars };
