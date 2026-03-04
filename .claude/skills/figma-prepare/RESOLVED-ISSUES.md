# /figma-prepare 解決済みの課題

KNOWN-ISSUES.md から移動した FIXED Issue のアーカイブ。

## Issue 1: deep_nesting の過剰検出 — FIXED

- **現象**: 673ノードが「深すぎるネスト」判定（実際はほとんどが正常な構造）
- **原因**: `analyze-structure.sh` がROOTノードからの絶対深度で計算していた
- **修正内容**: セクションルート（width≈1440のフレーム）からの相対深度で計算するよう変更
- **修正日**: 2026-03-04

## Issue 2: AutoLayout未適用の誤判定 — FIXED (workaround)

- **現象**: 全フレームが「AutoLayout未適用」判定（実際は適用済みフレームもある）
- **原因**: `get_metadata` のXML出力に `layoutMode` 属性が含まれない
- **修正内容**: Auto Layout指標をスコア計算から除外（計測不能として`autolayout_penalty: 0`固定）。メトリクスとしては残すが参考値扱い
- **修正日**: 2026-03-04
- **将来対応**: `get_design_context` でセクション単位に取得し、layoutModeを補完する案あり（トークン消費とのトレードオフ）

## Issue 4: 小文字 `image` が未命名検出されない — FIXED

- **Phase**: 1
- **現象**: Figma自動生成の `image 1254`, `image 1347` が未命名パターンに引っかからない
- **原因**: 正規表現が `Image`（大文字I）のみマッチ。Figmaは小文字 `image` で自動命名する場合がある
- **修正内容**: `UNNAMED_RE` に `re.IGNORECASE` フラグを追加。大文字小文字を問わず検出
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`, `scripts/generate-rename-map.sh`

## Issue 5: deep_nesting がノード単位で膨張 — FIXED

- **Phase**: 1
- **現象**: お知らせ記事 (1-306) で deep_nesting=90 / total=130 (69%)。記事コンテンツ（リスト・テーブル）の末端ノードが全てカウントされる
- **原因**: 深いパスが1本でも、そこに含まれる全ての子孫ノードがカウントされる
- **修正内容**: コンテナノード（FRAME/GROUP/COMPONENT/SECTION）のみをカウント対象に変更。TEXT/RECTANGLE等の末端ノードは除外
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`

## Issue 7: グルーピング候補が多すぎる — FIXED

- **Phase**: 3
- **現象**: 全デザインで候補数がノード数の30%超（1-306: 44/130, 1-4: 34/106, 1-125: 48/141）
- **原因**: proximity (24px) + pattern + semantic の3アルゴリズムが独立に検出するため重複が多い。既にグループ化済みの要素も候補になる
- **修正内容**: `deduplicate_candidates()` 関数を追加。pattern/proximity 重複時は pattern を優先。セマンティック名付き親の proximity 候補を除去
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`
- **効果**: フィクスチャテストで候補が 9 → 6 に削減（33%減）

## Issue 8: XML→JSON 座標変換バグ — FIXED

- **Phase**: 3, 4
- **現象**: Phase 4 のパディング計算が `pad=[0,2220,2752,0]` 等の異常値を出力
- **原因**: `get_metadata` XML の座標値は**親相対座標**だが、スクリプトは `absoluteBoundingBox`（**絶対座標**）を期待。XML→JSON 変換時に座標系変換をしていない
- **修正内容**: 全4スクリプトに `resolve_absolute_coords()` 関数を追加。データロード後に親オフセットを累積加算して絶対座標に変換。テストフィクスチャも親相対座標形式に統一
- **修正日**: 2026-03-04
- **ファイル**: 全4スクリプト (`analyze-structure.sh`, `generate-rename-map.sh`, `detect-grouping-candidates.sh`, `infer-autolayout.sh`)

## Issue 9: Phase 3 の二重検出 — FIXED

- **Phase**: 3
- **現象**: Job Cards が proximity グループと pattern グループの両方で検出される。同じ要素が2つの候補に含まれる
- **原因**: proximity, pattern, semantic の各検出が独立実行される
- **修正内容**: Issue 7 と統合対応。`deduplicate_candidates()` で pattern 優先の重複除去を実装
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`

## Issue 10: Phase 4 Gap推論は正確だがPadding不正確 — FIXED

- **Phase**: 4
- **現象**: Gap推論は正確（Job Cards gap=24px, Tabs gap=0 等）。しかしPadding値は不正確（Issue 8 の座標バグに起因）
- **修正内容**: Issue 8 の `resolve_absolute_coords()` 適用により自動的に解消
- **修正日**: 2026-03-04
- **ファイル**: `scripts/infer-autolayout.sh`

## Issue 3: リネーム推論の精度不足 — FIXED

