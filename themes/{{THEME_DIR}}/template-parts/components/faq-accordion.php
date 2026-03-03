<?php

/**
 * Component: FAQ Accordion
 *
 * Reusable FAQ accordion component.
 *
 * @package {{PACKAGE_NAME}}
 *
 * @param array $args {
 *     Optional. FAQ accordion arguments.
 *
 *     @type array $items         FAQ items array. Each item should have 'question' and 'answer' keys.
 *     @type int   $start_index   Starting number for Q/A labels. Default 1.
 * }
 */

// Parse arguments with defaults
$args = wp_parse_args(
  $args ?? [],
  [
    'items'       => [],
    'start_index' => 1,
  ]
);

$items       = $args['items'];
$start_index = absint( $args['start_index'] );

// Exit if no items
if ( empty( $items ) ) {
  return;
}
?>

<ul class="c-faq-accordion">
  <?php foreach ( $items as $index => $item ) : ?>
    <li class="c-faq-accordion__item js-faq-item">
      <button type="button" class="c-faq-accordion__question js-faq-trigger">
        <span class="c-faq-accordion__question-label">Q<?php echo $start_index + $index; ?></span>
        <span class="c-faq-accordion__question-text"><?php echo esc_html( $item['question'] ); ?></span>
        <span class="c-faq-accordion__question-icon">
          <span class="c-faq-accordion__question-icon-line"></span>
          <span class="c-faq-accordion__question-icon-line c-faq-accordion__question-icon-line--vertical"></span>
        </span>
      </button>
      <div class="c-faq-accordion__answer js-faq-answer">
        <div class="c-faq-accordion__answer-inner">
          <div class="c-faq-accordion__answer-content">
            <span class="c-faq-accordion__answer-label">A<?php echo $start_index + $index; ?></span>
            <p class="c-faq-accordion__answer-text"><?php echo esc_html( $item['answer'] ); ?></p>
          </div>
        </div>
      </div>
    </li>
  <?php endforeach; ?>
</ul>
