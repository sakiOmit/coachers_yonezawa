# Apply Workflow (--apply Details)

Phase 2/3/4 の `--apply` 実行時の詳細手順。evaluate_script パターン、ID マッピング、検証手順を記載。

## Phase 2: --apply 適用手順

### 2-5a. Stage B 適用: 再帰的セクショニング（必須）

sectioning-plan.yaml の階層構造を**トップダウンで再帰的に**適用する。

```
適用順序（トップダウン、外側から内側へ）:

Level 1: ルート直下のトップレベルセクション
  - l-header ラッパー（node_ids が2個以上の場合）
  - main-content ラッパー（subsections の全 node_ids をフラット収集）
  - l-footer ラッパー（node_ids が2個以上の場合）
  → apply-grouping.js 実行 → 各ラッパーの新IDを記録

Level 2: main-content 内の subsections
  - section-hero-area ラッパー（parent_id = main-content の新ID）
  - section-concept-area ラッパー（parent_id = main-content の新ID）
  - ...（subsections を持つセクションのみ）
  → apply-grouping.js 実行 → 各ラッパーの新IDを記録

Level 3+: さらにネストされた subsections（存在する場合）

※ 各レベル適用後に新ラッパーIDが発生するため、次レベルの parent_id は
  前レベルの apply-grouping.js 出力 wrappers[].id から取得する。
```

### 2-5b. sectioning-plan → grouping-plan 変換ロジック

```python
def flatten_sectioning_plan(sections, parent_id, clone_mapping):
    """sectioning-plan.yaml を apply-grouping.js 用の grouping-plan に変換。
    レベルごとにグループ化して返す。"""
    levels = {}  # {depth: [grouping_entry, ...]}

    def recurse(section_list, parent, depth):
        for section in section_list:
            if 'subsections' in section:
                # コンテナセクション: subsections の全 node_ids をフラット収集
                all_ids = collect_all_leaf_ids(section['subsections'])
                # clone_mapping で変換
                clone_ids = [clone_mapping[orig] for orig in all_ids if orig in clone_mapping]
                if len(clone_ids) >= 2:
                    entry = {
                        'node_ids': clone_ids,
                        'suggested_name': section['name'],
                        'parent_id': parent
                    }
                    levels.setdefault(depth, []).append(entry)
                # subsections を次のレベルで再帰
                recurse(section['subsections'], section['name'], depth + 1)
            else:
                # リーフセクション: node_ids が2個以上ならラッパー作成
                clone_ids = [clone_mapping[orig] for orig in section.get('node_ids', []) if orig in clone_mapping]
                if len(clone_ids) >= 2:
                    entry = {
                        'node_ids': clone_ids,
                        'suggested_name': section['name'],
                        'parent_id': parent
                    }
                    levels.setdefault(depth, []).append(entry)

    recurse(sections, parent_id, 0)
    return levels

def collect_all_leaf_ids(subsections):
    """subsections ツリーから全リーフ node_ids をフラットに収集"""
    ids = []
    for sub in subsections:
        if 'subsections' in sub:
            ids.extend(collect_all_leaf_ids(sub['subsections']))
        else:
            ids.extend(sub.get('node_ids', []))
    return ids
```

### 2-5c. レベル間の parent_id 再マッピング

```
Level N の apply-grouping.js 実行後:
  result.wrappers = [{ id: "61:500", name: "main-content" }, ...]

Level N+1 の grouping-plan で parent_id が "main-content"（名前参照）の場合:
  → result.wrappers から name が一致する wrapper の id を取得
  → parent_id = "61:500" に置換

※ node_ids が1個のみのセクションはラッパー不要。
  代わりにリネーム（node.name = section_name）で対応する。
```

### 2-5d. apply-grouping.js 実行（各レベル）

```
使用手順（レベルごとに繰り返す）:
1. scripts/apply-grouping.js を読み込み
2. __GROUPING_PLAN__ を該当レベルの候補JSONに置換（node_ids, suggested_name, parent_id）
3. __BATCH_INFO__ をバッチ情報に置換（例: "1/3"）
4. evaluate_script で実行 → ラッパーFrame作成 + 子要素移動
5. 結果の wrappers[].id を記録（次レベルの parent_id に使用）
```

