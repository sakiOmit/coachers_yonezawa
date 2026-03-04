# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 19: Phase 3 を Claude 推論ベースに拡張（セクショニング対応）

- **Phase**: 3
- **優先度**: 高
- **概要**: 現状の Phase 3（グルーピング検出）は bash heuristic（proximity / pattern / semantic / page-kv）のハードコードパターンのみ。セクショニング（トップレベル children をセクション単位に分割）ができない。
- **課題**:
  - パターン追加 = コード追加（スケールしない）
  - リード文をKVに含めるか等の曖昧な判断ができない
  - セクション境界の推論が不可能
- **提案**:
  - Phase 3 を「bash heuristic（プレフィルタ）+ Claude 推論（最終判断）」の2段構成に変更
  - 入力: children 一覧（id, name, type, bbox）+ `get_screenshot`
  - 出力: セクション分割案 + グルーピング案 + 推奨名
  - bash script は proximity 検出等の補助として残す
- **検証済みPOC**: 募集一覧（1:4）で metadata + screenshot から以下を正しく推論:
  - `l-header`: 1:106
  - `section-page-kv`: 1:102 + 1:105 + 1:101 + 1:5（見出し+パンくず+装飾+リード）
  - `section-job-listing`: 1:6 + 1:15 + 1:97（タブ+一覧+空状態）
- **影響ファイル**: SKILL.md (Phase 3 フロー), detect-grouping-candidates.sh (補助化)

### Issue 20: Before/After 検証を構造 diff ベースに変更

- **Phase**: 2, 3
- **優先度**: 中
- **概要**: 現状の Phase 2 Step 2-3e はスクショ比較だが、リネーム/グルーピングはビジュアルが変わらないためスクショでは差分が見えない。
- **課題**:
  - リネーム: 見た目は同一、レイヤー名だけ変わる → スクショ比較は無意味
  - グルーピング: 構造変更が正しいか確認するにはツリー比較が必要
- **提案**:
  - リネーム検証: apply-renames.js の戻り値（`[{oldName, newName}]`）で十分（既に実装済み）
  - グルーピング検証: apply 後に `evaluate_script` でクローン側ツリーを読み戻し → 計画との structural diff
  - スクショは「ビジュアル崩れがないか」の補助チェックに限定
  - SKILL.md Phase 2 Step 2-3e を「構造 diff + 補助スクショ」に修正
- **影響ファイル**: SKILL.md (Phase 2, 3 検証フロー), 新規 verify-structure.js (readback スクリプト)

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 46件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 2 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%

### 次の改善候補

- **Issue 19**: Phase 3 Claude 推論ベース拡張（セクショニング）
- **Issue 20**: Before/After 構造 diff 検証
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
| 19 | 3 | **OPEN** | Phase 3 を Claude 推論ベースに拡張（セクショニング対応） |
| 20 | 2,3 | **OPEN** | Before/After 検証を構造 diff ベースに変更 |
