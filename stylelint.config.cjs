module.exports = {
  extends: [
    "stylelint-config-standard-scss",
    "stylelint-config-recess-order",
    "stylelint-prettier/recommended"
  ],
  plugins: ["stylelint-scss"],
  rules: {
    // FLOCSS命名規則（ケバブケース対応）
    "selector-class-pattern": [
      "^(l-|c-|p-|u-|is-|has-|js-)[a-z][a-z0-9-]*(__[a-z][a-z0-9-]*)?(--[a-z][a-z0-9-]*)?$|^[a-z][a-z0-9-]*$",
      {
        message: "Expected class selector to follow FLOCSS + BEM pattern (l-, c-, p-, u-, is-, has-, js-)"
      }
    ],
    // ネスト深度制限
    "max-nesting-depth": [
      3,
      {
        ignore: ["pseudo-classes", "blockless-at-rules"],
        ignoreAtRules: ["include", "media", "supports"]
      }
    ],
    // &- ネスト禁止（BEM命名規則違反防止）
    // 例: &-element は禁止、&__element や &--modifier は許可
    "selector-nested-pattern": [
      "^(?!&-(?!-)).+$",
      {
        message: "&- nesting is not allowed. Use &__ for elements or &-- for modifiers (e.g., .p-block { &__element { } &--modifier { } })"
      }
    ],
    // SCSS固有ルール
    "scss/at-rule-no-unknown": true,
    "scss/dollar-variable-pattern": null, // 変数名は自由（ハイフン区切り許容）
    "scss/percent-placeholder-pattern": "^[a-z][a-zA-Z0-9]*$",
    // 無効化するルール
    "no-descending-specificity": null,
    "selector-pseudo-class-no-unknown": [
      true,
      {
        ignorePseudoClasses: ["global", "local"]
      }
    ]
  },
  ignoreFiles: [
    "node_modules/**/*",
    "themes/*/assets/**/*",
    "**/*.min.css"
  ]
};
