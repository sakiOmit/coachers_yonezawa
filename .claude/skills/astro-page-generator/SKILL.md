---
name: astro-page-generator
description: "Generate Astro page with section components, mock data, and SCSS wiring interactively"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - mcp__serena__read_memory
  - mcp__serena__search_for_pattern
  - mcp__serena__find_symbol
context: fork
agent: general-purpose
---

# Astro Page Generator

## Overview

Astro静的コーディング環境で新規ページを対話的に生成する。
ページ名、セクション構成、データ構造を収集し、Astroページ・セクションコンポーネント・モックデータJSON・SCSS接続を一括生成する。

## Usage

```
/astro-page-generator
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| (interactive) | Yes | ページ名（日本語） |
| (interactive) | Yes | ページスラッグ（kebab-case） |
| (interactive) | Yes | セクション一覧（カンマ区切り） |
| (interactive) | No | 既存WordPress PHPテンプレートパス（あれば参照） |

## Output

### Generated Files

**Astroページ:**
- `astro/src/pages/{slug}.astro`

**セクションコンポーネント:**
- `astro/src/components/sections/{slug}/{Section}.astro` (各セクション)

**モックデータ:**
- `astro/src/data/pages/{slug}.json`

**SCSS（既存なければ）:**
- `src/scss/object/projects/{slug}/` ディレクトリ
- `_p-{slug}.scss` + 各セクションファイル
- `src/css/pages/{slug}/style.scss` エントリーポイント

### Updated Files

- `vite.config.js` — エントリー追加（SCSSが新規の場合のみ）

## Processing Flow

```
1. 情報収集（対話）
   ├─ ページ名（日本語）
   ├─ ページスラッグ（kebab-case）
   ├─ セクション一覧
   └─ 既存PHPテンプレートの有無

2. 既存パターン確認
   ├─ 同名SCSSファイルの存在チェック
   ├─ 同名PHPテンプレートの参照（あれば構造を踏襲）
   └─ 既存共通コンポーネントの確認

3. ファイル生成
   ├─ モックデータJSON（ACF構造を模倣）
   ├─ セクションコンポーネント（Props interface付き）
   ├─ ページファイル（BaseLayout + import + sections）
   └─ SCSS構造（既存なければ新規作成）

4. ビルド設定更新
   └─ vite.config.js エントリー追加（SCSSが新規の場合）

5. 検証
   ├─ npm run astro:build
   └─ 生成ファイル一覧と変換先の対応表出力
```

## Generation Rules (Mandatory)

### Page File Template

```astro
---
/**
 * {ページ名}
 * WordPress pages/page-{slug}.php に相当
 *
 * 変換先: pages/page-{slug}.php
 * Template Name: {ページ名}
 */
import BaseLayout from '../layouts/BaseLayout.astro';
import Hero from '../components/sections/{slug}/Hero.astro';
// ... 他セクション

import '@root-src/css/pages/{slug}/style.scss';
import pageData from '../data/pages/{slug}.json';
---

<BaseLayout title="{ページ名} | サイト名">
  <main class="p-{slug}">
    <Hero {...pageData.hero} />
    <!-- 他セクション -->
  </main>
</BaseLayout>
```

### Section Component Template

```astro
---
/**
 * {SectionName}
 * WordPress template-parts/{slug}/{section}.php に相当
 *
 * 変換先: get_template_part('template-parts/{slug}/{section}')
 */
interface Props {
  // ACFフィールドに対応するprops
}

const { ... } = Astro.props;
---

<section class="p-{slug}-{section}">
  <div class="p-{slug}-{section}__container">
    <!-- Content -->
  </div>
</section>
```

### Data JSON Template

```json
{
  "hero": {
    "title": "...",
    "description": "...",
    "image": "/assets/images/{slug}/hero.png"
  },
  "sectionName": {
    "items": []
  }
}
```

### Naming Rules

| Target | Convention | Example |
|--------|-----------|---------|
| Astro file | PascalCase | `Hero.astro` |
| PHP target | kebab-case | `hero.php` |
| BEM block | `p-{slug}-{section}` | `p-about-hero` |
| Props | camelCase | `enHeading` |
| PHP args | snake_case | `en_heading` |
| Data key | camelCase | `hero.mainImage` |

## Error Handling

| Error | Response |
|-------|----------|
| Slug duplicate (Astro page exists) | 確認してから上書きまたは別名提案 |
| SCSS already exists | 既存SCSSを再利用、エントリーポイントのみ接続 |
| Build failure | エラー内容を表示し修正提案 |
| Invalid kebab-case | バリデーションして修正提案 |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/astro.md` | Astroワークフロー規約 |
| `.claude/rules/scss.md` | SCSS/BEM命名規約 |
| `astro/src/layouts/BaseLayout.astro` | 共通レイアウト |
| `astro/src/lib/data-helpers.ts` | データヘルパー |
| `astro/src/components/common/` | 共通コンポーネント |

## Examples

### Example: Creating an About Page

**Step 1: Start skill**
```
/astro-page-generator
```

**Step 2: Interactive input**
```
Agent: ページ名（日本語）:
User: 会社概要

Agent: ページスラッグ（kebab-case）:
User: about

Agent: セクション一覧（カンマ区切り）:
User: hero, mission, history, team, access

Agent: 既存のWordPress PHPテンプレートはありますか？:
User: themes/test-theme/pages/page-about.php
```

**Step 3: Confirmation**
```
Agent: 以下のファイルを生成します:

📄 astro/src/pages/about.astro
📁 astro/src/components/sections/about/
   ├── Hero.astro
   ├── Mission.astro
   ├── History.astro
   ├── Team.astro
   └── Access.astro
📄 astro/src/data/pages/about.json

SCSS（既存チェック）:
  → src/scss/object/projects/about/ が存在しない場合は新規作成
  → 存在する場合は既存を利用

Continue? (yes/no)
```

**Step 4: Generation complete**
```
✅ Astro page generated!

| Astro File | WordPress Target |
|-----------|-----------------|
| pages/about.astro | pages/page-about.php |
| sections/about/Hero.astro | template-parts/about/hero.php |
| sections/about/Mission.astro | template-parts/about/mission.php |
| data/pages/about.json | ACF fields |

Next steps:
1. npm run astro:dev で確認
2. モックデータを実際のコンテンツに更新
3. デザイン承認後、WordPress PHPに変換（/astro-to-wordpress）
```

## Related Skills

| Skill | Purpose |
|-------|---------|
| `wordpress-page-generator` | WordPress PHP版ページ生成 |
| `astro-to-wordpress` | Astro→WordPress変換 |
| `scss-component-generator` | SCSSコンポーネント追加 |

---

**Version**: 1.0.0
**Created**: 2026-02-18