- **Phase**: 2
- **現象**: `group-6`, `frame-0` 等のフォールバック名が多い（大半がPriority 4-5）。Priority 1（テキスト内容ベース推論）が全く効かない
- **原因**: `node.get('characters', '')` は常に空文字（`get_metadata` に `characters` フィールドがない）。しかし TEXT ノードは `name` フィールドにテキスト内容を保持している
- **修正内容**:
  1. Priority 1: TEXT ノードの `name` をテキスト内容として使用（`characters` → `name`）
  2. `to_kebab()` に `JP_KEYWORD_MAP` 追加（日本語テキスト → 英語slug変換）
  3. `get_text_children_content()` ヘルパー追加（子TEXTノードの名前を収集）
  4. Priority 3.2: 小さい空フレーム（48x48以下）→ `icon-*`
  5. Priority 3.5: ナビゲーション検出（4+短テキスト子 → `nav-*`）
  6. Priority 4: ボタン/アイコン/見出し検出を分化（`text-block` catch-all を改善）
  7. `infer_text_role()` にボタンキーワード追加（`見る`, `戻る`, `詳細` 等）
- **効果**: 実データ3件でフォールバック率 95% → 20-38%（目標50%以下を達成）
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/run-tests.sh`（5テスト追加）

## Issue 6: タブ/ボタンが text-block にリネームされる — FIXED

- **Phase**: 2
- **現象**: お知らせ一覧のタブ (Frame 94-98) → `text-block-0~4`。1テキスト子を持つフレームがすべて `text-block-*` に分類
- **原因**: Priority 4 の `text-block` catch-all がサイズや文脈を考慮せずに適用されていた
- **修正内容**: Issue 3 と統合対応。サイズヒューリスティック（h≤70 & w<300 & children≤2 → `btn-*`）を追加。TEXT子の名前からスラグ生成
- **効果**: Frame 94-98 → `btn-all`, `btn-news`, `btn-event`, `btn-category`
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`

## Issue 11: テストフィクスチャが実データの特徴を反映していない — FIXED

- **Phase**: 全フェーズ
- **修正内容**: 募集一覧 (1-4) から67ノードのサブセットを `fixture-realistic.json` として追加。`run-tests.sh` に9テスト追加。キャリブレーションにもケース追加
- **修正日**: 2026-03-04
- **ファイル**: `tests/fixture-realistic.json`, `tests/run-tests.sh`, `.claude/data/figma-prepare-calibration.yaml`

## Issue 12: `to_kebab()` の日本語部分マッチが誤ヒットする — FIXED

- **Phase**: 2
- **現象**: `"大規模イベントに強いオペレーション力"` → `"イベント"` が部分マッチ → `heading-event` を返す
- **原因**: `JP_KEYWORD_MAP` は `if jp in text` で部分一致検索しており、長文テキストの一部にキーワードが含まれると誤マッチ
- **修正内容**: `to_kebab()` にキーワード長/テキスト長の比率チェックを追加。比率 0.5 未満（キーワードがテキストの半分未満）の場合はスキップ
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/run-tests.sh`（unit test追加）

## Issue 13: JP_KEYWORD_MAP 未登録の日本語がそのまま出力される — FIXED

- **Phase**: 2
- **現象**: `"無料相談"` → `btn-無料相談`。kebab-case名に日本語が混入
- **原因**: `\w` が Unicode 文字（日本語含む）にマッチし、ASCII ロジックで除去されない
- **修正内容**: `to_kebab()` の ASCII ロジック前に `re.sub(r'[^\x00-\x7f]', ' ', text)` で非ASCII文字を除去するステップを追加
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/run-tests.sh`（unit test追加）

## Issue 14: heading vs body テキストの誤判定 — FIXED

