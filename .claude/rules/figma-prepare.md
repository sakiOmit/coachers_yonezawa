# Figma Prepare Rules

## Overview

Figmaデザインの構造整理（リネーム・グループ化・Auto Layout）に関する命名規約・閾値・品質スコア計算式を定義する。
`/figma-prepare` スキルの判定基準として使用。

## レイヤー命名規約

### セマンティックプレフィックス

| 用途 | プレフィックス | 例 |
|------|--------------|-----|
| セクション | section- | section-hero, section-about |
| カード | card- | card-feature, card-testimonial |
| ボタン | btn- | btn-primary, btn-cta |
| 画像 | img- | img-hero, img-avatar |
| 見出し | heading- | heading-main, heading-sub |
| 本文 | body- | body-intro, body-description |
| 背景 | bg- | bg-hero, bg-overlay |
| 区切り線 | divider | divider |
| コンテナ | container- | container-main, container-narrow |
| アイコン | icon- | icon-arrow, icon-check |
| ラベル | label- | label-category, label-tag |
| ナビゲーション | nav- | nav-main, nav-footer |
| フォーム | form- | form-contact, form-search |
| リスト | list- | list-features, list-members |
| リストアイテム | list-item- | list-item-feature |
| 装飾パターン | decoration-dots-, decoration-pattern- | decoration-dots-0, decoration-pattern-1（Issue 189） |
| ハイライト | highlight- | highlight-key-text（Issue 190） |

### 未命名レイヤーパターン（検出対象）

以下の正規表現にマッチするレイヤーを「未命名」として検出:

```
^(Rectangle|Ellipse|Line|Vector|Frame|Group|Component|Instance|Text|Polygon|Star|Image)\s*\d*$
```

※ マッチングはケースインセンシティブ（大文字小文字を区別しない）。例: "rectangle 1", "FRAME 2" もマッチする。

## 品質スコア計算

### 計算式（100点満点）

```
score = 100
score -= min(30, unnamed_rate * 0.5)         # 未命名率（%）× 0.5、上限-30
score -= min(40, flat_sections * 5 + flat_excess * 0.5)  # フラットセクション数 × 5 + 超過子要素数 × 0.5、上限-40（Issue 188: 30→40）
score -= min(10, ungrouped_candidates * 1)    # 未グループ候補数 × 1、上限-10（最も不安定な指標のため抑制）
score -= min(15, deep_nesting_count * 3)      # 深すぎるネスト数 × 3、上限-15
# autolayout_penalty は除外（get_metadataにlayoutMode情報なし、計測不能）
score = max(0, score)
```

**注意**:
- `deep_nesting_count` はセクションルート（width≈1440のフレーム）からの相対深度（`section_depth`）で計算。
- `max_depth` は絶対深度（ルートからの距離）。`max_section_depth` は最大相対深度（セクションルートからの距離）。スコア計算には `section_depth` を使用する。

### グレード判定

| グレード | スコア | 推奨アクション |
|---------|-------|---------------|
| A | 80-100 | そのまま `/figma-analyze` へ進行 |
| B | 60-79 | Phase 2（グループ化）推奨 |
| C | 40-59 | Phase 2 + 3（グループ化 + リネーム）推奨 |
| D | 20-39 | 全フェーズ推奨 |
| F | 0-19 | 全フェーズ推奨（手動確認も検討） |

## 閾値パラメータ

