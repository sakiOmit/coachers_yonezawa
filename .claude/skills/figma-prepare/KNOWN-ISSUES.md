# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

現在 OPEN の課題はありません。

## 改善方針

### 中期

1. **Phase 3 の精度向上**: 座標修正（Issue 8）後の実データで候補品質を再評価。必要に応じて proximity_gap 閾値のチューニング
2. **Phase 4 の精度向上**: Padding計算の実データ検証。Issue 8 修正後の精度を3件で確認し、必要なら補正ロジック追加

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 37件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ3件: Phase 2 フォールバック率 50% 以下達成済み

## 一覧

| Issue | Phase | 状態 | 概要 |
|-------|-------|------|------|
| 1-11 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