- **Phase**: 2
- **現象**: 見出し＋本文テキストのフレーム（2 TEXT子）が `heading-*` に分類される
- **原因**: Priority 4 の heading 判定が TEXT 子の長さを考慮しない
- **修正内容**: TEXT 子の最長文字数をチェック。50文字超の TEXT 子がある場合は `content-*` に分類
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/fixture-realistic.json`（テストフレーム追加）, `tests/run-tests.sh`（fixture test追加）

## テスト履歴

### テストフィクスチャ対応 — 2026-03-04

- `fixture-metadata.json`: `layoutMode`, `characters`, `fills` を削除し、実API形式に統一
- `fixture-dirty.json`: 未命名レイヤー大量の汚いファイルを追加
- 座標を親相対座標に変換（実APIと統一）
- テストは全24件パス（Issue 3+6 修正後37件）

### 3デザイン追加テスト — 2026-03-04

テスト対象:
- お知らせ記事 (1:306) — 130ノード、記事コンテンツ（リスト・テーブル・引用）
- 募集一覧 (1:4) — 106ノード、タブ+カードリスト
- お知らせ一覧 (1:125) — 141ノード、カードグリッド+ページネーション

### 初回キャリブレーション — 2026-03-04

| ID | Expected | Actual | Score (range) | Status |
|----|----------|--------|---------------|--------|
| fixture-metadata | B | B | 68.0 (60-80) | PASS |
| fixture-dirty | N/A | B | 67.0 (50-80) | PASS |
| real-dirty | D | D | 25.0 (15-35) | PASS |
| real-clean | B | B | 61.8 (55-70) | PASS |

**ペナルティ寄与率**: unnamed 66%, ungrouped 14%, flat 11%, nesting 8%

## 根本原因（参考）

`get_metadata` が返すXMLには以下の情報**しか含まれない**:
- id, name, type, x, y, width, height

以下は**含まれない**:
- `layoutMode` (AutoLayout設定)
- `characters` (テキスト内容) — ただしTEXTノードの `name` がテキスト内容を保持（Issue 3 で発見）
- `fills` (塗り)
- `strokes`, `effects`, `constraints` 等

座標値は**親相対座標**（Issue 8 の `resolve_absolute_coords()` で対処済み）。

## Issue 15: `get_design_context` 補完パイプライン — FIXED

- **Phase**: 新規 Phase 1.5
- **現象**: `get_metadata` のみでは fills, layoutMode, characters が取得できず、リネーム・AutoLayout精度に限界
- **修正内容**: `enrich-metadata.sh` スクリプトを新設。`get_design_context` から抽出した fills/layoutMode/characters をフラットマップ形式で受け取り、metadata ツリーにマージ
- **修正日**: 2026-03-04
- **ファイル**: `scripts/enrich-metadata.sh` (新規), `tests/fixture-enrichment.json` (新規)
- **テスト**: 7ノード×複数プロパティのマージを検証（46件中1件）

## Issue 16: ヘッダー/フッターのセマンティック推論強化 — FIXED

- **Phase**: 2
- **現象**: `Group 46165`（ヘッダー: ロゴ + ナビ10リンク）が `group-7` にフォールバック
- **原因**: Priority 3 が PAGE/CANVAS 直子のみ対応。セクションルート子の GROUP/FRAME は未対応
- **修正内容**: Priority 3.1 を追加。位置 + 幅 + 子構造ヒューリスティックで header/footer を検出:
  - Header: relative_y < 100 + 幅 > 70% + ナビ子（4+ TEXT孫）→ `header`
  - Footer: ページ下部 + コンパクト + テキスト主体 → `footer`
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/fixture-realistic.json` (footer追加)
- **テスト**: `Group 46165` → `header`, `Group 50001` → `footer` を検証（46件中2件）

## Issue 17: fills ベースの IMAGE 判定 — FIXED

