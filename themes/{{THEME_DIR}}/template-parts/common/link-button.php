<?php
/**
 * リンクボタンコンポーネント
 *
 * 使用方法:
 * <?php get_template_part('template-parts/common/link-button', null, [
 *   'tag' => 'a',              // a または button
 *   'ja_text' => '詳しく見る',
 *   'en_text' => 'View More',
 *   'href' => '/about/',       // tag="a" の場合
 *   'external' => false,       // 外部リンクか（デフォルト: false）
 *   'type' => 'button',        // tag="button" の場合: button|submit|reset
 *   'variant' => 'blue',       // blue または white
 *   'class_name' => ''         // 追加CSSクラス
 * ]); ?>
 *
 * @package {{PACKAGE_NAME}}
 */

// 引数バリデーション（開発環境のみ）
if ( ! validate_template_args($args, [ 'ja_text', 'en_text' ], 'link-button') ) {
    return;
}

// 引数を取得（デフォルト値つき）
$args = merge_template_defaults($args, [
    'tag' => 'button',
    'ja_text' => '',
    'en_text' => '',
    'href' => '',
    'external' => false,
    'type' => 'button',
    'variant' => 'blue',
    'class_name' => '',
]);

$tag        = $args['tag'];
$ja_text    = $args['ja_text'];
$en_text    = $args['en_text'];
$href       = $args['href'];
$external   = $args['external'];
$type       = $args['type'];
$variant    = $args['variant'];
$class_name = $args['class_name'];

$classes = [ 'c-link-button', "c-link-button--{$variant}" ];
if ( $class_name ) {
  $classes[] = $class_name;
}
$class_attr = implode(' ', $classes);

$arrow_icon = '<svg width="9" height="9" viewBox="0 0 9 9" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M0.157227 8.5918V0.591797L8.74902 4.5918L0.157227 8.5918Z" fill="currentColor"/>
</svg>';
?>

<?php if ( $tag === 'button' ) : ?>
<button class="<?php echo esc_attr($class_attr); ?>" type="<?php echo esc_attr($type); ?>">
  <span class="c-link-button__text">
    <span class="c-link-button__text-ja"><?php echo esc_html($ja_text); ?></span>
    <span class="c-link-button__text-en"><?php echo esc_html($en_text); ?></span>
  </span>
  <span class="c-link-button__icon">
    <span class="c-link-button__icon-wrapper">
      <span class="c-link-button__icon-arrow">
        <?php echo wp_kses_post( $arrow_icon ); ?>
      </span>
    </span>
  </span>
</button>
<?php elseif ( $tag === 'a' ) : ?>
<a class="<?php echo esc_attr($class_attr); ?>" href="<?php echo esc_url($href); ?>" 
  <?php
  if ( $external ) :
    ?>
  target="_blank" rel="noopener noreferrer"<?php endif; ?>>
  <span class="c-link-button__text">
    <span class="c-link-button__text-ja"><?php echo esc_html($ja_text); ?></span>
    <span class="c-link-button__text-en"><?php echo esc_html($en_text); ?></span>
  </span>
  <span class="c-link-button__icon">
    <span class="c-link-button__icon-wrapper">
      <span class="c-link-button__icon-arrow">
        <?php echo wp_kses_post( $arrow_icon ); ?>
      </span>
    </span>
  </span>
</a>
<?php endif; ?>