| パラメータ | 値 | 用途 |
|-----------|-----|------|
| proximity_gap | 24px | 近接要素のグルーピング判定距離 |
| section_root_width | 1440px | Figmaページレベルフレーム幅（セクションルート検出の基準値） |
| flat_threshold | 15 children | フラット構造の検出閾値 |
| repeated_pattern_min | 3 occurrences | リピートパターンの最小検出回数 |
| grid_snap | 4px | Gap/Paddingのスナップ単位 |
| deep_nesting_threshold | 6 levels | 深すぎるネストの閾値 |
| batch_size | 50 nodes | Chrome DevTools実行時のバッチサイズ |
| variance_ratio | 1.5 | Auto Layout方向判定（X分散 > Y分散 × ratio → HORIZONTAL） |
| cv_threshold | 0.25 | 等間隔スペーシング検出の変動係数閾値（Issue 138） |
| spatial_gap_threshold | 100px | サブグループ分割の最小ギャップ |
| header_zone_height | 120px | ヘッダー検出ゾーン（ページ上端からの距離） |
| footer_zone_height | 300px | フッター検出ゾーン（ページ下端からの距離） |
| zone_overlap_item | 0.5 (50%) | 垂直ゾーンマージ：アイテム側の最小重なり率 |
| zone_overlap_zone | 0.3 (30%) | 垂直ゾーンマージ：ゾーン側の最小重なり率 |
| zone_min_members | 3 | 垂直ゾーングループの最小ノード数（ベンチマーク改善：1-2ノードゾーンの過剰検出防止） |
| jaccard_threshold | 0.7 | パターン検出のファジーマッチ閾値 |
| header_max_element_height | 200px | ヘッダーグループ内要素の最大高さ（Issue 125） |
| footer_zone_margin | 50px | フッターゾーン下方マージン（ページ外要素包含用、Issue 129） |
| header_zone_margin | 50px | ヘッダーゾーン下方マージン（Issue 266） |
| divider_max_height | 5px | 水平区切り線の最大高さ（Phase 3 リネーム、Issue 124） |
| header_y_threshold | 100px | ヘッダー検出Y位置閾値（Phase 3 リネーム、Issue 124） |
| footer_proximity | 100px | フッター検出の親下端からの距離（Phase 3 リネーム、Issue 124） |
| footer_max_height | 200px | フッター検出の最大高さ（Phase 3 リネーム、Issue 124） |
| wide_element_ratio | 0.7 | 「幅広」判定の親幅比率（Phase 3 リネーム、Issue 124） |
| wide_element_min_width | 500px | 「幅広」判定の最小絶対幅（Phase 3 リネーム、Issue 124） |
| icon_max_size | 48px | アイコン検出の最大幅/高さ（Phase 3 リネーム、Issue 124） |
| bullet_max_size | 12px | 弾丸ポイントELLIPSE検出の最大幅/高さ（ベンチマーク改善2） |
| section_bg_width_ratio | 0.9 (90%) | セクション背景RECTANGLE検出の幅比率（>= 1296px、ベンチマーク改善3） |
| button_max_height | 70px | ボタン検出の最大高さ（Phase 3 リネーム、Issue 124） |
| button_max_width | 300px | ボタン検出の最大幅（Phase 3 リネーム、Issue 124） |
| button_text_max_len | 15 chars | ボタンテキストの最大文字数（Phase 3 リネーム、Issue 124） |
| label_max_len | 20 chars | ラベルテキストの最大文字数（Phase 3 リネーム、Issue 124） |
| nav_min_text_count | 4 items | ナビゲーション検出の最小TEXT子要素数（Phase 3 リネーム、Issue 124） |
| nav_max_text_len | 20 chars | ナビゲーション項目の最大文字数（Phase 3 リネーム、Issue 124） |
| nav_grandchild_min | 4 items | ヘッダーナビ検出の最小TEXTグランドチャイルド数（Phase 3 リネーム、Issue 124） |
| row_tolerance | 20px | WRAP/グリッド行検出のY座標グルーピング許容差（Issue 131） |
| header_text_max_width | 200px | ヘッダーナビテキスト要素の最大幅（Phase 2 検出、Issue 134） |
| header_logo_max_width | 300px | ヘッダーロゴ要素の最大幅（Phase 2 検出、Issue 134） |
| header_logo_max_height | 100px | ヘッダーロゴ要素の最大高さ（Phase 2 検出、Issue 134） |
| header_nav_min_texts | 3 items | ヘッダーナビ検出の最小TEXT数（Phase 2 検出、Issue 134） |
| hero_zone_distance | 200px | ヒーロー検出のページ上端からの最大距離（Phase 2 ゾーン命名、Issue 135） |
| large_bg_width_ratio | 0.6 | 大背景検出のページ幅比率（Phase 2 ゾーン命名、Issue 135） |
| consecutive_pattern_min | 3 occurrences | 連続パターンの最小検出回数 |
| heading_max_height_ratio | 0.4 (40%) | ヘッディング検出：コンテンツ高さ比の上限 |
| heading_max_children | 5 | ヘッディングフレームの最大子要素数 |
| heading_text_ratio | 0.5 (50%) | ヘッディング検出：TEXT/VECTOR葉ノード比率の下限 |
| loose_element_max_height | 20px | 遊離要素の最大高さ |
| loose_absorption_distance | 200px | 遊離要素吸収の最大距離 |
| bg_width_ratio | 0.8 | 背景RECTANGLE検出の親幅比率（Issue 180） |
| bg_min_height_ratio | 0.3 | 背景RECTANGLE検出の親高さ比率（Issue 180） |
| bg_decoration_max_area_ratio | 0.05 | 装飾要素の最大面積比率（Issue 180） |
| table_min_rows | 3 | テーブル検出の最小行数（Issue 181） |
| table_row_width_ratio | 0.9 | テーブル行背景の親幅比率（Issue 181） |
| table_divider_max_height | 2px | テーブル区切り線の最大高さ（Issue 181） |
| off_canvas_margin | 1.5 | Off-canvas判定の乗数（x > page_width × 1.5 でoff-canvas、Issue 182） |
| overflow_bg_min_width | 1400px | はみ出し背景候補の最小幅（Issue 183） |
| section_root_width_ratio | 0.9 (90%) | セクションルート検出の最小幅比率（width >= 1440 × 0.9 = 1296px、Issue 191） |
| tuple_pattern_min | 3 repetitions | タプルパターンの最小繰り返し回数（Issue 186） |
| tuple_max_size | 5 elements | タプル内の最大要素数（Issue 186） |
| decoration_max_size | 200px | 装飾パターンフレームの最大幅/高さ（Issue 189） |
| decoration_shape_ratio | 0.6 (60%) | 装飾パターン内のシェイプ葉ノード比率の下限（Issue 189） |
| decoration_min_shapes | 3 | 装飾パターンの最小シェイプ葉ノード数（Issue 189） |
| highlight_overlap_ratio | 0.8 (80%) | ハイライト検出のY重なり率下限（Issue 190） |
| highlight_x_overlap_ratio | 0.5 (50%) | ハイライト検出のX重なり率下限（Issue 196） |
| highlight_text_max_len | 30 chars | ハイライトテキストの最大文字数（Issue 190） |
| highlight_height_ratio_min | 0.5 | ハイライトRECT高さ/TEXT高さの下限比率（Issue 190） |
| highlight_height_ratio_max | 2.0 | ハイライトRECT高さ/TEXT高さの上限比率（Issue 190） |
| en_label_max_words | 3 words | EN+JPペア検出：英語ラベルの最大単語数（Issue 185） |
| en_jp_pair_max_distance | 200px | EN+JPペア検出：ペア間の最大距離（Issue 185） |
| cta_square_ratio_min | 0.8 | CTA検出：幅/高さ比の下限（Issue 193） |
| cta_square_ratio_max | 1.2 | CTA検出：幅/高さ比の上限（Issue 193） |
| cta_y_threshold | 100px | CTA検出：ページ上端からの最大Y位置（Issue 193） |
| side_panel_max_width | 80px | サイドパネル検出：最大幅（Issue 192） |
| side_panel_height_ratio | 3.0 | サイドパネル検出：高さ/幅の最小比率（Issue 192） |
| horizontal_bar_max_height | 100px | 水平バー検出：Y帯域の最大高さ（Issue 184） |
| horizontal_bar_min_elements | 4 | 水平バー検出：帯域内の最小要素数（Issue 184） |
| horizontal_bar_variance_ratio | 3 | 水平バー検出：X分散がY分散の何倍以上で水平判定（Issue 196） |
| heading_soft_height_ratio | 0.8 (80%) | ヘッディング検出：40-80%の中間ゾーンの上限比率（Issue 197） |
| center_align_variance | 4 | Auto Layout反軸アライメント：CENTER判定の分散閾値（Issue 202） |
| align_tolerance | 2px | Auto Layout反軸アライメント：MIN/MAX判定の位置許容差（Issue 202） |
| confidence_high_cov | 0.15 | Auto Layout Gap整合性：high confidence判定のCoV閾値（Issue 202） |
| confidence_medium_cov | 0.35 | Auto Layout Gap整合性：medium confidence判定のCoV閾値（Issue 202） |
| bg_left_overflow_width_ratio | 0.5 (50%) | 左はみ出し背景検出：親幅に対する最小幅比率（Issue 204） |
| hint_header_y_ratio | 0.05 (5%) | Stage Bヒント：ヘッダー判定Y位置比率（ページ高さの上位5%、Issue 201） |
| hint_footer_y_ratio | 0.9 (90%) | Stage Bヒント：フッター判定Y位置比率（y+h > page_h × 0.9、Issue 201） |
| hint_wide_element_ratio | 0.8 (80%) | Stage Bヒント：ヘッダー/フッター幅比率（ページ幅の80%超、Issue 201） |
| hint_bg_min_height | 100px | Stage Bヒント：背景候補RECTANGLEの最小高さ（Issue 201） |
| hint_heading_max_height | 200px | Stage Bヒント：ヘッディング候補の最大高さ（Issue 201） |
| flag_overflow_x_ratio | 1.05 | フラグ判定：overflow検出の右端許容比率（5%超過、Issue 203） |
| flag_overflow_y_ratio | 1.02 | フラグ判定：overflow-y検出の下端許容比率（2%超過、Issue 203） |
| flag_bg_full_width_ratio | 0.95 (95%) | フラグ判定：bg-fullの幅比率（ページ幅の95%以上、Issue 203） |
| flag_tiny_max_size | 50px | フラグ判定：tiny要素の最大幅/高さ（Issue 203） |
| spatial_split_min_non_leaf | 6 elements | 空間ギャップ分割：非リーフグループの最小要素数（Issue 206） |
| cta_x_position_ratio | 0.8 (80%) | CTA検出：X位置が親幅の80%以上で右上配置判定（Issue 215） |
| side_panel_right_x_ratio | 0.9 (90%) | サイドパネル検出：右端X位置比率（Issue 216） |
| side_panel_left_x_ratio | 0.1 (10%) | サイドパネル検出：左端X位置比率（Issue 216） |
| footer_text_ratio | 0.3 (30%) | フッター検出：TEXT子要素の最小比率（Issue 217） |
| image_wrapper_ratio | 0.5 (50%) | 画像ラッパー検出：IMAGE/RECTANGLE子要素の最小比率（Issue 218） |
| heading_body_text_threshold | 50 chars | ヘッディングvs本文判定：この文字数超 → body、以下 → heading（Issue 219） |
| grid_size_similarity | 0.20 (20%) | グリッド検出：幅/高さの最大変動率（Issue 220） |
| grandchild_threshold | 5 nodes | Stage C：グランドチャイルド展開の最大node_ids数（Issue 212） |
| max_stage_c_depth | 10 levels | Stage C 再帰安全上限（収束ベース、実際は3-4で終了。Issue 224, 257） |
| compare_match_threshold | 0.5 | Stage A/C グループマッチングのJaccard閾値（Issue 214） |
| stage_c_coverage_threshold | 0.8 (80%) | Stage C採用閾値（レガシー、段階統合に置換済み） |
| stage_merge_tier1 | 0.8 (80%) | 段階統合Tier 1：カバレッジ >= 80% → Stage C完全採用 |
| stage_merge_tier2 | 0.6 (60%) | 段階統合Tier 2：カバレッジ >= 60% → Stage C + 未マッチStage Aマージ |
| stage_merge_tier3 | 0.4 (40%) | 段階統合Tier 3：カバレッジ >= 40% → Stage A + 高信頼Stage Cマージ |
| base_viewport_width | 1440px | ビューポートスケーリング基準幅 |
| base_viewport_height | 8500px | ビューポートスケーリング基準高さ |
| llm_fallback_confidence_threshold | 50 | LLMフォールバック発動の信頼度閾値 |
| llm_confidence_high | 92 | LLM回答「高」の信頼度スコア |
| llm_confidence_medium | 78 | LLM回答「中」の信頼度スコア |
| llm_confidence_low | 62 | LLM回答「低」の信頼度スコア |