- **Phase**: 2
- **現象**: `RECTANGLE` に IMAGE fill がある要素が `bg-*` にリネーム（`img-*` が適切）
- **修正内容**: Priority 2 (Shape analysis) で enriched metadata の fills をチェック。`fills[].type === 'IMAGE'` なら `img-*` プレフィックスを使用
- **依存**: Issue 15 (enrich-metadata.sh)
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`
- **テスト**: `image 1347` → `img-3`, `image 1254` → `img-2`, SOLID fill は `bg-0` 維持（46件中3件）

## Issue 18: layoutMode 補完による Phase 4 精度向上 — FIXED

- **Phase**: 4
- **現象**: Auto Layout の方向・gap・padding が全て座標推論に依存（medium confidence）
- **修正内容**: `infer-autolayout.sh` に `layout_from_enrichment()` を追加。enriched metadata に layoutMode がある場合は推論をスキップし、実値を使用（exact confidence）
- **依存**: Issue 15 (enrich-metadata.sh)
- **修正日**: 2026-03-04
- **ファイル**: `scripts/infer-autolayout.sh`
- **テスト**: 2フレームが exact confidence で出力されることを検証（46件中1件）

## Issue 20: Before/After 検証を構造 diff ベースに変更 — FIXED

- **Phase**: 2, 3
- **現象**: Phase 2 Step 2-3e のスクショ比較は、リネーム/グルーピングでビジュアルが変わらないため差分が見えない
- **修正内容**:
  - `verify-structure.js` を新設。クローンアートボードの DFS 走査で期待名と actual name を比較
  - SKILL.md Phase 2 Step 2-3e を「構造 diff 検証（primary）+ 補助スクリーンショット（secondary）」に変更
  - Phase 3 --apply 後にもツリー読み戻し検証を追加
  - `references/figma-plugin-api.md` に構造検証パターンを追加
- **修正日**: 2026-03-04
- **ファイル**: `scripts/verify-structure.js` (新規), `SKILL.md`, `references/figma-plugin-api.md`, `KNOWN-ISSUES.md`

## Issue 21: Phase 2（リネーム）と Phase 3（グルーピング）の実行順序を入れ替える — FIXED

- **Phase**: 2, 3
- **優先度**: 高
- **概要**: グルーピングを先に行い、確定した構造に対してリネームする順序に変更
- **修正内容**:
  - Phase 番号を振り直し: Phase 2 = グルーピング + セクショニング、Phase 3 = セマンティックリネーム
  - SKILL.md: フロー図、Phase 2/3 セクション全体を入れ替え、ステップ番号を更新
  - references/phase-details.md: Phase 2/3 セクション入れ替え、依存関係セクション更新
  - references/figma-plugin-api.md: Phase 番号参照を更新
  - scripts/: 4スクリプトのコメントヘッダーとYAML出力のPhase番号を更新
  - tests/run-tests.sh: Phase ラベル更新（Phase 3 = rename, Phase 2 = grouping）
  - analyze-structure.sh: recommendation メッセージを更新
- **修正日**: 2026-03-04
- **テスト**: 全57件パス（回帰なし）

## Issue 24: 共通関数の Python ライブラリ化 — FIXED

- **Phase**: 全体
- **優先度**: 低
- **概要**: `resolve_absolute_coords`, `get_bbox`, `UNNAMED_RE`, `get_root_node` が
  最大6スクリプトに重複定義されていた。共通 Python ライブラリに切り出し。
- **修正内容**:
  - `lib/figma_utils.py` を新設。以下の共通関数を定義:
    - `resolve_absolute_coords(node, parent_x, parent_y)` — 5スクリプトから統合
    - `get_bbox(node)` → `{x, y, w, h}` — 2スクリプトから統合
    - `get_root_node(data)` — 6スクリプトから統合
    - `UNNAMED_RE` — 4スクリプトから統合
    - `is_unnamed(name)` — 便利ラッパー
  - 6スクリプトを更新: `SCRIPT_DIR` + `sys.path.insert` でインポート
  - `prepare-sectioning-context.sh` のローカル `get_bbox` は Issue 25 で共有版に統合済み
- **修正日**: 2026-03-04
- **ファイル**: `lib/figma_utils.py` (新規), 全6スクリプト更新
- **テスト**: 全60件パス（回帰なし）
- **削減効果**: 約85行の重複コードを解消

## Issue 25: `get_bbox` 返却キー名統一 — FIXED

- **Phase**: 全体
- **優先度**: 低
- **概要**: `prepare-sectioning-context.sh` のみローカル `get_bbox` を使用し `{x, y, width, height}`
  キーを返していた。共有 `get_bbox` は `{x, y, w, h}` を返すため不整合。
- **修正内容**:
  - `prepare-sectioning-context.sh` のローカル `get_bbox` を削除し、共有版を使用
  - 内部参照を `bb['width']`→`bb['w']`, `bb['height']`→`bb['h']` に更新
  - 出力 JSON の `page_size` は意味的フィールドとして `width`/`height` を維持（bbox形式と異なる）
  - Issue 24 の RESOLVED-ISSUES エントリの「prepare-sectioning-context.sh のみローカル定義を残す」記述を更新
- **修正日**: 2026-03-04
- **ファイル**: `scripts/prepare-sectioning-context.sh`
- **テスト**: 全60件パス（回帰なし）

## Issue 26: ドキュメント Phase 番号不整合 + デッドコード除去 — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: Issue 21 で Phase 2/3 の実行順序を入れ替えた際、一部ドキュメントの更新が漏れていた。
  また `prepare-sectioning-context.sh` に未使用コード・インポートが残存していた。
- **修正内容**:
  - `.claude/rules/figma-prepare.md`: グレード判定表の Phase 2/3 説明を修正
    - `Phase 2（リネーム）` → `Phase 2（グループ化）`
    - `Phase 2 + 3（リネーム + グループ化）` → `Phase 2 + 3（グループ化 + リネーム）`
  - `references/phase-details.md` line 150: クロスリファレンスを修正
    - `「Phase 3: グループ化」` → `「Phase 2: グループ化」`
  - `SKILL.md` Related Files: `lib/figma_utils.py` を追加
  - `prepare-sectioning-context.sh`: 未使用 `re` インポート削除、デッド関数 `collect_all_text()` 削除、
    `Counter` インポートを関数内からモジュール先頭に移動
- **修正日**: 2026-03-04
- **ファイル**: `.claude/rules/figma-prepare.md`, `references/phase-details.md`, `SKILL.md`,
  `scripts/prepare-sectioning-context.sh`
- **テスト**: 全60件パス（回帰なし）

## Issue 22: Phase 2 グルーピング精度 — FIXED

- **Phase**: 2
- **優先度**: 高
- **概要**: 募集一覧ページ (1:4) のフラットな9子要素が、関連要素ごとに適切にグルーピングされるべきだが、Stage A ヒューリスティックに不具合があった。
- **修正内容** (Stage A dedup ロジック修正):
  - **Root cause**: `deduplicate_candidates()` Rule 2 がルートレベル（アートボード直下）の
    proximity候補を一律削除していた
  - **Fix 1**: Rule 1 拡張 — `pattern`, `page-kv`, `semantic` を proximity より高優先度に
  - **Fix 2**: Rule 2 修正 — `root_id` パラメータ追加でルート直下候補を除外対象から除外
- **残課題**: ネストグルーピングは Issue 23 に分離（Stage B で補完可能）
- **修正日**: 2026-03-04
- **テスト**: 全60件パス（3件追加）

## Issue 23: ネストされたグルーピングが Stage A で未対応 — CLOSED (Won't Fix)

- **Phase**: 2
- **優先度**: 低
- **概要**: Stage A の proximity/pattern 検出は各階層を独立に走査するため、
  「兄弟要素のサブグループをネストした階層構造」は生成できない。
  例: ヒーロー領域で「画像 + 見出しフレーム」を内部グループ化し、さらにそれと
  パンくずをまとめた外部グループを作る2段階ネスト。
- **クローズ理由**: Stage B（Claude 推論ベース）がスクリーンショット + コンテキスト情報を
  使って意味的なセクション分割を行うため、この機能は設計上 Stage B に委譲される。
  Stage A にマルチパス・ネストグルーピングを追加すると、アルゴリズムの複雑度が大幅に
  増加する割に Stage B が同等の結果を出せるため、費用対効果が低い。
- **クローズ日**: 2026-03-04

## Issue 27: YAML出力の特殊文字エスケープ — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: 3スクリプト（detect-grouping-candidates, generate-rename-map, infer-autolayout）
  の YAML 出力が手動文字列結合で、ノード名にダブルクォートやコロン等が含まれると
  不正な YAML が生成される。
- **修正内容**:
  - `lib/figma_utils.py` に `yaml_str()` ヘルパー関数を追加（`json.dumps` ベースで安全にエスケープ）
  - 3スクリプトの YAML 出力を `yaml_str()` 使用に変更
- **修正日**: 2026-03-04
- **ファイル**: `lib/figma_utils.py`, `scripts/detect-grouping-candidates.sh`,
  `scripts/generate-rename-map.sh`, `scripts/infer-autolayout.sh`
- **テスト**: 全60件パス（回帰なし）

## Issue 28: テストメッセージ Phase 番号不整合 + シェル変数インジェクション — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: 2つの問題を修正。
  1. **テストメッセージ**: Issue 21 の Phase スワップ後、`run-tests.sh` の fail メッセージに
     "Phase2 renames" が残存（正しくは "Phase3 renames"）。変数名 `P2_TOTAL` も紛らわしい。
  2. **シェル変数インジェクション**: 全5スクリプトで `output_file = '${OUTPUT_FILE}'` と
     シェル変数を Python コード内に直接展開。パスにシングルクォートが含まれると構文エラー。
- **修正内容**:
  - `run-tests.sh`: fail メッセージを "Phase3 renames" に修正、変数名を `P3_RENAME_TOTAL` に変更
  - 5スクリプト: `${OUTPUT_FILE}` 展開を `sys.argv` 経由のパス受け渡しに変更
- **修正日**: 2026-03-04
- **ファイル**: `tests/run-tests.sh`, 全5スクリプト
  (`detect-grouping-candidates.sh`, `generate-rename-map.sh`, `infer-autolayout.sh`,
   `prepare-sectioning-context.sh`, `enrich-metadata.sh`)
- **テスト**: 全60件パス（回帰なし）

## Issue 29: page-kv 検出ロジックの二重定義 — FIXED (設計変更)

- **Phase**: 2
- **優先度**: 低
- **概要**: `detect-grouping-candidates.sh` の `detect_page_kv_groups()` と
  `prepare-sectioning-context.sh` の `detect_heuristic_hints()` に、page-kv 検出の
  類似ロジックが重複していた。
- **修正内容**: 設計変更により `detect_page_kv_groups()` 自体を Stage A から削除。
  セマンティック理解は Stage B（Claude 推論）に委ねる方針に転換。
  `prepare-sectioning-context.sh` では `page_kv_candidates` を `gap_analysis` +
  `background_candidates` に置換し、Claude にリッチな判断材料を提供。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`, `scripts/prepare-sectioning-context.sh`,
  `references/sectioning-prompt-template.md`
