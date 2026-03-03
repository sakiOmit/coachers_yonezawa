# WordPress Page Template Patterns

## Section Naming Convention

**Independent Block naming required:** `p-{page}-{section}`

```php
// ✅ Correct
<section class="p-about-hero">
<section class="p-about-mission">

// ❌ Forbidden
<section class="p-about__hero">
<section class="p-about__mission">
```

## Page Template Structure

```php
<?php
/**
 * Template Name: Page Name
 *
 * @package Theme
 */

get_header();
?>

<main class="l-main">
  <section class="p-{slug}-hero">
    <div class="p-{slug}-hero__container">
      <!-- Content -->
    </div>
  </section>
</main>

<?php get_footer(); ?>
```

## SCSS File Structure

```
src/scss/object/projects/{slug}/
├── _p-{slug}.scss           # Import only (@use)
├── _p-{slug}-hero.scss      # hero section
├── _p-{slug}-about.scss     # about section
└── _p-{slug}-contact.scss   # contact section
```

## Entry File

```scss
// src/css/pages/{slug}/style.scss
@use "../../../scss/object/projects/{slug}/p-{slug}";
```

## Split Rule

200行以上のテンプレートは template-parts に分割:

| 推定行数 | 方式 | 出力 |
|---------|------|------|
| < 200行 | 単一ファイル | `pages/page-{slug}.php` のみ |
| >= 200行 | template-parts 分割 | `pages/page-{slug}.php` + `template-parts/{slug}/*.php` |

### Split Template (200+ lines)

**メインテンプレート:**
```php
<?php
/**
 * Template Name: Page Name
 *
 * @package Theme
 */

get_header();
?>

<main class="l-main">
  <?php get_template_part('template-parts/{slug}/hero'); ?>
  <?php get_template_part('template-parts/{slug}/message'); ?>
  <?php get_template_part('template-parts/{slug}/positions'); ?>
</main>

<?php get_footer(); ?>
```

**セクションパーツ:**
```php
<?php
/**
 * {Section Name} section for {Page Name}
 */
?>

<section class="p-{slug}-{section}">
  <div class="p-{slug}-{section}__container">
    <?php if ($title = get_field('{section}_title')): ?>
      <h2 class="p-{slug}-{section}__title">
        <?php echo esc_html($title); ?>
      </h2>
    <?php endif; ?>
  </div>
</section>
```

## Example: Creating a Recruit Page

**Step 1: Start skill**
```
/wordpress-page-generator
```

**Step 2: Interactive input**
```
Agent: Enter page name (Japanese):
User: 採用情報

Agent: Enter page slug (kebab-case):
User: recruit

Agent: Enter sections (comma-separated):
User: hero, message, positions, benefits, faq, entry

Agent: Estimated line count?
User: 300
```

**Step 3: Confirmation**
```
Agent: Will generate with template-parts split:

📁 themes/{{THEME_NAME}}/pages/page-recruit.php
📁 themes/{{THEME_NAME}}/template-parts/recruit/
   ├── hero.php
   ├── message.php
   ├── positions.php
   ├── benefits.php
   ├── faq.php
   └── entry.php
📁 src/scss/object/projects/recruit/ (7 files)
📁 src/css/pages/recruit/style.scss

Continue? (yes/no)
```

**Step 4: Generation complete**
```
✅ WordPress page template created!

Next steps:
1. Run npm run dev to verify build
2. Create fixed page in WordPress, select template
3. Implement each section PHP/SCSS
4. Use /acf-field-generator for ACF fields if needed
```
