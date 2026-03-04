# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 22: Phase 2 グルーピング精度が実期待に達していない — PARTIALLY FIXED

- **Phase**: 2
- **優先度**: 高
- **概要**: 募集一覧ページ (1:4) のフラットな9子要素が、関連要素ごとに適切にグルーピングされるべきだが、Stage A ヒューリスティックに不具合があった。
- **期待する構造** (figma-prepare テストファイル `34:133` に手動例あり):
  ```
  募集一覧
  ├── Group（タブ + カード一覧）
  │   ├── 2. 募集区分タブ
  │   └── 3. 募集カード一覧（12件）
  ├── 3. 募集カード一覧（0件）
  ├── TEXT（リード文）
  ├── Group（ヒーロー画像 + 見出し + パンくず）
  │   ├── Group（画像 + 見出しフレーム）
  │   │   ├── image 1347
  │   │   └── Frame 46405
  │   └── TOP > job description
  └── Group 46165（ヘッダー）
  ```
- **修正内容** (Stage A dedup ロジック修正):
  - **Root cause**: `deduplicate_candidates()` Rule 2 がルートレベル（アートボード直下）の
    proximity候補を一律削除していた。親名 "募集一覧" が UNNAMED_RE にマッチしないため、
    タブ+カード一覧 (1:6 + 1:15) の proximity グループが誤って除外されていた。
  - **Fix 1**: Rule 1 拡張 — `pattern` だけでなく `page-kv`, `semantic` も proximity より
    高優先度とし、ノード重複時に proximity を除外（リードテキスト 1:5 がヒーロー領域と
    誤マージされる問題を解消）
  - **Fix 2**: Rule 2 修正 — `root_id` パラメータを追加し、ルートノード直下の proximity
    候補は除外対象から除外。アートボード自体が命名済みでも子要素のグルーピングは有効。
  - detect-grouping-candidates.sh: `deduplicate_candidates(candidates, root_id)` に変更
- **残課題**:
  - ヒーロー画像 + 見出し + パンくずの複合グルーピング（ネスト）は未対応
  - セマンティック検出が子構造ベースのみで、位置的な視覚領域を考慮していない
  - Stage B（Claude 推論）で補完可能な範囲
- **修正日**: 2026-03-04
- **テスト**: 全60件パス（回帰なし、3件追加）
  - Issue 22: Tab + Card list grouped (proximity at root)
  - Issue 22: Lead text (1:5) not mixed with hero group
  - Issue 22: page-kv hero group (heading + breadcrumb + bg)

### Issue 23: ネストされたグルーピングが Stage A で未対応

- **Phase**: 2
- **優先度**: 低
- **概要**: Issue 22 の期待構造では、ヒーロー領域内に「画像 + 見出しフレーム」のネストされた
  グループが存在するが、Stage A の proximity/pattern/page-kv 検出は単一階層のみ動作する。
- **期待する構造**:
  ```
  Group（ヒーロー画像 + 見出し + パンくず）
  ├── Group（画像 + 見出しフレーム）  ← このネストが未対応
  │   ├── image 1347
  │   └── Frame 46405
  └── TOP > job description
  ```
- **現状**: page-kv が 1:101 + 1:102 + 1:105 をフラットに検出するが、内部のネスト構造は生成しない
- **対応方針**: Stage B（Claude 推論ベース）で補完可能。Stage A の改善優先度は低い。

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 60件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 2 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%

### 次の改善候補

- 実プロジェクトでの `/figma-prepare --enrich` 実運用テスト（トークン消費計測含む）
- characters フィールドを活用した TEXT コンテンツベースのリネーム精度向上
- 複数ページ横断での共通ヘッダー/フッター自動検出
- Stage A ネストグルーピング対応（Issue 23、Stage B で代替可能）

## 一覧

| Issue | Phase | 状態 | 概要 |
| ----- | ----- | ---- | ---- |
| 1-14 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 15 | 1.5 | **FIXED** | `get_design_context` 補完パイプライン — `enrich-metadata.sh` 新設 |
| 16 | 2 | **FIXED** | ヘッダー/フッターのセマンティック推論強化 — Priority 3.1 追加 |
| 17 | 2 | **FIXED** | fills ベースの IMAGE 判定 — Priority 2 で fills チェック |
| 18 | 4 | **FIXED** | layoutMode 補完による Phase 4 精度向上 — exact confidence |
| 19 | 3 | **FIXED** | Phase 3 を Claude 推論ベースに拡張（セクショニング対応）— Stage B 追加 |
| 20 | 2,3 | **FIXED** | Before/After 検証を構造 diff ベースに変更 — verify-structure.js 新設 |
| 21 | 2,3 | **FIXED** | Phase 2/3 の実行順序入れ替え（Phase 2=グルーピング、Phase 3=リネーム） |
| 22 | 2 | **PARTIAL** | Phase 2 グルーピング精度 — dedup修正 + テストケース3件追加 |
| 23 | 2 | **OPEN** | ネストされたグルーピングが Stage A で未対応（Stage B で補完可能） |
| 24 | 全体 | **FIXED** | 共通関数の Python ライブラリ化 — `lib/figma_utils.py` 新設 |
| 25 | 全体 | **FIXED** | `get_bbox` 返却キー名統一 — 共有 `get_bbox` に統合 + デッドコード除去 |
| 26 | 全体 | **FIXED** | ドキュメント Phase 番号不整合 + デッドコード除去 |