- **テスト**: 全63件パス

## Issue 30: `detect_semantic_groups` が enriched fills を考慮しない — FIXED (設計変更)

- **Phase**: 2
- **優先度**: 低
- **概要**: `detect-grouping-candidates.sh` の `detect_semantic_groups()` が enriched fills
  を考慮しないため、RECTANGLE に IMAGE fill を設定したカードが検出されなかった。
- **修正内容**: 設計変更により `detect_semantic_groups()` 自体を Stage A から削除。
  Stage A は proximity + pattern の汎用検出のみに簡素化。
  セマンティック理解（カード/メディアオブジェクト判定）は Stage B（Claude 推論）に委ねる。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`
- **テスト**: 全63件パス

## Issue 31: Stage A 簡素化による Stage B 依存度増加 — FIXED

- **Phase**: 2
- **優先度**: 低
- **概要**: Stage A から semantic/page-kv を削除した結果、Stage B（Claude 推論）が
  利用不可の場合（スクリーンショット取得失敗等）にフォールバック時の警告が不足していた。
- **修正内容**: SKILL.md に Stage B フォールバック時の明示的な警告テンプレートを追加。
  Error Handling テーブルにも「Stage B スクリーンショット失敗」行を追加。
- **修正日**: 2026-03-04
- **ファイル**: `SKILL.md`

## Issue 32: generate-rename-map.sh Priority 4 fills=[] IndexError — FIXED

- **Phase**: 3
- **優先度**: 中
- **概要**: Priority 4 の `has_image` 判定で `c.get('fills', [{}])[0].get('type')` が
  enriched metadata で `fills: []` の場合に `IndexError` を引き起こすバグ。
- **修正内容**: `c.get('fills')` の存在 + 非空チェックを先行させ、安全に `any()` で判定する
  パターンに変更。テスト2件追加（enrichment pipeline 内 + 独立 unit test）。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `tests/run-tests.sh`, `tests/fixture-enrichment.json`
- **テスト**: 全65件パス（+2件追加）

## Issue 33: phase-details.md のドキュメント陳腐化 — FIXED

- **Phase**: ドキュメント
- **優先度**: 低
- **概要**: Issue 29/30 の設計変更後、phase-details.md の5箇所が陳腐化していた。
- **修正内容**:
  1. Phase 1 ペナルティ重み表を実コードに合わせ更新（ungrouped: -1/件 cap -10、autolayout: 0）
  2. Stage A セマンティック検出テーブルを削除し、Stage B 委譲の注記に置換
  3. heuristic_hints 出力例を gap_analysis + background_candidates に更新
  4. ヒューリスティックヒント定義表を更新
  5. 結果統合セクションを Stage A/B 独立適用に書き直し
- **修正日**: 2026-03-04
- **ファイル**: `references/phase-details.md`

## Issue 34: `SCRIPT_DIR` シェル変数インジェクション — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: 全6スクリプトで `sys.path.insert(0, '${SCRIPT_DIR}/../lib')` と、bash の `SCRIPT_DIR`
  変数を Python ヒアドキュメント内に直接展開していた。Issue 28 で `OUTPUT_FILE` の同種の問題は
  `sys.argv` 経由に修正済みだったが、`SCRIPT_DIR` には同じ修正が適用されていなかった。
- **リスク**: `SCRIPT_DIR` のパスにシングルクォートが含まれると Python 構文エラー。
- **修正内容**:
  - 全6スクリプトで `${SCRIPT_DIR}/..` を bash 側の最初の引数として渡し、
    Python 側で `sys.argv[1]` から lib パスを取得する方式に変更
  - 既存の `sys.argv` インデックスを全て +1 にシフト
  - `os` モジュールの import を追加
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`, `scripts/generate-rename-map.sh`,
  `scripts/detect-grouping-candidates.sh`, `scripts/infer-autolayout.sh`,
  `scripts/prepare-sectioning-context.sh`, `scripts/enrich-metadata.sh`
