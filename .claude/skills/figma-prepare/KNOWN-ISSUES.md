# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 15: `get_design_context` 補完パイプライン

- **Phase**: 新規 Phase 1.5（Phase 1 と Phase 2 の間に挿入）
- **現象**: `get_metadata` のみでは取得できない情報（layoutMode, fills, characters等）により、リネーム精度に限界がある
- **具体例**: `Group 46165`（ヘッダー: ロゴ画像 + ハンバーガー + ナビ10リンク）→ `group-7` フォールバック。`get_design_context` があれば fills から「ロゴ画像」「背景色」等を判定でき、`header` と推論可能
- **影響**: group-* フォールバック率がお知らせ記事で25%。特にヘッダー/フッター等のセマンティックな構造が判定不能
- **対策**: セクション単位で `get_design_context` を呼び出し、metadata に fills・layoutMode・characters を補完するスクリプトを新設
- **優先度**: 短期（実装決定済み）

### Issue 16: ヘッダー/フッターのセマンティック推論強化

- **Phase**: 2
- **現象**: ページ最上部のフレーム（ロゴ + ナビ + ハンバーガー）が `group-*` にフォールバック。ページ最下部のフレーム（コピーライト + リンク群）も同様
- **原因**: 現在の Priority 3 はトップレベル FRAME (parent=PAGE) のみ `section-header/footer` と判定。GROUP 型や、PAGE 直下でないネストされたヘッダーには効かない
- **検出元**: 募集一覧 (1:4) の `Group 46165` → `group-7`
- **想定対策**:
  - Position + 子構造のヒューリスティック: 最上部 + (ロゴ画像 + ナビリンク群) → `header`
  - `get_design_context` 補完データの fills で IMAGE 判定 → ロゴ検出精度向上
  - 最下部 + テキスト子のみ → `footer`
- **依存**: Issue 15 の補完データがあれば精度大幅向上。なくても座標+構造で部分対応可能

### Issue 17: fills ベースの IMAGE 判定

- **Phase**: 2
- **現象**: `RECTANGLE` に IMAGE fill がある要素（ACF画像フィールド相当）が `bg-*` にリネームされる。実際は `img-hero` 等が適切
- **原因**: `get_metadata` には fills 情報がないため、RECTANGLE は全て `SHAPE_PREFIXES['RECTANGLE'] = 'bg'` に分類
- **検出元**: 募集一覧 (1:4) の `image 1347` → `bg-4`（実際はヒーロー画像）
- **想定対策**: `get_design_context` から fills を取得。`fills[0].type === 'IMAGE'` なら `img-*` に分類
- **依存**: Issue 15

### Issue 18: layoutMode 補完による Phase 4 精度向上

- **Phase**: 4
- **現象**: Auto Layout の方向・gap・padding は全て座標推論に依存。実際の layoutMode があれば推論不要
- **原因**: `get_metadata` に layoutMode が含まれない（Issue 2 で workaround 済み）
- **想定対策**: `get_design_context` から layoutMode, itemSpacing, paddingTop/Right/Bottom/Left を取得し、Phase 4 推論結果を上書き
- **依存**: Issue 15

## 改善方針

### 短期（Issue 15-16）

1. **Phase 1.5 新設**: `get_design_context` 補完スクリプト（`enrich-metadata.sh`）
   - セクションルート単位で `get_design_context` を呼び出し
   - fills, layoutMode, characters を metadata JSON にマージ
   - トークン消費の実測（3ページで計測）
2. **ヘッダー/フッター推論**: Position + 子構造ヒューリスティック強化

### 中期（Issue 17-18）

1. **fills ベース IMAGE 判定**: RECTANGLE の bg/img 分類改善
2. **layoutMode 補完**: Phase 4 の推論→実値切り替え

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 39件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 2 フォールバック率 50% 以下達成済み → 目標: 15% 以下
- 新規指標: ヘッダー/フッター検出率（実データ3ページで計測）

## 一覧

| Issue | Phase | 状態 | 概要 |
|-------|-------|------|------|
| 1-14 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 15 | 1.5 | **OPEN** | `get_design_context` 補完パイプライン |
| 16 | 2 | **OPEN** | ヘッダー/フッターのセマンティック推論強化 |
| 17 | 2 | **OPEN** | fills ベースの IMAGE 判定 |
| 18 | 4 | **OPEN** | layoutMode 補完による Phase 4 精度向上 |