### 2-5e. Stage A / Stage C 適用（再帰的マルチデプス対応 — Issue #227）

結果統合（2-4）で採用されたネストレベルグルーピング候補を適用。
Stage C の再帰結果により nested-grouping-plan.yaml は複数の depth を持つ。

```
使用手順:
1. nested-grouping-plan.yaml の全 depth を確認
   ※ depth 0: リーフセクション内の直接グルーピング
   ※ depth 1+: 非single グループ内の再帰的グルーピング

2. depth 0 から昇順に適用（外→内）:
   FOR depth = 0 TO max_depth:
     a. 該当 depth のグルーピング候補を抽出
        ※ Stage C 採用セクションは nested-grouping-plan.yaml から
        ※ フォールバックセクションは grouping-plan.yaml から（depth 0 のみ）
     b. parent_id を現在のノード親から動的取得
        ※ depth 0: evaluate_script で node.parent.id を取得
        ※ depth > 0: 前 depth で作成されたラッパーが新しい parent
     c. apply-grouping.js で実行 → 新ラッパーIDを記録
     d. 次 depth の parent_id マッピングを更新

3. Stage A フォールバックセクションは depth 0 のみ

4. verify-grouping.js で全 depth のラッパーを検証
```

### Phase 2 構造 diff 検証

`--apply` 実行後、`verify-grouping.js` で**全レベルの**ラッパーFRAME・子要素移動・bbox整合性を検証。

```
使用手順:
1. scripts/verify-grouping.js を読み込み
2. __VERIFICATION_PLAN__ を検証データJSONに置換（全レベルのラッパーを含む）:
   [
     {
       "wrapper_id": "61:467",
       "expected_name": "main-content",
       "expected_child_ids": ["61:500", "61:501", "61:266", ...]
     },
     ...
   ]
3. evaluate_script で実行

検証項目:
  a. ラッパーFRAMEの存在・名前一致
  b. 期待される子要素がラッパー内に存在
  c. ラッパーbbox ≈ 子要素union bbox（±2px許容）

判定:
  - matchRate >= 0.98 → 成功
  - matchRate < 0.98 → 警告 + issues 一覧表示
```

## Phase 3: --apply 実行（Adjacent Artboard 方式）

### 3-3a. Chrome DevTools MCP 接続確認

```
mcp__chrome-devtools__evaluate_script
  function: () => typeof figma
→ "object" 以外の場合: プラグイン開閉を案内して中止
```

### 3-3b. アートボード複製

```
mcp__chrome-devtools__evaluate_script の function パラメータにインラインで渡す:
  - figma.getNodeById(sourceNodeId) でソース取得
  - source.clone() で深い複製
  - clone.x = source.x + source.width + 100 で右隣に配置
  - buildMapping() で並行DFS → IDマッピング生成

結果: { clone: { id, name }, mapping: {...}, total: N, nameMatchRate }
nameMatchRate < 0.95 の場合: 警告表示 + 続行確認

パターン: figma-plugin-api.md「Adjacent Artboard」参照
```

### 3-3c. グルーピング適用（Phase 2 結果をクローンに反映 — 必須）

**Phase 2 のグルーピング計画を、クローンしたアートボードに適用する。**
**このステップを飛ばすと、フラット構造のままリネームだけが行われ、構造化が一切されない。**

```
手順:
1. sectioning-plan.yaml と grouping-plan.yaml を読み込む
2. flatten_sectioning_plan() ロジックで変換
   ※ node_ids を clone_mapping で変換（元ID → クローンID）
3. レベルごとにトップダウンで apply-grouping.js を実行
4. 各レベル適用後、wrappers[].id を記録して次レベルの parent_id に使用
5. Stage A / Stage C のネストレベルグルーピングを depth 0 から適用
6. Stage C 再帰ネストの適用（depth 1+）
7. verify-grouping.js で全 depth のラッパーを含む構造 diff 検証
```

### 3-3d. リネームマップの ID 変換

```
rename-map.yaml の各 nodeId を mapping テーブルで変換:
  元 ID (例: "1:10") → 複製 ID (例: "23:55")

変換できない ID は警告としてスキップ。
※ 3-3c でグルーピングにより新しいラッパーFrameが追加されているため、
  clone_mapping に存在しない新規IDはスキップして問題ない。
```

