# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 12: `to_kebab()` の日本語部分マッチが誤ヒットする

- **Phase**: 2
- **現象**: `"大規模イベントに強いオペレーション力"` → `"イベント"` が部分マッチ → `heading-event` を返す。実際はポイント見出しであり `event` は意図と異なる
- **原因**: `JP_KEYWORD_MAP` は `if jp in text` で部分一致検索しており、長文テキストの一部にキーワードが含まれると誤マッチする
- **影響**: Point 1〜5 の見出しコンテナが全て `heading-event` になる等、misleading な名前が生成される
- **検出元**: layers_bondish 04_REASON (1:1437) での実行結果
- **想定対策**: 短テキスト（≤20文字程度）のみキーワードマッチ適用、または完全一致優先＋部分一致は短文限定

### Issue 13: JP_KEYWORD_MAP 未登録の日本語がそのまま出力される

- **Phase**: 2
- **現象**: `"無料相談"` → `btn-無料相談`、`"資料請求"` → `btn-資料請求`。kebab-case名に日本語が混入
- **原因**: `to_kebab()` のASCIIロジック (`re.sub(r'[^\w\s-]', '', text.lower())`) で日本語文字が `\w` にマッチし除去されずに残る
- **影響**: レイヤー名としては機能するが、kebab-case規約に反する。実装時のクラス名生成に支障
- **検出元**: layers_bondish 04_REASON (1:1437) での実行結果
- **想定対策**: (A) JP_KEYWORD_MAP を拡充（`無料相談→free-consultation`, `資料請求→request-docs`等）、(B) ASCII以外の文字をフォールバック除去するオプション追加

### Issue 14: heading vs body テキストの誤判定

- **Phase**: 2
- **現象**: 見出しテキスト＋本文テキストを含むフレーム（2 TEXT子）が `heading-*` に分類される。実際は `text-block-*` または `content-*` が適切
- **原因**: Priority 4 の heading 判定が「1-2 TEXT子 + 画像なし + 子3以下」で発火。見出し+本文の構造でも条件を満たす
- **影響**: `heading-ケータリングにとどまらず企画段階からご担当者様を...`（本文テキストがheading名に）
- **検出元**: layers_bondish 04_REASON (1:1437) での実行結果
- **想定対策**: TEXT子の高さ/行数で見出しと本文を区別。高さ>100pxまたは文字数>50の TEXT 子がある場合は `content-*` に分類

### Issue 15: `get_design_context` 補完による精度向上（中期）

- **Phase**: 全フェーズ
- **現象**: `get_metadata` のみでは取得できない情報（layoutMode, characters, fills等）により、精度に限界がある
- **影響**: group-* フォールバック率が40%前後で頭打ち。Auto Layout検出は推論のみ
- **想定対策**: セクション単位で `get_design_context` を追加呼び出しし、layoutMode・fills等を補完。トークン消費とのトレードオフを検証
- **優先度**: 中期。analyze→実装ワークフローの実績データで効果を測定してから着手

## 改善方針

### 短期（Issue 12-14）

- Phase 2 リネーム精度の改善。Fallback率42%→30%以下を目指す
- `to_kebab()` の日本語処理改善、heading/body判定ロジック改善

### 中期（Issue 15）

1. **`get_design_context` 補完**: analyze→実装の結果フィードバックを基にチューニング
2. **Phase 3 の精度向上**: 座標修正（Issue 8）後の実データで候補品質を再評価。必要に応じて proximity_gap 閾値のチューニング
3. **Phase 4 の精度向上**: Padding計算の実データ検証。Issue 8 修正後の精度を3件で確認し、必要なら補正ロジック追加

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 37件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 2 フォールバック率 50% 以下達成済み（yonezawa 3件 + layers_bondish 1件）

## 一覧

| Issue | Phase | 状態 | 概要 |
|-------|-------|------|------|
| 1-11 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 12 | 2 | **OPEN** | `to_kebab()` 日本語部分マッチの誤ヒット |
| 13 | 2 | **OPEN** | JP_KEYWORD_MAP 未登録の日本語がそのまま出力 |
| 14 | 2 | **OPEN** | heading vs body テキストの誤判定 |
| 15 | 全 | **OPEN** | `get_design_context` 補完による精度向上（中期） |
