---
name: scss-component-generator
description: "Generate FLOCSS+BEM compliant SCSS components (component/project/layout) interactively."
argument-hint: "[component|project|layout] [name]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
  - mcp__serena__read_memory
  - mcp__serena__search_for_pattern
  - mcp__serena__find_symbol
model: opus
context: fork
agent: general-purpose
---

# SCSS Component Generator

## Dynamic Context

```
Existing SCSS components:
!`ls src/scss/object/component/ src/scss/object/project/ 2>/dev/null || echo "(empty)"`
```

## Overview

Generate FLOCSS + BEM compliant SCSS components interactively. This skill collects component information through dialogue and automatically generates SCSS files following project conventions.

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/figma-implement` Step 6（任意） |
| **後工程** | `/review scss`, `/qa` |
| **呼び出し元** | ユーザー直接, `/figma-implement` |
| **呼び出し先** | なし |

## Usage

```
/scss-component-generator
```

The skill will guide you through an interactive process to collect necessary information.

## Input Parameters

Collected interactively:

| Parameter | Required | Description |
|-----------|----------|-------------|
| Component Type | Yes | `component` (c-), `project` (p-), or `layout` (l-) |
| Component Name | Yes | kebab-case name |
| Page Name | Yes* | Page name for project components |
| Elements | Yes | BEM elements (comma-separated, kebab-case) |
| Modifiers | No | BEM modifiers (optional) |
| Responsive | Yes | Whether responsive styles are needed (yes/no) |

*Required only for `project` type

## Output

### File Locations

| Type | Output Path |
|------|-------------|
| Component | `src/scss/object/components/_c-{name}.scss` |
| Project | `src/scss/object/projects/{page}/_p-{page}-{name}.scss` |
| Layout | `src/scss/layout/_l-{name}.scss` |

### Entry File Update

Automatically adds `@use` to:
- `src/css/pages/{page}/style.scss`

## Processing Flow

```
1. Information Collection
   ├─ Component type (component / project / layout)
   ├─ Component name (kebab-case)
   ├─ Page name (for project type)
   ├─ Elements list (BEM Elements)
   ├─ Modifiers (optional)
   └─ Responsive requirement

2. Base Style Check
   └─ Use Serena MCP read_memory("base-styles-reference.md")
      to check for styles to avoid duplicating

3. Template-Based Code Generation
   └─ Use templates/ for SCSS code generation

4. File Output
   └─ Save to appropriate directory

5. Entry File Update
   └─ Add @use to style.scss if needed

6. Verification
   ├─ Run Stylelint check (npm run lint:css)
   └─ Guide user to next steps
```

## Component Types & Generation Rules

3種類のコンポーネント（c-/p-/l-）のテンプレートと BEM/Responsive/Container ルールは references に定義。

**詳細**: → [references/scss-generation-rules.md](references/scss-generation-rules.md)（テンプレート + ルール + 対話例）

## Error Handling

| Error | Response |
|-------|----------|
| Filename conflict | Check existing files before creation |
| Invalid kebab-case | Validate input format |
| Stylelint error | Run check and report issues |
| Base style duplication | Warn user about redundant styles |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. **引数あり** (`[component|project|layout] [name]`): 非対話モードで直接生成
   - `--elements e1,e2,e3` オプション: BEM Elements をカンマ区切りで指定
   - `--modifiers m1,m2` オプション: BEM Modifiers をカンマ区切りで指定
   - 例: `/scss-component-generator project top-hero --elements title,description,image --modifiers large`
2. **引数なし**: 対話モード（従来通りユーザーに質問）

## 実行手順

1. **型判定**
   - 第1引数が `component`/`project`/`layout` のいずれかを確認
   - 不正な場合: 正しい型を提示して選択を促す

2. **名前検証**
   - 第2引数が kebab-case であることをバリデーション
   - `project` 型の場合: `{page}-{section}` 形式であることを確認（例: `top-hero`）
   - 既存ファイルとの重複チェック

3. **テンプレート適用**
   - `scripts/generate-scss.sh` が利用可能であれば先行実行
   - スクリプトが利用できない場合は直接 Write で生成
   - Generation Rules (Mandatory) セクションのテンプレートに従う

4. **BEM/FLOCSS 検証**
   - `scripts/validate-scss-component.sh` を生成ファイルに対して実行:
     ```bash
     bash .claude/skills/scss-component-generator/scripts/validate-scss-component.sh {生成ファイル}
     ```
   - FAIL の場合: 指摘箇所を修正して再検証
   - PASS の場合: Stylelint へ進む

5. **Stylelint 検証**
   - `npm run lint:css` を実行して追加の準拠チェック
   - エラーがあれば自動修正を試行

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/generate-scss.sh` | テンプレートからの SCSS 自動生成 | type, name, page, elements, modifiers | SCSS file |
| `scripts/validate-scss-component.sh` | BEM/FLOCSS 品質自動検証 | SCSS file path | Validation results (text) |

