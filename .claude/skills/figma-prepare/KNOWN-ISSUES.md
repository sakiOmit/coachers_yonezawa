# /figma-prepare 既知の課題

FIXED / CLOSED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

なし。

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 68件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 3 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture + INSTANCE/COMPONENT型対応）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%
- characters フィールド活用: enriched TEXT のリネーム精度向上

### 次の改善候補

- 実プロジェクトでの `/figma-prepare --enrich` 実運用テスト（トークン消費計測含む）
- 複数ページ横断での共通ヘッダー/フッター自動検出

## 一覧

| Issue | Phase | 状態 | 概要 |
| ----- | ----- | ---- | ---- |
| 1-14 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 15 | 1.5 | **FIXED** | `get_design_context` 補完パイプライン — `enrich-metadata.sh` 新設 |
| 16 | 2 | **FIXED** | ヘッダー/フッターのセマンティック推論強化 — Priority 3.1 追加 |
| 17 | 2 | **FIXED** | fills ベースの IMAGE 判定 — Priority 2 で fills チェック |
| 18 | 4 | **FIXED** | layoutMode 補完による Phase 4 精度向上 — exact confidence |
| 19 | 2 | **FIXED** | Phase 2 Stage B を Claude 推論ベースに拡張（セクショニング対応）— Stage B 追加 |
| 20 | 2,3 | **FIXED** | Before/After 検証を構造 diff ベースに変更 — verify-structure.js 新設 |
| 21 | 2,3 | **FIXED** | Phase 2/3 の実行順序入れ替え（Phase 2=グルーピング、Phase 3=リネーム） |
| 22 | 2 | **FIXED** | Phase 2 グルーピング精度 — dedup修正 + テストケース3件追加 |
| 23 | 2 | **CLOSED** | ネストグルーピング — 設計上 Stage B に委譲（Won't Fix） |
| 24 | 全体 | **FIXED** | 共通関数の Python ライブラリ化 — `lib/figma_utils.py` 新設 |
| 25 | 全体 | **FIXED** | `get_bbox` 返却キー名統一 — 共有 `get_bbox` に統合 + デッドコード除去 |
| 26 | 全体 | **FIXED** | ドキュメント Phase 番号不整合 + デッドコード除去 |
| 27 | 全体 | **FIXED** | YAML出力の特殊文字エスケープ — `yaml_str()` ヘルパー導入 |
| 28 | 全体 | **FIXED** | テストメッセージ Phase 番号不整合 + シェル変数インジェクション修正 |
| 29 | 2 | **FIXED** | page-kv 検出ロジックの二重定義 → 設計変更: page-kv 検出器自体を削除 |
| 30 | 2 | **FIXED** | `detect_semantic_groups` が enriched fills を考慮しない → 設計変更: semantic 検出器自体を削除 |
| 31 | 2 | **FIXED** | Stage A 簡素化による Stage B 依存度増加 — フォールバック警告追加 |
| 32 | 3 | **FIXED** | Priority 4 fills=[] IndexError — 安全な fills チェックに修正 |
| 33 | docs | **FIXED** | phase-details.md のドキュメント陳腐化 — 5箇所修正 |
| 34 | 全体 | **FIXED** | `SCRIPT_DIR` シェル変数インジェクション — `sys.argv` 経由に変更 |
| 35 | 3 | **FIXED** | `infer_name()` 内の `text_contents` 二重計算 — 単一ブロックに統合 |
| 36 | docs | **FIXED** | phase-details.md の `autolayout_penalty` 出力例が非ゼロ — 0 に修正 |
| 37 | 2,3 | **FIXED** | INSTANCE/COMPONENT/SECTION 型のヘッダー/フッター検出漏れ — 型チェック拡張 |
| 38 | 3 | **FIXED** | characters フィールド活用でリネーム精度向上 — enriched TEXT 優先 |
| 39 | 3 | **FIXED** | Priority 3 デッドコード文書化 — PAGE/CANVAS 限定の到達条件をコメント明記 |
| 40 | 1 | **FIXED** | Phase 1 スコアリングの detect_grouping_candidates 不一致を文書化 |
| 41 | 2 | **FIXED** | YAML出力の `'pattern'` キー誤り → `'structure_hash'` に修正 |
| 42 | docs | **FIXED** | sectioning-prompt-template.md の Phase 番号誤り（Phase 3 → Phase 2） |
| 43 | docs | **FIXED** | phase-details.md 信頼度テーブル更新 — `exact` 追加、`low` 削除 |
| 44 | 2,3 | **FIXED** | 未使用 import 削除 — `unicodedata`(Phase 3), `re`(Phase 2) |
| 45 | 全体 | **FIXED** | `to_kebab` + `JP_KEYWORD_MAP` コード重複 — `figma_utils.py` に統合 |
| 46 | docs | **CLOSED** | confidence 定義の不一致 — 調査の結果 phase-details.md は正しく更新済み（Not an Issue） |
| 47 | 3 | **FIXED** | `to_kebab` CamelCase 分割未実装 — `re.sub` で分割ロジック追加 |
| 48 | 全体 | **FIXED** | 深いネスト Figma ファイルで再帰制限クラッシュ — `sys.setrecursionlimit(3000)` 追加 |
