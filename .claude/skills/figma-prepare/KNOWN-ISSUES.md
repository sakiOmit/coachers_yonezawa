# /figma-prepare 既知の課題

FIXED / CLOSED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

（現在オープンの課題なし — Issue 115-118 は修正済み）

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 86件
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 3 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture + INSTANCE/COMPONENT型対応）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%
- characters フィールド活用: enriched TEXT のリネーム精度向上
- figma_utils.py ユニットテスト: 全 public 関数カバー（18関数）

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
| 49 | 全体 | **FIXED** | `get_text_children_content` / `get_text_children_preview` コード重複 — `figma_utils.py` に統合 |
| 50 | テスト | **FIXED** | `figma_utils.py` の `yaml_str`, `get_bbox`, `get_root_node` テスト未カバー — ユニットテスト追加 |
| 51 | テスト | **FIXED** | `to_kebab` エッジケーステスト不足 — 空文字列、日本語、CamelCase、特殊文字等のテスト追加 |
| 52 | 全体 | **FIXED** | `snap()` 関数コード重複 — `infer-autolayout.sh` から `figma_utils.py` に抽出 |
| 53 | 全体 | **FIXED** | `is_section_root()` 関数コード重複 — `analyze-structure.sh` から `figma_utils.py` に抽出 |
| 54 | docs | **FIXED** | phase-details.md リネームロジック優先順テーブルに Sub-priority 未記載 — 3.1/3.2/3.5 追加 |
| 55 | テスト | **FIXED** | `is_unnamed()` ユニットテスト未カバー — 12パターン+6非マッチのテスト追加 |
| 56 | テスト | **FIXED** | `resolve_absolute_coords()` ユニットテスト未カバー — 座標累積・リーフ・bbox欠損のテスト追加 |
| 57 | テスト | **FIXED** | `to_kebab` タブ・改行文字のテスト未カバー — chr(9)/chr(10)/chr(13) のテスト追加 |
| 58 | テスト | **FIXED** | `enrich-metadata.sh` 空エンリッチメント JSON のエッジケーステスト未カバー — テスト追加 |
| 59 | テスト | **FIXED** | `prepare-sectioning-context.sh` 子要素なしルートのエッジケーステスト未カバー — テスト追加 |
| 60 | 全体 | **FIXED** | `absoluteBoundingBox: null` で `get_bbox`/`is_section_root`/`resolve_absolute_coords` がクラッシュ — `or {}` ガード追加 |
| 61 | 2 | **FIXED** | `detect-grouping-candidates.sh` の YAML 出力に `suggested_wrapper` が欠落 — 出力行追加 |
| 62 | 全体 | **FIXED** | `get_text_children_content(filter_unnamed=True)` が `characters` でなく `name` で判定するよう修正 |
| 63 | 4 | **FIXED** | `layout_from_enrichment()` が exact な Figma 値を `snap()` で丸めていた — `int()` に変更 |
| 64 | テスト | **FIXED** | `run-tests.sh`/`qa-check.sh` の `printf "$ERRORS"` がフォーマット文字列として解釈される — 安全な方式に修正 |
| 65 | テスト | **FIXED** | `qa-check.sh` の `check_unused_imports` にサブシェル問題によるデッドコードループ — 削除 |
| 66 | docs | **FIXED** | `phase-details.md` Phase 3 前提条件「ブランチ必須」が SKILL.md の Adjacent Artboard 方式と矛盾 — 修正 |
| 67 | 全体 | **FIXED** | `resolve_absolute_coords` の二重呼び出しで座標が破損する — `_abs_resolved` マーカーで防止 |
| 68 | docs | **FIXED** | KNOWN-ISSUES.md の public 関数カウント（11→9）修正 |
| 69 | 4 | **FIXED** | `infer-autolayout.sh` が INSTANCE/COMPONENT ノードの Auto Layout 推論をスキップ — 型チェック拡張 |
| 70 | 4 | **FIXED** | `layout_from_enrichment` の `source` が base metadata でも `'enriched'` と表示される — ロジック修正 |
| 71 | 1 | **FIXED** | `analyze-structure.sh` の `max_depth` が絶対深度で報告されるがスコアは相対深度を使用 — `max_section_depth` 追加 |
| 72 | 1 | **FIXED** | `analyze-structure.sh` が INSTANCE 型ノードをフラット/深ネスト指標に含めない — 型チェック拡張 |
| 73 | docs | **FIXED** | SKILL.md Usage/Input Parameters に `--enrich` フラグ未記載 — ドキュメント追加 |
| 74 | 4 | **FIXED** | Phase 4 YAML 出力に `source` フィールドが欠落 — 出力行追加 |
| 75 | 4 | **FIXED** | `source` ラベルが `'enriched'` だがベースメタデータ由来も含む — `'exact'` に統一 |
| 76 | docs | **FIXED** | `.claude/rules/figma-prepare.md` に `max_section_depth` 指標の説明が未記載 — ドキュメント追加 |
| 77 | 3 | **FIXED** | Priority 3.1 nav検出の子要素タイプに INSTANCE/COMPONENT が含まれない — 型チェック拡張 |
| 78 | 2 | **FIXED** | 近接グルーピングが距離のみ判定で誤検出 — スコアリング化（距離×整列×サイズ類似） |
| 79 | 2 | **FIXED** | パターン検出が完全一致ハッシュで微差を見逃す — Jaccard類似度0.7でファジーマッチ |
| 80 | 2 | **FIXED** | 等間隔配置の検出手法がない — `detect_regular_spacing` (CV < 0.25) 追加 |
| 81 | 2 | **FIXED** | Stage Aに構造的セマンティック検出器がない — Card/Nav/Grid検出器追加（fills非依存） |
| 82 | 4 | **FIXED** | 2要素のAuto Layout方向判定が不安定 — `infer_direction_two_elements`（dx vs dy直接比較） |
| 83 | 4 | **FIXED** | WRAP/SPACE_BETWEEN/END未対応 — `detect_wrap`, `detect_space_between`, END alignment追加 |
| 84 | 4 | **FIXED** | 信頼度がchild数のみで判定 — gap CoVベース（< 0.15: high, 0.15-0.35: medium, >= 0.35: low） |
| 85 | 2 | **FIXED** | トップレベルのヘッダー/フッター構成要素が未グルーピング — `detect_header_footer_groups` をルートレベル限定で追加。ページ上端120px以内のナビTEXT+ロゴ/アイコン要素、下端300px以内の要素を検出。既に HEADER/FOOTER 名を持つ要素はスキップ |
| 86 | 2 | **FIXED** | 異種type要素の「セクション」グルーピング未対応 — `detect_vertical_zone_groups` をルートレベル限定で追加。Y座標範囲の重なり（50%以上）による垂直ゾーンマージで、異なるtypeの要素をセクション単位にグルーピング。method='zone'（priority=3、semantic=4とpattern=2の間） |
| 87 | 2 | **FIXED** | リーフノードのpattern誤検出 — children=[]のノード（TEXT等）が位置的に離れていても同一ハッシュで1グループになる。`_split_by_spatial_gap`で空間ギャップによるサブグルーピングを追加 |
| 88 | 2 | **CLOSED** | 大規模patternグループのサブグルーピング — 調査の結果、12枚カードのグリッド(3行×4列、行間30px)は1グループ維持が正しい（目標ページでも1セクション内に包含）。上位セクション分割はStage Bに委譲。`_split_by_spatial_gap`にグリッド検出(row_tolerance=20)を追加し大ギャップのみ分割するよう改善 |
| 89 | 1 | **FIXED** | Phase 1スコアリングがトップレベル子要素数を十分にペナライズしない — `flat_excess`指標追加（超過子要素数×0.5）。flat_penaltyを`flat_sections×5 + flat_excess×0.5`に変更、上限を-20→-30に拡大。フラット構造(40要素)のスコアが56.5→44.0に低下し構造化(3要素)60.9との差が拡大 |
| 90 | 全体 | **FIXED** | Phase 2-4の `--apply` 機能 — `apply-grouping.js`（ラッパーFrame作成+子要素移動）、`apply-autolayout.js`（layoutMode/gap/padding設定）新設。Phase 3の `apply-renames.js` は既存。全スクリプトがバッチ50件/回、ID存在チェック、エラーperノードスキップに対応 |
| 91 | 2 | **FIXED** | Zone検出のセマンティック命名 — `infer_zone_semantic_name` で子構造分析（hero/cards/grid/nav/content）。カウンタ付きサフィックス（cards-1, content-2等）で一意性保証。テスト追加（86件） |
| 92 | 2 | **FIXED** | `apply-grouping.js` の適用後検証スクリプト `verify-grouping.js` 新設 — ラッパーFRAME存在・名前一致、子要素移動確認、bbox整合性（±2px許容）の3項目を検証 |
| 93 | docs | **FIXED** | SKILL.md Phase 2/4 `--apply` セクションに `apply-grouping.js` / `apply-autolayout.js` のスクリプト名・手順を追記 |
| 94 | 4 | **FIXED** | `apply-autolayout.js` の適用後検証スクリプト `verify-autolayout.js` 新設 — layoutMode/layoutWrap、itemSpacing（±1px）、padding 4辺（±1px）、primaryAxisAlignItems、counterAxisAlignItems を検証。SKILL.md Phase 4-3、figma-plugin-api.md にドキュメント追加 |
| 95 | テスト | **FIXED** | `run-tests.sh` インライン Python 内のシェル変数インジェクション — `'${SCRIPT_DIR}'`/`'${SKILLS_DIR}'` を `os.environ[]` 経由に変更。`export SCRIPT_DIR SKILLS_DIR` 追加 |
| 96 | テスト | **FIXED** | `qa-check.sh` 関数外での `local` 宣言 — `--json` モードの `local tmp_issues tmp_warnings` を削除。`set -euo pipefail` 環境でのエラー回避 |
| 97 | docs | **FIXED** | `phase-details.md` フラット構造ペナルティ上限値が古い（-20→-30）— Issue 89 の `flat_excess` 追加を反映 |
| 98 | 4 | **FIXED** | `infer-autolayout.sh` の `source` 変数が未初期化 — `source = None` で先行初期化追加 |
| 99 | 2 | **FIXED** | `apply-grouping.js` のデッドソート比較関数（常に 0 を返す `.sort()`）— 不要な `.sort()` 呼び出しを削除 |
| 100 | 全体 | **FIXED** | `figma_utils.py` の関数内ラジーインポート（PEP 8 違反）— `Counter`, `statistics` をファイル先頭に移動 |
| 101 | 全体 | **FIXED** | `detect_regular_spacing()` の未使用パラメータ `tolerance` — パラメータ削除、CV_THRESHOLD 定数に統一 |
| 102 | テスト | **FIXED** | `qa-check.sh` dead-code チェックが `figma_utils.py` 内部使用関数を誤検出 — `alignment_bonus`, `size_similarity_bonus`, `_raw_distance` は `compute_grouping_score()` 内部で使用。チェッカーに内部使用判定（def行+呼び出し行で出現数>1）を追加 |
| 103 | docs | **FIXED** | `phase-details.md` Stage A 検出メソッドテーブルが陳腐化 — `semantic` の優先度が 3→4 に修正、`zone` メソッド（優先度 3）を追加 |
| 104 | 4 | **FIXED** | `infer_layout()` が counter_axis_align に 'END' を返すが Figma Plugin API は 'MAX' のみ受付 — verify-autolayout.js で検証失敗の原因。'END' → 'MAX' に修正、phase-details.md のドキュメントも更新 |
| 105 | 1 | **FIXED** | `analyze-structure.sh` の `score_breakdown.flat_penalty` が未丸め — `unnamed_penalty` は `round(..., 1)` だが `flat_penalty` は未丸め。一貫性のため `round(..., 1)` を追加 |
| 106 | docs | **FIXED** | `phase-details.md` line 139 が「セマンティック検出は Stage A から削除済み（Issue 29/30）」と記載しているが、Issue 81 で fills 非依存の構造ベースセマンティック検出として再追加済み。同一ファイル内の検出メソッドテーブル（lines 235-241）と直接矛盾。注意文を更新 |
| 107 | docs | **FIXED** | Phase 2 Stage A のメソッド一覧が不完全 — `phase-details.md` line 230 に "zone" 欠落、`SKILL.md` lines 351/369 が "proximity + pattern のみ" と記載。Issue 78-86 で追加された5手法（proximity + pattern + spacing + semantic + zone）に更新 |
| 108 | テスト | **FIXED** | `qa-check.sh` `doc-staleness` チェックが Stage A 検出メソッドの矛盾を検出できない — 「削除済み」記述の検出と SKILL.md のメソッド一覧不完全性チェックを追加 |
| 109 | 2 | **FIXED** | `apply-grouping.js` の `absoluteTransform` null チェック欠落 — 子ノードの bbox 計算（line 104）と位置変換（lines 149-152）で `absoluteTransform` に null ガード追加。親ノードは既にガード済み（lines 129-130）だが子ノードは未対応だった |
| 110 | 2 | **FIXED** | `apply-grouping.js` デッドコード `origX`/`origY` — `childOrder` の map で取得・destructure されるが未使用。map を削除し直接 `childNodes` をイテレート |
| 111 | テスト | **FIXED** | `run-tests.sh` 4px スナップテストが `exact` source フレームをスキップしない — enriched フレームは Figma 実値を保持（Issue 63）するため 4px 刻みでない場合がある。`source == 'exact'` のフレームをスキップするよう修正 |
| 112 | テスト | **FIXED** | `run-tests.sh` `assert_json_range`/`assert_json_gte`/cross-script テストのシェル変数 Python インジェクション — Issue 64/95 と同様の問題。`$actual`/`$min`/`$max` を `sys.argv` 経由に変更 |
| 113 | テスト | **FIXED** | `run-tests.sh` コメント「Phase 2 renames」が「Phase 3 renames」の誤り — テストメッセージ（line 497/501）は正しいがコメント（line 499）が古い Phase 番号のまま |
| 114 | docs | **FIXED** | `phase-details.md` 出力例の3箇所不整合 — (a) YAML に `max_section_depth` 欠落（Issue 71 追加分）、(b) コンソール ungrouped_penalty が -10.0 だが 5 候補 × 1 = -5.0 が正、(c) score 65 が実際のペナルティ合計 39.9 と不一致（60 に修正） |
| 115 | 4 | **FIXED** | `infer-autolayout.sh` YAML出力に `primary_axis_align` が欠落 — `apply-autolayout.js` が常に `MIN` をデフォルト適用してしまう。YAML書き出しループに `primary_axis_align` 行を追加 |
| 116 | 1 | **FIXED** | `is_section_root()` が FRAME 型のみ判定 — COMPONENT/INSTANCE/SECTION 型のセクションルートで `section_depth` がリセットされず深さスコアが不正に加算される。型チェックを拡張 |
| 117 | 2 | **FIXED** | `apply-grouping.js` 出力に `total` フィールドが欠落 — `apply-renames.js` と `apply-autolayout.js` は `total` を含むが `apply-grouping.js` のみ欠落。`total: groupingPlan.length` を追加 |
| 118 | 4 | **FIXED** | `infer-autolayout.sh` YAML出力のキー名 `counter_align` が `counter_axis_align` と不一致 — データ構造と `apply-autolayout.js` は `counter_axis_align` を期待。YAMLキーを `counter_axis_align` に統一 |