- **テスト**: 全65件パス（回帰なし）

## Issue 35: `infer_name()` 内の `text_contents` 二重計算 — FIXED

- **Phase**: 3
- **優先度**: 低
- **概要**: `generate-rename-map.sh` の `infer_name()` 関数で、`get_text_children_content(children)`
  が Priority 3.5（ナビゲーション検出）と Priority 4（子構造分析）の両方で呼び出されていた。
  同じ `children` に対する同一の計算であり冗長。
- **修正内容**: Priority 3.5 と Priority 4 を1つの `if children:` ブロックに統合し、
  `text_contents` を1回だけ計算して両方の Priority で共有。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`
- **テスト**: 全65件パス（回帰なし）

## Issue 36: phase-details.md の `autolayout_penalty` 出力例が非ゼロ — FIXED

- **Phase**: ドキュメント
- **優先度**: 低
- **概要**: Issue 2 で `autolayout_penalty` を計測不能として 0 固定にしたが、
  `references/phase-details.md` の YAML 出力例（`autolayout_penalty: 12`）と
  コンソール出力例（`Auto Layout penalty │ -12.0`）が更新されていなかった。
  Issue 33 のドキュメント陳腐化修正でもこの箇所は見落とされていた。
- **修正内容**: YAML 出力例を `autolayout_penalty: 0` + コメント付きに、
  コンソール出力例を `0 (excluded)` に修正。
- **修正日**: 2026-03-04
- **ファイル**: `references/phase-details.md`

## Issue 37: INSTANCE/COMPONENT/SECTION 型のヘッダー/フッター検出漏れ — FIXED

- **Phase**: 2, 3
- **優先度**: 中
- **概要**: `prepare-sectioning-context.sh` の `detect_heuristic_hints()` と `generate-rename-map.sh` の
  Priority 3.1 で、ヘッダー/フッター候補のノード型を `('FRAME', 'GROUP')` のみチェックしていた。
  Figma ではヘッダー/フッターが INSTANCE（コンポーネントインスタンス）や COMPONENT、SECTION として
  定義されることがあり、これらの型が検出から漏れていた。
- **修正内容**: 型チェックを `('FRAME', 'GROUP', 'INSTANCE', 'COMPONENT', 'SECTION')` に拡張。
  `prepare-sectioning-context.sh` のヘッダー/フッター候補検出と `generate-rename-map.sh` の
  Priority 3.1 の両方を修正。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/prepare-sectioning-context.sh`, `scripts/generate-rename-map.sh`