## リネームロジック（優先順）

| 優先度 | 手法 | 適用条件 | 例 |
|-------|------|---------|-----|
| 0 | EN+JPラベルペア検出 | 大文字ASCII TEXT + 日本語TEXT兄弟、200px以内 | COMPANY→en-label-company, 会社情報→heading-company-info（Issue 185） |
| 1 | テキスト内容ベース | TEXT ノードの内容から推論 | "お問い合わせ" → heading-contact |
| 2 | シェイプ分析 | RECTANGLE/ELLIPSE の用途推論 | 全幅薄型 → divider |
| 3 | ポジション分析 | ページ内の位置から推論 | 最上部 → header |
| 3.1 | ヘッダー/フッター検出 | 上端+幅広+ナビ子要素 / 下端+コンパクト+テキスト多 | header, footer |
| 3.15 | CTA正方形ボタン検出 | 略正方形(0.8-1.2比)+右上配置+CTAキーワード | cta-contact（Issue 193） |
| 3.16 | サイドパネル検出 | 幅80px以下+高さ/幅比3.0以上+ページ端配置 | side-panel-0（Issue 192） |
| 3.2 | 小アイコン検出 | 子なし、48x48以下 | icon-0 |
| 3.5 | ナビゲーション検出 | 4+短テキスト子要素、水平配置 | nav-0 |
| 4.0 | 装飾パターン検出 | FRAME/GROUP、200px以下、60%+シェイプ葉ノード、3+シェイプ | decoration-dots-0, decoration-pattern-0（Issue 189） |
| 4 | 子構造分析 | 子要素の構成から推論 | img+text+btn → card |
| 5 | フォールバック | 上記で判定不可 | {type}-{index} |

