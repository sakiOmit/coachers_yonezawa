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

※ マッチングはケースインセンシティブ（大文字小文字を区別しない）。例: "rectangle 1", "FRAME 2" もマッチする。

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
| cv_threshold | 0.25 | 等間隔スペーシング検出の変動係数閾値（Issue 138） |
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
| 3.1 | ヘッダー/フッター検出 | 上端+幅広+ナビ子要素 / 下端+コンパクト+テキスト多 | header, footer |
| 3.2 | 小アイコン検出 | 子なし、48x48以下 | icon-0 |
| 3.5 | ナビゲーション検出 | 4+短テキスト子要素、水平配置 | nav-0 |
| 4 | 子構造分析 | 子要素の構成から推論 | img+text+btn → card |
| 5 | フォールバック | 上記で判定不可 | {type}-{index} |

## グルーピング検出アルゴリズム

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

### セマンティック検出（Phase 2 Stage A）

| 検出タイプ | 判定条件 | 推論結果 |
|-----------|---------|---------|
| Card | FRAME/COMPONENT/INSTANCE、子2-6個、IMAGE/RECTANGLE + TEXT | card |
| Navigation | 4+子要素、水平配置、各TEXT幅 < 200px | nav |
| Grid | 2+行 × 2+列、要素サイズ類似（20%以内） | list |
| Header | 上部ゾーン + ナビTEXT + ロゴ要素 | header |
| Footer | 下部ゾーン + 2+要素 | footer |

## Auto Layout推論ロジック

### 方向判定

```
2要素の場合:
  dx = |center_x1 - center_x2|
  dy = |center_y1 - center_y2|
  dx > dy → HORIZONTAL, それ以外 → VERTICAL

3要素以上:
  x_variance = 子要素のX座標の分散
  y_variance = 子要素のY座標の分散
  x_variance > y_variance * 1.5 → HORIZONTAL, それ以外 → VERTICAL
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

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| レイヤーの削除 | デザイン情報の損失 |
| ビジュアルプロパティの変更（色・フォント・サイズ等） | デザイン崩れ |
| コンポーネントインスタンスのdetach | コンポーネント関係の破壊 |
| 元アートボードの直接変更 | 復元不能のリスク（Adjacent Artboard 方式を使用） |
| 非表示レイヤーの操作 | 意図的に非表示の可能性 |

## 安全策

| 対策 | 内容 |
|------|------|
| Adjacent Artboard 必須 | Phase 2以降は clone した隣接アートボード上で実行（元デザインは不変） |
| dry-run デフォルト | Phase 2-4は--dry-runがデフォルト、--applyで実行 |
| バッチ実行 | 50件/回のバッチで処理（タイムアウト回避） |
| ID存在チェック | evaluate_script前に全nodeIdの存在を確認 |
| Undo可能 | Figma側でCtrl+Zで復元可能であることを案内 |

## チェックリスト

- [ ] Phase 1 の品質スコアを確認した
- [ ] グレードに応じた推奨フェーズを実行した
- [ ] Phase 2以降は clone した隣接アートボード上で実行した
- [ ] dry-runで結果を確認してから--applyした
- [ ] リネーム結果が命名規約に沿っている
- [ ] グルーピングでレイアウトが崩れていない
- [ ] Auto Layout適用後の表示を確認した
