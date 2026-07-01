import tokens from "@/static/tokens";

/**
 * Ant Design 5 ConfigProvider theme, derived from the token source (UI-1).
 * Structurally identical to the previously-inlined theme in layout.js —
 * borderRadius stays 0 (pass 1, pixel-equivalent).
 */
const antTheme = {
  token: {
    borderRadius: 0,
    fontFamily: "inherit",
    fontFamilyCode: "--font-geist-sans",
    colorPrimary: tokens.brand.primary,
    colorLink: tokens.brand.primary,
  },
  components: {
    Button: {
      // Primary (Figma node 3019:7379)
      colorPrimaryHover: tokens.button.primaryHover,
      colorPrimaryActive: tokens.button.primaryActive,
      // Secondary / default
      defaultBg: tokens.neutral.white,
      defaultColor: tokens.button.secondaryText,
      defaultBorderColor: tokens.button.secondaryBorder,
      defaultHoverBg: tokens.button.secondaryHoverBg,
      defaultHoverColor: tokens.button.secondaryHoverText,
      defaultHoverBorderColor: tokens.button.secondaryBorder,
      defaultActiveBg: tokens.button.secondaryActiveBg,
      defaultActiveColor: tokens.button.secondaryText,
      defaultActiveBorderColor: tokens.button.secondaryBorder,
      // Link / text (Ghost) — scoped to Button so global links are unaffected
      colorLink: tokens.button.linkText,
      colorLinkHover: tokens.button.linkHover,
      colorLinkActive: tokens.button.linkActive,
      // Figma button spec (44px / 24px / 14px) applied to BOTH default and large
      controlHeight: tokens.button.xlHeight,
      paddingInline: tokens.button.xlPaddingX,
      contentFontSize: tokens.button.xlFontSize,
      controlHeightLG: tokens.button.xlHeight,
      paddingInlineLG: tokens.button.xlPaddingX,
      contentFontSizeLG: tokens.button.xlFontSize,
    },
    Input: {
      // Figma node 3019:7303
      borderRadius: tokens.input.radius,
      controlHeight: tokens.input.height, // 40px
      colorBorder: tokens.input.border,
      hoverBorderColor: tokens.input.border, // stays grey on hover (per design)
      activeBorderColor: tokens.input.borderActive,
      activeShadow: "0 1px 2px 0 rgba(16,24,40,0.05)",
      colorTextPlaceholder: tokens.input.placeholder,
      colorText: tokens.input.text,
      paddingInline: tokens.input.paddingX,
    },
    Select: {
      // Figma node 3019:7261 — mirrors the Input field; focus ring in globals.css
      borderRadius: tokens.input.radius,
      controlHeight: tokens.input.height,
      colorBorder: tokens.input.border,
      hoverBorderColor: tokens.input.border, // stays grey on hover (per design)
      activeBorderColor: tokens.input.borderActive,
      colorTextPlaceholder: tokens.select.placeholder,
      colorText: tokens.input.text,
    },
    Form: {
      itemMarginBottom: tokens.space.formItem,
    },
    Tabs: {
      inkBarColor: tokens.brand.primary,
      itemActiveColor: tokens.brand.primary,
      itemColor: tokens.text.muted,
      itemHoverColor: tokens.text.muted,
      itemSelectedColor: tokens.brand.primary,
      titleFontSize: 16,
      titleFontSizeLG: 20,
      titleFontSizeSM: 16,
    },
    Table: {
      // Figma nodes 3217:34504 (header) / 3217:34521 (cell).
      // Header/body font sizes + row heights diverge → set in globals.css.
      headerBg: tokens.table.headerBg,
      headerColor: tokens.table.headerColor,
      // Keep the whole header one flat grey — no highlight on the sorted column
      headerSortActiveBg: tokens.table.headerBg,
      headerSortHoverBg: tokens.table.headerBg,
      // Body stays white — no tint on the sorted column
      bodySortBg: tokens.neutral.white,
      headerSplitColor: "transparent",
      borderColor: tokens.table.border,
      rowHoverBg: tokens.table.hoverBg,
      colorText: tokens.table.bodyColor,
      cellPaddingInline: tokens.table.cellInline,
      cellFontSize: 14,
    },
    Descriptions: {
      labelBg: tokens.surface.labelBg,
      titleColor: tokens.text.heading,
    },
  },
};

export default antTheme;