## グルーピング検出アルゴリズム

### 既存構造保護ルール（Issue #221）

デザイナーが意図的に作成した構造を分解しない。以下のノードの子要素にはグルーピング検出を適用しない:

| ノードタイプ | 条件 | 理由 |
|-------------|------|------|
| GROUP | 意味のある名前（UNNAMED_RE非マッチ） | デザイナーが意図的にグループ化した構造 |
| COMPONENT | 常に保護 | 再利用コンポーネント構造の維持 |
| INSTANCE | 常に保護 | コンポーネントインスタンスの構造維持 |

**例外**: ルートレベル（アートボード直下）は常に処理対象。保護はルート以外のレベルに適用。

**自動名のGROUP**（`Group 1`, `Group 23` 等）は保護対象外。UNNAMED_REにマッチするため処理される。

### 過剰グルーピング抑制（Issue #222）

非ルートレベルで子要素数が `flat_threshold` (15) 未満のノードには、`proximity` / `pattern` / `spacing` 検出を適用しない。`semantic` 検出（cards, nav, grid）は子要素数に関わらず実行する。

| レベル | 子要素数 | 適用手法 |
|-------|---------|---------|
| ルート | 任意 | 全手法（semantic + pattern + spacing + proximity + zone + ...） |
| 非ルート | >= 15 | 全手法 |
| 非ルート | < 15 | semantic のみ（cards, nav, grid の構造検出） |

