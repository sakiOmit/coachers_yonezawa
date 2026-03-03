# Complexity Calculation & Catalog Matching Details

## Phase 2: 複雑度スコア計算

### スコア公式

```
complexity = min(children * 2, 40)
           + min(depth * 5, 30)
           + min(text_count, 20)
           + min(height / 1000, 10)
```

### スコア要素

| 要素 | 最大スコア | 計算方法 | 根拠 |
|------|-----------|---------|------|
| 子要素数 | 40 | children × 2 | 直接の子要素が多いほど構造が複雑 |
| ネスト深度 | 30 | depth × 5 | 深いネストは分割の必要性を示す |
| テキスト要素数 | 20 | text_count × 1 | テキスト要素はコンテンツ密度の指標 |
| フレーム高さ | 10 | height / 1000 | 高さはトークン消費量の近似値 |

### 戦略判定マトリクス

| 条件 | 戦略 | アクション |
|------|------|----------|
| height < 5000 AND score < 50 | `NORMAL` | 通常取得（get_design_context 1回） |
| height >= 8000 OR score >= 70 | `SPLIT` | 分割取得推奨 |
| height >= 10000 | `SPLIT_REQUIRED` | 分割取得必須 |
| それ以外 | `NORMAL` | 通常取得 |

### 除外条件

- `visible: false` のフレームはスキップ
- hidden レイヤーは複雑度計算から除外

## Phase 3: 共通コンポーネント検出

### 3-1. 名前一致検出

メタデータのレイヤー名が複数ページで一致するものを抽出:

```
例: "Header", "Footer", "CTA Section" が3ページに出現
→ 共通コンポーネント候補
```

### 3-2. 位置一致検出

同一の相対位置（top/bottom）に同種の要素が配置されているものを検出:

```
例: 全ページの最上部に "Header" (y=0, height≈80)
→ 共通ヘッダー
```

### 3-3. 構造一致検出

子要素の構成が類似するフレームを検出:

```
例: Page A の "Card" と Page B の "Card" が同じ子要素構造
→ 共通カードコンポーネント
```

### 3-4. Instance検出

Figma Component Instance（`type: "INSTANCE"`）を検出:

```
例: 同一 componentId を持つ Instance が複数ページに存在
→ Figma上で既にコンポーネント化済み
```

### 検出結果フィールド

| フィールド | 説明 |
|-----------|------|
| name | コンポーネント名 |
| detection_method | 検出手法（name/position/structure/instance） |
| pages | 出現ページリスト |
| occurrence_count | 出現回数 |
| suggested_type | 推定タイプ（header/footer/card/button/etc） |

## Phase 4: カタログマッチング

### マッチングスコア計算

| 条件 | スコア |
|------|--------|
| type 一致 | +40% |
| 必須props充足 | +30% |
| variant対応可能 | +20% |
| figma_patterns一致 | +10% |

**注意**: Code Connect は使用しない。カタログのみで判定。

### 判定閾値

| スコア | 判定 | アクション |
|--------|------|----------|
| 70%以上 | `REUSE` | 既存コンポーネントをそのまま使用 |
| 40-69% | `EXTEND` | 既存ベース + カスタムスタイル |
| 40%未満 | `NEW` | 新規コンポーネント作成 |

### 再利用判定表（出力例）

```
| Component | Score | Decision | Existing Match | Action |
|-----------|-------|----------|----------------|--------|
| Header    | 85%   | REUSE    | c-page-header  | Use as-is |
| CTA Card  | 55%   | EXTEND   | c-card         | Add variant |
| Hero      | 20%   | NEW      | -              | Create new |
```
