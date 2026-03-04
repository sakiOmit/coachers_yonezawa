# /figma-prepare 既知の課題

FIXED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 23: ネストされたグルーピングが Stage A で未対応

- **Phase**: 2
- **優先度**: 低
- **概要**: Issue 22 の期待構造では、ヒーロー領域内に「画像 + 見出しフレーム」のネストされた
  グループが存在するが、Stage A の proximity/pattern/page-kv 検出は単一階層のみ動作する。
  Issue 22 の残課題（位置ベースのセマンティック検出）も含む。
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

### Issue 31: Stage A 簡素化による Stage B 依存度増加 — **FIXED**

- **Phase**: 2
- **優先度**: 低
- **概要**: Stage A から `detect_semantic_groups()` と `detect_page_kv_groups()` を削除し、
  proximity + pattern のみに簡素化した。セマンティック理解は Stage B（Claude 推論）に委ねる設計。
  Stage B（Claude 推論）が利用不可の場合（スクリーンショット取得失敗等）、page-kv/semantic
  検出なしになる。
- **リスク**: Stage B フォールバック時は proximity + pattern のみで進行（簡素化前の Stage A
  から page-kv/semantic を除いた状態と同等）。
- **対応方針**: Stage B フォールバック時はユーザーに警告を表示し、手動セクショニングを推奨。
  現状は Stage B の可用性が高いため実害は低い。
- **解決**: SKILL.md に Stage B フォールバック時の明示的な警告テンプレートを追加。
  Error Handling テーブルにも「Stage B スクリーンショット失敗」行を追加。

### Issue 32: generate-rename-map.sh Priority 4 fills=[] IndexError — **FIXED**

- **Phase**: 3
- **優先度**: 中
- **概要**: Priority 4 の `has_image` 判定で `c.get('fills', [{}])[0].get('type')` を使用。
  enriched metadata で `fills: []`（空配列）の場合、`[][0]` が `IndexError` を引き起こす。
- **再現条件**: RECTANGLE ノードが enriched metadata 経由で `"fills": []` を持つ場合、
  そのノードの親が unnamed FRAME/GROUP であると Priority 4 到達時にクラッシュ。
- **解決**: `c.get('fills')` の存在 + 非空チェックを先行させ、安全に `any()` で判定。
  テスト2件追加（enrichment pipeline 内 + 独立 unit test）。

### Issue 33: phase-details.md のドキュメント陳腐化 — **FIXED**

- **Phase**: ドキュメント
- **優先度**: 低
- **概要**: Issue 29/30 で Stage A から semantic/page-kv 検出が削除されたが、
  phase-details.md の以下セクションが更新されていなかった:
  1. Phase 1 ペナルティ重み表（ungrouped: -2→-1, cap: -20→-10, autolayout: 除外）
  2. Stage A セマンティック検出テーブル
  3. heuristic_hints 出力例（page_kv_candidates → gap_analysis + background_candidates）
  4. ヒューリスティックヒント定義表
  5. 結果統合セクションの page-kv 参照
- **解決**: 全5箇所を実コードと一致するよう修正。

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 65件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 3 フォールバック率 0%（realistic fixture）
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
| 22 | 2 | **FIXED** | Phase 2 グルーピング精度 — dedup修正 + テストケース3件追加 |
| 23 | 2 | **OPEN** | ネストされたグルーピングが Stage A で未対応（Stage B で補完可能） |
| 24 | 全体 | **FIXED** | 共通関数の Python ライブラリ化 — `lib/figma_utils.py` 新設 |
| 25 | 全体 | **FIXED** | `get_bbox` 返却キー名統一 — 共有 `get_bbox` に統合 + デッドコード除去 |
| 26 | 全体 | **FIXED** | ドキュメント Phase 番号不整合 + デッドコード除去 |
| 27 | 全体 | **FIXED** | YAML出力の特殊文字エスケープ — `yaml_str()` ヘルパー導入 |
| 28 | 全体 | **FIXED** | テストメッセージ Phase 番号不整合 + 変数名修正 |
| 29 | 2 | **FIXED** | page-kv 検出ロジックの二重定義 → 設計変更: page-kv 検出器自体を削除 |
| 30 | 2 | **FIXED** | `detect_semantic_groups` が enriched fills を考慮しない → 設計変更: semantic 検出器自体を削除 |
| 31 | 2 | **FIXED** | Stage A 簡素化による Stage B 依存度増加 — フォールバック警告追加 |
| 32 | 3 | **FIXED** | Priority 4 fills=[] IndexError — 安全な fills チェックに修正 |
| 33 | docs | **FIXED** | phase-details.md のドキュメント陳腐化 — 5箇所修正 |