**理由**: 少数の子要素を持つ整理されたノードに proximity/pattern を適用すると、不要なサブグループが大量生成される。semantic 検出のみ残すことで、genuineなカード/ナビ/グリッドパターンは検出しつつ過剰グルーピングを防止。

**注意**: 名前付きFRAMEでも semantic 検出は実行する。名前があっても内部にカード3枚があればcard-listとして検出するのは有用。

### 近接性ベース（スコアリング）

1. 兄弟要素の全ペアの距離を計算
2. スコアリング: `effective_distance = raw_distance × alignment_bonus × size_similarity_bonus`
   - alignment_bonus: 左端/右端/中心X/上端/下端/中心Y が 2px 以内 → 0.5（距離半減）
   - size_similarity_bonus: 幅・高さとも 20% 以内 → 0.7（距離 30% 減）
3. `score = max(0, 1 - effective_distance / (gap × 2))` → score > 0.5 でグループ化

### パターン検出（ファジーマッチング）

1. 各要素の「構造ハッシュ」を計算（子要素タイプ + 数の組み合わせ）
2. Jaccard 類似度 >= 0.7 でファジーマッチング（完全一致不要）
3. 同一パターンが repeated_pattern_min (3) 回以上出現 → リストアイテム
4. リストアイテムの親をリストコンテナとして提案

### 等間隔検出

1. 兄弟要素間のスペーシング（gap）を計算
2. Gap の変動係数（CV = 標準偏差 / 平均）を算出
3. CV < cv_threshold (0.25) → 等間隔配置として検出

### 垂直ゾーンマージ

1. 兄弟要素をY座標範囲でゾーンに分類
2. ゾーン同士の重なり率を計算（zone_overlap_item: 50%, zone_overlap_zone: 30%）
3. 閾値以上の重なり → ゾーンをマージしてグルーピング候補

### 連続パターン検出

```
1. 各兄弟要素の structure_hash を計算
2. 連続する要素のハッシュを Jaccard 類似度 >= 0.7 で比較
3. 3回以上連続でマッチ → 連続パターングループ
4. グループの suggested_name は先頭要素の名前から推論
```

### ヘッディング-コンテンツペア検出

```
1. 兄弟要素を順番にスキャン
2. is_heading_like 判定: 子要素5個以下、TEXT/VECTOR/ELLIPSE葉が50%以上
3. heading の高さ < 次の兄弟の高さ × 0.4 → ペア検出
4. ペアは section-{heading-text-slug} として命名
```

### 遊離要素吸収

```
1. グルーピング後、未グループ要素をスキャン
2. LINE型、または高さ20px以下のリーフ要素を「遊離」と判定
3. 200px以内の最近グループに吸収
4. 吸収先はY座標距離で決定
```

