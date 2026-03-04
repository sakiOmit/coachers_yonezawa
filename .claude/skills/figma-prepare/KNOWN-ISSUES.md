# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 3: リネーム推論の精度不足

- **Phase**: 2
- **現象**: `group-6`, `frame-0` 等のフォールバック名が多い（305件中、大半がPriority 4-5）
- **原因**: `get_metadata` のXML出力に `characters`（テキスト内容）が含まれない。Priority 1（テキスト内容ベース推論）が全く効かない
- **影響**: リネーム後の名前がセマンティックでなく、実用性が低い
- **修正方針**: Phase 2 の開始時に `get_design_context` をセクション単位で取得し、テキスト内容を rename ロジックに注入する
- **ファイル**: `scripts/generate-rename-map.sh` + `SKILL.md` Phase 2 のフロー

### Issue 6: タブ/ボタンが text-block にリネームされる

- **Phase**: 2
- **現象**: お知らせ一覧のタブ (Frame 94-98) → `text-block-0~4`。お知らせ記事のボタン (Frame 66 = 一覧に戻る) → `text-block-1`
- **原因**: 1テキスト子を持つフレーム = text-block と推論される。ボタン/タブの検出ロジックが弱い
- **影響**: Issue 3 の一部。テキスト内容があれば `btn-*` / `tab-*` と推論可能
- **修正方針**: Issue 3 の `get_design_context` テキスト注入で改善。加えて、サイズヒューリスティック（height < 70 & width < 300 → ボタン候補）を追加
- **ファイル**: `scripts/generate-rename-map.sh`

## 改善方針

### 短期（次セッション）

1. **Issue 3 + 6**: リネーム精度の改善
   - Phase 2 開始時に `get_design_context` をセクション単位で取得
   - テキスト内容（`characters`）をリネーム推論に注入
   - ボタン/タブのサイズヒューリスティック追加（height < 70 & width < 300）
   - 実データ3件で改善率を計測

### 中期

2. **Phase 3 の精度向上**: 座標修正（Issue 8）後の実データで候補品質を再評価。必要に応じて proximity_gap 閾値のチューニング
3. **Phase 4 の精度向上**: Padding計算の実データ検証。Issue 8 修正後の精度を3件で確認し、必要なら補正ロジック追加

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内
- 実データ3件: Phase 2 の Priority 4-5 率を 95% → 50% 以下に改善（Issue 3 解決時）

## 一覧

| Issue | Phase | 状態 | 概要 |
|-------|-------|------|------|
| 3 | 2 | **OPEN** | characters 不足で Priority 1 不可 |
| 6 | 2 | **OPEN** | Issue 3 と関連 |
| 1, 2, 4, 5, 7-11 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
