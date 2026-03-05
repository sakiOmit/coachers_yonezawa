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

### 未命名レイヤーパターン（検出対象）

以下の正規表現にマッチするレイヤーを「未命名」として検出:

```
^(Rectangle|Ellipse|Line|Vector|Frame|Group|Component|Instance|Text|Polygon|Star|Image)\s*\d*$
```

## 品質スコア計算

### 計算式（100点満点）

```
score = 100
score -= min(30, unnamed_rate * 0.5)         # 未命名率（%）× 0.5、上限-30
score -= min(30, flat_sections * 5 + flat_excess * 0.5)  # フラットセクション数 × 5 + 超過子要素数 × 0.5、上限-30
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
| flat_threshold | 15 children | フラット構造の検出閾値 |
| repeated_pattern_min | 3 occurrences | リピートパターンの最小検出回数 |
| grid_snap | 4px | Gap/Paddingのスナップ単位 |
| deep_nesting_threshold | 6 levels | 深すぎるネストの閾値 |
| batch_size | 50 nodes | Chrome DevTools実行時のバッチサイズ |
| variance_ratio | 1.5 | Auto Layout方向判定（X分散 > Y分散 × ratio → HORIZONTAL） |
| spatial_gap_threshold | 100px | サブグループ分割の最小ギャップ |
| header_zone_height | 120px | ヘッダー検出ゾーン（ページ上端からの距離） |
| footer_zone_height | 300px | フッター検出ゾーン（ページ下端からの距離） |
| zone_overlap_item | 0.5 (50%) | 垂直ゾーンマージ：アイテム側の最小重なり率 |
| zone_overlap_zone | 0.3 (30%) | 垂直ゾーンマージ：ゾーン側の最小重なり率 |
| jaccard_threshold | 0.7 | パターン検出のファジーマッチ閾値 |
| header_max_element_height | 200px | ヘッダーグループ内要素の最大高さ（Issue 125） |
| footer_zone_margin | 50px | フッターゾーン下方マージン（ページ外要素包含用、Issue 129） |
| divider_max_height | 5px | 水平区切り線の最大高さ（Phase 3 リネーム、Issue 124） |
| header_y_threshold | 100px | ヘッダー検出Y位置閾値（Phase 3 リネーム、Issue 124） |
| footer_proximity | 100px | フッター検出の親下端からの距離（Phase 3 リネーム、Issue 124） |
| footer_max_height | 200px | フッター検出の最大高さ（Phase 3 リネーム、Issue 124） |
| wide_element_ratio | 0.7 | 「幅広」判定の親幅比率（Phase 3 リネーム、Issue 124） |
| wide_element_min_width | 500px | 「幅広」判定の最小絶対幅（Phase 3 リネーム、Issue 124） |
| icon_max_size | 48px | アイコン検出の最大幅/高さ（Phase 3 リネーム、Issue 124） |
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

## リネームロジック（優先順）

| 優先度 | 手法 | 適用条件 | 例 |
|-------|------|---------|-----|
| 1 | テキスト内容ベース | TEXT ノードの内容から推論 | "お問い合わせ" → heading-contact |
| 2 | シェイプ分析 | RECTANGLE/ELLIPSE の用途推論 | 全幅薄型 → divider |
| 3 | ポジション分析 | ページ内の位置から推論 | 最上部 → header |
| 4 | 子構造分析 | 子要素の構成から推論 | img+text+btn → card |
| 5 | フォールバック | 上記で判定不可 | {type}-{index} |

## グルーピング検出アルゴリズム

### 近接性ベース

1. 兄弟要素間の距離を計算
2. proximity_gap (24px) 以内の要素をUnion-Findで結合
3. 結合されたグループが2要素以上 → グルーピング候補

### パターン検出

1. 各要素の「構造ハッシュ」を計算（子要素タイプ + 数の組み合わせ）
2. 同一ハッシュが repeated_pattern_min (3) 回以上出現 → リストアイテム
3. リストアイテムの親をリストコンテナとして提案

### セマンティック検出

| 子要素構成 | 推論結果 |
|-----------|---------|
| IMAGE + TEXT + BUTTON | card |
| TEXT(large) + TEXT(small) | text-block |
| IMAGE + TEXT | media-object |
| FRAME × N (同構造) | list |

## Auto Layout推論ロジック

### 方向判定

```
x_variance = 子要素のX座標の分散
y_variance = 子要素のY座標の分散

if x_variance > y_variance * 1.5:
    direction = "HORIZONTAL"
else:
    direction = "VERTICAL"
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

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| レイヤーの削除 | デザイン情報の損失 |
| ビジュアルプロパティの変更（色・フォント・サイズ等） | デザイン崩れ |
| コンポーネントインスタンスのdetach | コンポーネント関係の破壊 |
| メインブランチでの直接実行 | 復元不能のリスク |
| 非表示レイヤーの操作 | 意図的に非表示の可能性 |

## 安全策

| 対策 | 内容 |
|------|------|
| ブランチ必須 | Phase 2以降はFigmaブランチ上でのみ実行 |
| dry-run デフォルト | Phase 2-4は--dry-runがデフォルト、--applyで実行 |
| バッチ実行 | 50件/回のバッチで処理（タイムアウト回避） |
| ID存在チェック | evaluate_script前に全nodeIdの存在を確認 |
| Undo可能 | Figma側でCtrl+Zで復元可能であることを案内 |

## チェックリスト

- [ ] Phase 1 の品質スコアを確認した
- [ ] グレードに応じた推奨フェーズを実行した
- [ ] Phase 2以降はFigmaブランチ上で実行した
- [ ] dry-runで結果を確認してから--applyした
- [ ] リネーム結果が命名規約に沿っている
- [ ] グルーピングでレイアウトが崩れていない
- [ ] Auto Layout適用後の表示を確認した
