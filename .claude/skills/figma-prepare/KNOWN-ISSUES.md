# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

（現在 OPEN な課題はありません）

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 46件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 2 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%

### 次の改善候補

- 実プロジェクトでの `/figma-prepare --enrich` 実運用テスト（トークン消費計測含む）
- characters フィールドを活用した TEXT コンテンツベースのリネーム精度向上
- 複数ページ横断での共通ヘッダー/フッター自動検出

## 一覧

| Issue | Phase | 状態 | 概要 |
|-------|-------|------|------|
| 1-14 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 15 | 1.5 | **FIXED** | `get_design_context` 補完パイプライン — `enrich-metadata.sh` 新設 |
| 16 | 2 | **FIXED** | ヘッダー/フッターのセマンティック推論強化 — Priority 3.1 追加 |
| 17 | 2 | **FIXED** | fills ベースの IMAGE 判定 — Priority 2 で fills チェック |
| 18 | 4 | **FIXED** | layoutMode 補完による Phase 4 精度向上 — exact confidence |