### generate-scss.sh

```bash
bash .claude/skills/scss-component-generator/scripts/generate-scss.sh <type> <name> [page] [elements] [modifiers]
# Examples:
bash .claude/skills/scss-component-generator/scripts/generate-scss.sh component button '' icon,text primary,secondary
bash .claude/skills/scss-component-generator/scripts/generate-scss.sh project hero top title,description,image large
bash .claude/skills/scss-component-generator/scripts/generate-scss.sh layout sidebar
```

- **入力**: type (component|project|layout), name (kebab-case), page (project時必須), elements (カンマ区切り), modifiers (カンマ区切り)
- **出力**: FLOCSS 準拠の SCSS ファイル
- **生成先**:
  - component → `src/scss/object/component/_c-{name}.scss`
  - project → `src/scss/object/project/{page}/_p-{page}-{name}.scss`
  - layout → `src/scss/layout/_l-{name}.scss`
- **container 要素**: `@include container()` が自動挿入される
- **終了コード**: 0=成功, 1=バリデーションエラー

### validate-scss-component.sh

```bash
bash .claude/skills/scss-component-generator/scripts/validate-scss-component.sh <scss-file>
# Example:
bash .claude/skills/scss-component-generator/scripts/validate-scss-component.sh src/scss/object/component/_c-button.scss
```

- **入力**: SCSS ファイルパス
- **検証項目** (6チェック):
  1. FLOCSS プレフィックス (c-/p-/l-/u-)
  2. kebab-case 命名 (camelCase 検出)
  3. BEM ネスト (&__ 使用、&- 禁止)
  4. container ルール (@include container() のみ)
  5. hover ルール (&:hover 直接使用禁止)
  6. ネスト深度 (最大4階層)
- **終了コード**: 0=PASS, 1=FAIL (issue count 付き)

## Agent Integration

Step 2（Base Style Check）で flocss-base-specialist エージェントに相談可能:

```
Task tool:
  subagent_type: flocss-base-specialist
  prompt: |
    以下の SCSS コンポーネントについて Base Style との重複チェックを実行してください:
    - type: {type} (component/project/layout)
    - name: {name}
    - elements: {elements}

    確認観点:
    - foundation/ で定義済みのスタイルとの重複
    - 変数・mixin の適切な使用
    - FLOCSS レイヤー配置の妥当性
```

**委譲条件**: 新規 component (c-) 作成時、または base style 重複が懸念される場合
**Fallback**: エージェント不在時は `.claude/rules/scss.md` を Read して直接チェック

## Related Files

| File | Purpose |
|------|---------|
| `templates/` | SCSS templates for code generation |
| `docs/coding-guidelines/02-scss-design.md` | SCSS design guidelines |
| `.claude/rules/scss.md` | SCSS rules |
| `.claude/skills/scripts-standard.md` | スクリプト標準規約 |

---

**Version**: 1.0.0
**Created**: 2026-01-30
**Original Author**: Team
**Migrated by**: Auto-generated
