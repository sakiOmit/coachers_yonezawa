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
score -= min(20, flat_sections * 5)           # フラットセクション数 × 5、上限-20
score -= min(10, ungrouped_candidates * 1)    # 未グループ候補数 × 1、上限-10（最も不安定な指標のため抑制）
score -= min(15, deep_nesting_count * 3)      # 深すぎるネスト数 × 3、上限-15
# autolayout_penalty は除外（get_metadataにlayoutMode情報なし、計測不能）
score = max(0, score)
```

**注意**: deep_nesting_count はセクションルート（width≈1440のフレーム）からの相対深度で計算。

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