### 背景-コンテンツレイヤー分離（Issue 180）

```
1. 兄弟要素から全幅RECTANGLE（親幅の80%以上、リーフノード、親高さの30%以上）を検出
2. 該当が1個のみ → 背景候補
3. 背景RECTANGLEとbbox重複する小型VECTOR/ELLIPSE（面積5%未満）を装飾として検出
4. 残り = コンテンツ要素。2個以上あれば content-layer グループを提案
5. bg_node_ids に背景+装飾、node_ids にコンテンツを格納
```

### テーブル行構造検出（Issue 181）

```
1. 兄弟要素から全幅RECTANGLE（親幅の90%以上、リーフノード）を3+個検出 → 行背景
2. 全幅VECTOR/LINE（親幅の90%以上、高さ2px以下）を区切り線として検出
3. 各RECTANGLEのY範囲内にY中心が入るTEXT等を行メンバーとして割り当て
4. 最初のRECTANGLEより上にあるFRAME/TEXT等をヘッダーとして包含
5. 全メンバー + 区切り線を table-{slug} グループとして提案
```

### リピーティングタプルパターン検出（Issue 186）

```
1. 兄弟要素のtype列を抽出: ['RECTANGLE', 'FRAME', 'INSTANCE', 'RECTANGLE', 'FRAME', 'INSTANCE', ...]
2. tuple_size を TUPLE_MAX_SIZE (5) から 2 まで降順に試行（大きいタプル優先）
3. 各 tuple_size で type 列をスライドウィンドウ走査
4. 参照タプル内の distinct type 数が 2 未満 → スキップ（同一type列は consecutive で処理）
5. 参照タプルと完全一致する連続タプルを数える
6. TUPLE_PATTERN_MIN (3) 回以上連続 → タプルグループとして検出
7. 検出済みインデックスは covered に記録し重複を防止
8. 複数の非重複タプルパターンを同時検出可能
```

### 装飾ドットパターン検出（Issue 189）

```
1. FRAME/GROUP ノードで子要素あり
2. サイズが DECORATION_MAX_SIZE (200px) x 200px 以下
3. 葉ノード（再帰的に展開）の 60%+ が ELLIPSE/RECTANGLE/VECTOR
4. シェイプ葉ノードが 3 個以上
5. ELLIPSE が最多 → decoration-dots-{index}、それ以外 → decoration-pattern-{index}
```

### ハイライトテキスト検出（Issue 190）

```
1. 兄弟要素から RECTANGLE（リーフ）+ TEXT ペアを検索
2. Y範囲の重なり率 >= 80%（小さい方の高さ基準）
3. X範囲も 50%+ 重なり
4. RECTANGLE の高さが TEXT の 0.5-2.0 倍
5. TEXT の文字数が 30 文字以下
6. 検出ペアを highlight-{text-slug} グループとして提案
7. Phase 2 の非ルートレベルで実行
```

### セマンティック検出（Phase 2 Stage A）

| 検出タイプ | 判定条件 | 推論結果 |
|-----------|---------|---------|
| Card | FRAME/COMPONENT/INSTANCE、子2-6個、IMAGE/RECTANGLE + TEXT | card |
| Navigation | 4+子要素、水平配置、各TEXT幅 < 200px | nav |
| Grid | 2+行 × 2+列、要素サイズ類似（20%以内） | list |
| Header | 上部ゾーン + ナビTEXT + ロゴ要素 | header |
| Footer | 下部ゾーン + 2+要素 | footer |
| Bg-Content | 全幅RECTANGLE(80%+) + 装飾VECTOR/ELLIPSE → bg-layer、残り → content-layer | content-layer（Issue 180） |
| Table | 3+全幅RECTANGLE(90%+) + VECTOR/LINE区切り線 + TEXT行メンバー | table（Issue 181） |
| Highlight | RECTANGLE + TEXT 同位置ペア（Y重なり80%+、X重なり50%+） | highlight（Issue 190） |
| Horizontal-Bar | 狭Y帯域(<100px)に4+要素、RECTANGLE背景あり、水平分布(X分散>Y分散×3) | horizontal-bar / news-bar（Issue 184） |
| Two-Column | テキスト群が片側+画像がもう片側、X座標で左右分離 | two-column（Issue #223、Stage C Claude推論） |
| Decoration | ドットグリッド等の装飾FRAME、コンテンツと分離 | decoration（Issue #223、Stage C Claude推論） |
| Variant | 同一componentIdのINSTANCE 2+個 | variant（Proposal 5、componentIdベース） |