- **テスト**: INSTANCE header + COMPONENT footer 検出テスト追加、全67件パス

## Issue 38: characters フィールド活用でリネーム精度向上 — FIXED

- **Phase**: 3
- **優先度**: 中
- **概要**: TEXT ノードのリネームで `name` フィールドのみ使用していたが、
  enrichment 後は `characters` フィールド（実際の表示テキスト）が利用可能。
  `name` はレイヤー名（手動リネーム済みの場合は表示テキストと異なる可能性）であるのに対し、
  `characters` は常に実際の表示テキストを含む。
- **修正内容**:
  - `generate-rename-map.sh`: `infer_name()` の Priority 1 で `characters` を `name` より優先
  - `generate-rename-map.sh`: `get_text_children_content()` で `characters` を優先
  - `prepare-sectioning-context.sh`: `get_text_children_preview()` で `characters` を優先
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `scripts/prepare-sectioning-context.sh`
- **テスト**: characters フィールド優先テスト追加、全67件パス

## Issue 39: Priority 3 デッドコード文書化 — FIXED

- **Phase**: 3
- **優先度**: 低
- **概要**: `generate-rename-map.sh` の Priority 3 は `parent.get('type') in ('PAGE', 'CANVAS')` を
  チェックするが、`/figma-prepare` は通常アートボード（FRAME型）の nodeId で呼び出されるため、
  root の子要素の parent.type は常に FRAME。Priority 3 は実質的に到達不可能。
- **修正内容**: コードコメントで到達条件（PAGE/CANVAS レベルクエリ時のみ有効）を明記。
  Priority 3.1 がアートボードレベルのヘッダー/フッター検出を担っていることを文書化。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`

## Issue 40: Phase 1 スコアリングの detect_grouping_candidates 不一致を文書化 — FIXED

- **Phase**: 1
- **優先度**: 低
- **概要**: Phase 1 の `analyze-structure.sh` 内の `detect_grouping_candidates()` は簡易版で、
  Phase 2 の `detect-grouping-candidates.sh` と異なるアルゴリズム（Union-Find proximity なし、
  structure hash ではなく type+children_count ベース）を使用。
- **影響**: `ungrouped_candidates` メトリクスが Phase 2 の実際の検出結果と乖離する可能性があるが、
  スコアリングでの重みが最小（cap=10, weight=1）のため実質的な影響は軽微。
- **修正内容**: コードコメントで意図的な差異と、重みが低いため実害なしであることを文書化。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/analyze-structure.sh`

## Issue 41: YAML出力の `'pattern'` キー誤り → `'structure_hash'` に修正 — FIXED

- **Phase**: 2
- **優先度**: 低
- **概要**: `detect-grouping-candidates.sh` の YAML 出力セクションで、パターン検出されたグループの
  構造ハッシュを出力する条件分岐が `if 'pattern' in c:` となっていたが、実際のキー名は
  `'structure_hash'`。結果として YAML 出力にパターン情報が含まれないバグ。
