# Astro Page Generation Templates

## Page File Template

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

import pageData from '../data/pages/{slug}.json';
---

<BaseLayout title="{ページ名} | サイト名" bodyClass="p-{slug}">
  <link rel="stylesheet" href="/assets/css/pages/{slug}/style.css" slot="addCSS" />
  <main>
    <Hero {...pageData.hero} />
    <!-- 他セクション -->
  </main>
</BaseLayout>
```

## Section Component Template

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

## Data JSON Template

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

## Naming Rules

| Target | Convention | Example |
|--------|-----------|---------|
| Astro file | PascalCase | `Hero.astro` |
| PHP target | kebab-case | `hero.php` |
| BEM block | `p-{slug}-{section}` | `p-about-hero` |
| Props | camelCase | `enHeading` |
| PHP args | snake_case | `en_heading` |
| Data key | camelCase | `hero.mainImage` |

## Example: Creating an About Page

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