## Auto Layout推論ロジック

### 方向判定

```
2要素の場合:
  dx = |center_x1 - center_x2|
  dy = |center_y1 - center_y2|
  dx > dy → HORIZONTAL, それ以外 → VERTICAL

3要素以上（3段階フォールバック）:
  Stage 1: x_variance > y_variance * 1.5 → HORIZONTAL
  Stage 1: y_variance > x_variance * 1.5 → VERTICAL
  Stage 2: 曖昧な場合 → 行数 vs 列数で判定
    行数 < 列数 → HORIZONTAL
    列数 < 行数 → VERTICAL
    同数 → HORIZONTAL（デフォルト）
```

### WRAP検出

```
方向判定後:
  HORIZONTAL + 4+要素 + Y座標が2+行に分かれる(row_tolerance=20px) → WRAP
  WRAP時はdirectionを'WRAP'に上書き
```

### SPACE_BETWEEN検出

```
先頭要素が親の開始端に接触(4px以内) + 末尾要素が終了端に接触
  → primaryAxisAlignItems = 'SPACE_BETWEEN'
それ以外 → MIN
```

### Gap推論

```
gaps = [隣接要素間のスペーシング]
raw_gap = median(gaps)
gap = round(raw_gap / grid_snap) * grid_snap  # 4px刻みにスナップ
```

### Padding推論

```
padding_top = min(child.y) - parent.y
padding_left = min(child.x) - parent.x
padding_bottom = (parent.y + parent.height) - max(child.y + child.height)
padding_right = (parent.x + parent.width) - max(child.x + child.width)
# 各値を4px刻みにスナップ
```

## 開発ルール（コーディング規約）

figma-prepare のスクリプト・ユーティリティを新規作成・修正する際に必ず守るルール。
過去のバグパターンから抽出した予防策。

### 1. Hidden Children フィルタ（必須）

`children` を処理する全関数の冒頭で `visible: false` をフィルタせよ。
フィルタなしで children を走査すると、非表示要素の座標が検出・推論を狂わせる。

```python
# ✅ 正しい — 冒頭でフィルタ
children = [c for c in node.get('children', []) if c.get('visible') != False]

# ❌ 禁止 — フィルタなしで直接走査
children = node.get('children', [])
```

**適用対象**: `walk_and_detect`, `infer_layout`, `walk_and_infer`, `count_nodes`, 新規関数すべて

### 2. ゼロ除算ガード（必須）

割り算の前に分母が 0 でないことを確認せよ。
統計関数（`mean`, `stdev`）の結果も分母に使う場合は同様。

```python
# ✅ 正しい
mean_val = statistics.mean(values)
if mean_val <= 0:
    return default_value
cv = statistics.stdev(values) / mean_val

# ❌ 禁止
cv = statistics.stdev(values) / statistics.mean(values)
```

**特に注意**: gap計算、比率計算、面積計算、bbox の w/h

### 3. 座標パラメータ伝播（必須）

`root_x` / `root_y` を受け取る関数を呼ぶ際は、必ずアートボードの原点座標を渡せ。
デフォルト値 `0` に頼ると、マイナス座標アートボードで誤判定が発生する。

```python
# ✅ 正しい — 呼び出し元で root_x/root_y を渡す
generate_enriched_table(children, page_width=w, page_height=h, root_x=root_bb['x'], root_y=root_bb['y'])

# ❌ 禁止 — root_x/root_y を省略（デフォルト 0 に落ちる）
generate_enriched_table(children, page_width=w, page_height=h)
```

**対象関数**: `is_off_canvas`, `_compute_flags`, `generate_enriched_table`

### 4. 定数の一元管理（必須）

新しい閾値・マジックナンバーは以下の2箇所に**同時に**定義せよ:

| 場所 | 役割 |
|------|------|
| `figma_utils.py` 冒頭の定数セクション | 実装で参照する Python 定数 |
| `.claude/rules/figma-prepare.md` の閾値パラメータ表 | ドキュメント・レビュー用 |

```python
# ✅ 正しい — figma_utils.py に名前付き定数
NEW_THRESHOLD = 42  # 新しい閾値の説明（Issue NNN）

# ❌ 禁止 — スクリプト内にマジックナンバー
if some_value > 42:  # なぜ 42？
```