- **影響**: JSON 出力は全キーをダンプするため影響なし。YAML 出力のみ `structure_hash` が欠落。
- **修正内容**: `'pattern'` → `'structure_hash'` にキー名を修正。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/detect-grouping-candidates.sh`
- **テスト**: Issue 41 テストケース追加（YAML出力にstructure_hashキーが存在することを検証）

## Issue 42: sectioning-prompt-template.md の Phase 番号誤り — FIXED

- **Phase**: docs
- **優先度**: 低
- **概要**: `references/sectioning-prompt-template.md` の冒頭に "Phase 3 Stage B" と記載されていたが、
  Issue 21 の Phase 番号入れ替え後は "Phase 2 Stage B" が正しい。
- **修正内容**: "Phase 3 Stage B" → "Phase 2 Stage B"、"Step 3-2c" → "Step 2-2c" に修正。
- **修正日**: 2026-03-04
- **ファイル**: `references/sectioning-prompt-template.md`

## Issue 43: phase-details.md 信頼度テーブルの陳腐化 — FIXED

- **Phase**: docs
- **優先度**: 低
- **概要**: `references/phase-details.md` の Phase 4 信頼度テーブルに以下の問題:
  1. Issue 18 で追加された `exact` 信頼度（enriched layoutMode 由来）が未記載
  2. `low` 信頼度（Gap ばらつき大）が文書化されていたが、コードでは未実装
- **修正内容**: テーブルを実装に合わせて更新。`exact` を追加、`low` を削除。enriched metadata からの
  直接取得に関する説明を追記。
- **修正日**: 2026-03-04
- **ファイル**: `references/phase-details.md`

## Issue 44: 未使用 import 削除 — FIXED

- **Phase**: 2, 3
- **優先度**: 低
- **概要**: 以下のスクリプトに未使用の Python import が残存:
  - `generate-rename-map.sh`: `unicodedata` — `to_kebab()` のリファクタ時に不要になった
  - `detect-grouping-candidates.sh`: `re` — `UNNAMED_RE` を `figma_utils` から import に切り替え後に不要に
- **修正内容**: 不要な import を削除。
- **修正日**: 2026-03-04
- **ファイル**: `scripts/generate-rename-map.sh`, `scripts/detect-grouping-candidates.sh`

## Issue 45: `to_kebab` + `JP_KEYWORD_MAP` コード重複 — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: `generate-rename-map.sh` と `run-tests.sh` に `to_kebab()` 関数と `JP_KEYWORD_MAP` 辞書が
  完全に重複していた。DRY原則違反であり、一方を変更すると他方との乖離リスクがあった。
- **修正内容**: `to_kebab()` と `JP_KEYWORD_MAP` を `lib/figma_utils.py` に移動。
  `generate-rename-map.sh` は `from figma_utils import to_kebab` に変更。
  `run-tests.sh` も `figma_utils.to_kebab` を直接 import してテスト。
  副作用として `generate-rename-map.sh` の `import re` が不要になったため削除。
- **修正日**: 2026-03-05
- **ファイル**: `lib/figma_utils.py`, `scripts/generate-rename-map.sh`, `tests/run-tests.sh`

## Issue 46: confidence 定義の不一致 — CLOSED (Not an Issue)

- **Phase**: docs
- **優先度**: 低
- **概要**: Phase 4 の confidence 判定ロジックが rules とコードで異なると疑われたが、
  調査の結果 `phase-details.md`（正のソース）は既に Issue 43 で正しく更新済み
  （子要素数ベース: 3+ → high, 2 → medium）。`figma-prepare.md` には confidence 定義自体が
  存在しないため不整合は発生していなかった。
- **修正日**: 2026-03-05
- **ファイル**: なし

## Issue 47: `to_kebab` CamelCase 分割未実装 — FIXED

- **Phase**: 3
- **優先度**: 低
- **概要**: `to_kebab()` の docstring に「Camel-case parsing via re.sub + lowercase」と記載されていたが、
  実際には CamelCase 分割ロジックが未実装だった。`CamelCaseText` → `camelcasetext` になっていた。
  Figma の自動生成名はスペース区切り（`Frame 1`）のため影響は限定的だが、
  ユーザー定義のレイヤー名（`HeroSection` 等）で不適切な命名になる可能性があった。
- **修正内容**: `to_kebab()` に CamelCase 分割の `re.sub` を2つ追加:
  1. `([a-z])([A-Z])` → `\1 \2` (camelCase → camel Case)
  2. `([A-Z]+)([A-Z][a-z])` → `\1 \2` (HTMLParser → HTML Parser)
  テストケース3件追加: `CamelCase`, `HTMLParser`, `myComponent`
- **修正日**: 2026-03-05
- **ファイル**: `lib/figma_utils.py`, `tests/run-tests.sh`

## Issue 48: 深いネスト Figma ファイルで再帰制限クラッシュ — FIXED

- **Phase**: 全体
- **優先度**: 中
- **概要**: 全スクリプトの再帰関数（`count_nodes`, `walk_and_detect`, `walk_and_infer`,
  `collect_renames`, `resolve_absolute_coords`, `enrich_node`）に Python デフォルト再帰制限（1000）の
  ガードがなかった。極端にネストの深い Figma ファイルで `RecursionError` クラッシュの可能性があった。
- **修正内容**: 6スクリプト全てに `sys.setrecursionlimit(3000)` を追加。
  Figma のネスト深度は通常100以下だが、安全マージンとして3000に設定。
- **修正日**: 2026-03-05
- **ファイル**: `scripts/analyze-structure.sh`, `scripts/detect-grouping-candidates.sh`,
  `scripts/generate-rename-map.sh`, `scripts/infer-autolayout.sh`,
  `scripts/prepare-sectioning-context.sh`, `scripts/enrich-metadata.sh`