### 3-3e. バッチリネーム実行

```
1. 変換済みリネームマップを 50件/バッチ に分割
2. 各バッチごとに:
   mcp__chrome-devtools__evaluate_script の function パラメータで実行:
     - renameMap オブジェクトをインライン埋め込み
     - figma.getNodeById() → node.name = newName
   結果: { renamed: N, skipped: N, errors: [...] }
3. 全バッチの結果を集計

パターン: figma-plugin-api.md「Phase 3: リネーム」参照
```

### 3-3f. 構造 diff 検証

```
1. verify-structure.js でクローンのツリーを読み戻し
   - __CLONE_NODE_ID__ にクローンID、__EXPECTED_NAMES__ にリネームマップを埋め込み
   - evaluate_script で実行

2. リネームマップの期待名と actual name を比較
   結果: { total, matched, mismatched, missing, matchRate }

3. 判定:
   - matchRate >= 0.98 → 成功
   - matchRate < 0.98 → 警告 + mismatch 一覧表示

4. 補助: スクリーンショットでビジュアル崩れがないか確認（任意）
```

### 3-3g. 結果サマリー

```
╔══════════════════════════════════════════════╗
║         Phase 3: Rename Applied             ║
╠══════════════════════════════════════════════╣

Method: Adjacent Artboard (clone + rename)

Clone: "{cloneName}" (ID: {cloneId})
  Position: x={x}, y={y}

Results:
  Renamed: {renamed} layers
  Skipped: {skipped} layers
  Errors:  {errorCount}

Verification:
  Structure diff: {matched}/{total} matched ({matchRate}%)
  Visual check: screenshot available (supplementary)

Original artboard: unchanged

Next:
  - Figma で Before/After を並べて確認
  - 問題なければ元アートボードを削除し複製を採用
  - 修正が必要な場合は複製を削除して再実行
╚══════════════════════════════════════════════╝
```

## Phase 4: --apply 適用手順

```
使用手順:
1. scripts/apply-autolayout.js を読み込み
2. __AUTOLAYOUT_PLAN__ をレイアウトJSON配列に置換（node_id, direction, gap, padding, etc.）
3. __BATCH_INFO__ をバッチ情報に置換（例: "1/2"）
4. __MIN_CONFIDENCE__ を最低信頼度に置換（"medium" 推奨 — exact+high+medium を適用、low はスキップ）
5. evaluate_script で実行 → layoutMode/itemSpacing/padding/counterAxisAlignItems 設定
```

### Phase 4 検証

```
使用手順:
1. scripts/verify-autolayout.js を読み込み
2. __VERIFICATION_PLAN__ を検証データJSONに置換:
   [
     {
       "node_id": "23:55",
       "expected_direction": "VERTICAL",
       "expected_gap": 24,
       "expected_padding": { "top": 16, "right": 16, "bottom": 16, "left": 16 },
       "expected_primary_align": "MIN",
       "expected_counter_align": "CENTER"
     }
   ]
3. evaluate_script で実行

検証項目:
  a. ノードの存在確認
  b. layoutMode / layoutWrap が期待方向と一致
  c. itemSpacing が期待値と一致（±1px許容）
  d. padding 4辺が期待値と一致（±1px許容）
  e. primaryAxisAlignItems / counterAxisAlignItems が一致

判定:
  - matchRate >= 0.98 → 成功
  - matchRate < 0.98 → 警告 + issues 一覧表示
```

## Stage C 再帰的適用順序（Issue #227）

```
Stage B (sectioning-plan.yaml)
  Level 1 → Level 2 → ... → Level N
    ↓ parent_id マッピング更新

Stage C depth 0 (nested-grouping-plan.yaml, depth=0)
  各セクションの直接 children をグルーピング
    ↓ 新ラッパーID記録

Stage C depth 1 (nested-grouping-plan.yaml, depth=1)
  depth 0 で生成されたラッパー内部をサブグルーピング
    ↓ 新ラッパーID記録

Stage C depth 2+ ...

Stage A fallback (grouping-plan.yaml)
  Stage C カバレッジ < 80% のセクションのみ、depth 0 で適用

verify-grouping.js
  全 depth のラッパーを一括検証
```