**ルール**:
- 定数名は `UPPER_SNAKE_CASE`
- コメントに用途と Issue 番号を記載
- `figma-prepare.md` の閾値パラメータ表にも行を追加

### 5. 再帰スキップ対象の明示（推奨）

特定条件のノードで再帰をスキップする場合、スキップ理由をコメントで明示せよ。
スキップ漏れ（無駄な再帰）とスキップ過剰（検出漏れ）の両方を防ぐ。

```python
# ✅ 正しい — スキップ理由を明示
# Skip: decoration patterns have no meaningful sub-structure (Issue 240)
if not is_root and is_decoration_pattern(child):
    continue

# Skip: protected nodes preserve designer intent (Issue 221)
if not is_root and _is_protected_node(node):
    for child in children:
        walk_and_detect(child, ...)  # recurse but don't detect at this level
    return
```

### 6. テスト必須（必須）

新規関数・バグ修正には必ずユニットテスト + ベンチマーク回帰テストを実施せよ。

### 7. ベンチマーク回帰テスト（必須）

ロジック変更後は実務デザインベンチマークで精度が劣化していないことを確認せよ。

```bash
python3 tests/figma-prepare/benchmark/run_benchmark.py --all
```

| データ | ファイル | ノード数 | 検証ポイント |
|--------|---------|---------|------------|
| /iso | `tests/figma-prepare/benchmark/data/iso.xml` | 167 | EN+JP 4ペア, bullet 6, section-bg 12 |
| /csr | `tests/figma-prepare/benchmark/data/csr.xml` | 302 | EN+JP 10ペア, bullet 18, section-bg 12, zone 9 |

ベースライン結果は `tests/figma-prepare/benchmark/results/` にある。
変更後の結果をベースラインと比較し、指標悪化がないことを確認してからコミットせよ。

### ユニットテスト

| 変更種別 | 最低テスト数 |
|---------|------------|
| 新規関数 | 正常系 2 + エッジケース 1 |
| バグ修正 | 再現テスト 1 + 回帰テスト 1 |
| 定数変更 | 境界値テスト 1 |

**エッジケースの必須チェック項目**:
- 空配列 / None
- 要素数 0, 1, 2（最小ケース）
- ゼロサイズ要素（w=0, h=0）
- マイナス座標
- `visible: false` の要素が混在

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| レイヤーの削除 | デザイン情報の損失 |
| ビジュアルプロパティの変更（色・フォント・サイズ等） | デザイン崩れ |
| コンポーネントインスタンスのdetach | コンポーネント関係の破壊 |
| 元アートボードの直接変更 | 復元不能のリスク（Adjacent Artboard 方式を使用） |
| 非表示レイヤーの操作 | 意図的に非表示の可能性 |
| children 直接走査（hidden フィルタなし） | 非表示要素による検出・推論の歪み |
| ガードなし除算 | ZeroDivisionError |
| スクリプト内マジックナンバー | 保守性低下・二重管理 |
| root_x/root_y 省略での座標関数呼び出し | マイナス座標アートボードで誤判定 |

## 安全策

| 対策 | 内容 |
|------|------|
| Adjacent Artboard 必須 | Phase 2以降は clone した隣接アートボード上で実行（元デザインは不変） |
| dry-run デフォルト | Phase 2-4は--dry-runがデフォルト、--applyで実行 |
| バッチ実行 | 50件/回のバッチで処理（タイムアウト回避） |
| ID存在チェック | evaluate_script前に全nodeIdの存在を確認 |
| Undo可能 | Figma側でCtrl+Zで復元可能であることを案内 |

## チェックリスト

### 実行時
- [ ] Phase 1 の品質スコアを確認した
- [ ] グレードに応じた推奨フェーズを実行した
- [ ] Phase 2以降は clone した隣接アートボード上で実行した
- [ ] dry-runで結果を確認してから--applyした
- [ ] リネーム結果が命名規約に沿っている
- [ ] グルーピングでレイアウトが崩れていない
- [ ] Auto Layout適用後の表示を確認した

### 開発時（コード変更時）
- [ ] children 走査前に `visible != False` フィルタを入れた
- [ ] 除算の前にゼロガードを入れた
- [ ] 座標関数の呼び出しで root_x/root_y を渡した
- [ ] 新しい閾値は figma_utils.py + figma-prepare.md の両方に定義した
- [ ] ユニットテストを追加した（正常系 + エッジケース）
- [ ] ベンチマーク回帰テストを実行した（`run_benchmark.py --all`）
- [ ] 再帰スキップにはコメントで理由を明示した
