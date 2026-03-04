# Figma Rules

## Overview

このルールファイルは、Figma MCP連携における実装規約を統合的に定義します。
キャッシュ戦略、分割取得、コンポーネント再利用、Code Connect連携、nodeベース実装、アセット書き出しを含みます。

## 実装前準備

### 実装前チェックリスト

Figma実装を開始する前に、以下を確認せよ:

| 項目 | 確認コマンド | 期待結果 |
|------|-------------|---------|
| キャッシュ | `ls -la .claude/cache/figma/` | 24時間以内のキャッシュがあれば利用 |
| visual-diff依存関係 | `npm list pixelmatch pngjs` | インストール済み |
| Figma Variables | `get_variable_defs` | 空でないこと（空なら手動抽出） |
| Code Connect | `get_code_connect_map` | 登録済みコンポーネント確認 |

### /figma-analyze の実行（複数ページ時推奨）

複数ページの実装前に `/figma-analyze` を実行し、以下を事前に把握する:

- ページ構造と複雑度スコア
- 分割戦略（NORMAL / SPLIT / SPLIT_REQUIRED）
- ページ横断の共通コンポーネント
- 既存カタログとのマッチング結果
- 推奨実装順序

```bash
/figma-analyze {url1} {url2} {url3}
```

レポートは `.claude/cache/figma/analysis-report.yaml` に出力される。

## キャッシュ戦略

### キャッシュの自動保存

`mcp__figma__get_design_context` のレスポンスは自動的にキャッシュされます:

- **保存場所**: `.claude/cache/figma/`
- **ファイル名**: `{fileKey}_{nodeId}_{timestamp}.json`
- **TTL**: 24時間（自動クリーンアップ）

### セッション開始時のキャッシュ確認（必須）

Figma実装を開始する前に、必ずキャッシュを確認:

```bash
ls -la .claude/cache/figma/
```

### キャッシュ利用の判断

| 条件 | 対応 |
|------|------|
| 24時間以内 + デザイン変更なし | キャッシュ利用（Read ツール） |
| 24時間超過 | 新規取得（get_design_context） |
| デザイン変更あり | 新規取得（get_design_context） |

### キャッシュ読み込み手順

```
1. ls .claude/cache/figma/ でファイル一覧確認
2. ファイル名から対象のfileKey/nodeIdを特定
3. Read ツールで該当ファイルを読み込み
4. cache_data.output を使用して実装
```

### PreToolUse フック

`get_design_context` 呼び出し時、PreToolUseフックが自動でキャッシュを検索:

- キャッシュヒット時: 通知メッセージが表示される
- キャッシュミス時: 通常通りAPI呼び出し

## 大規模ページの分割

### 分割検討の基準

以下の場合、セクション分割を検討:

| 条件 | 対応 |
|------|------|
| トップレベルフレーム > 5 | 分割推奨 |
| 推定要素数 > 100 | 分割推奨 |
| トークン制限エラー | 強制分割 |

### 分割基準（詳細）

| 条件 | 閾値 |
|------|------|
| フレーム高さ | 2,000px 超 |
| 子要素数 | 20個 超 |

### 複雑度ベース分割基準

```
complexity = 子要素数 + (ネスト深度 × 5) + (テキスト要素数 × 0.5)
```

| スコア | アクション |
|--------|----------|
| 50以上 | 分割取得 |
| 50未満 | 通常取得 |

**除外条件:**
- `visible: false` のフレームはスキップ
- hidden レイヤーは複雑度計算から除外

### トークン制限対策

| 条件 | アクション |
|------|----------|
| 高さ 8,000px 以上 | get_metadata を先行実行 |
| 高さ 10,000px 以上 | 必ず分割取得 |

```
if (height >= 10000px) → 必須分割
else if (height >= 8000px) → metadata先行 + 状況判断
else → 通常取得可能
```

### トークン制限エラーの検出

レスポンスに以下が含まれている場合、トークン制限:

```
⚠️ Output size too large - returning metadata and screenshot only
⚠️ Node data omitted due to size constraints
```

### 分割実装の3フェーズワークフロー

5セクション以上のページは以下の3フェーズで実施:

#### Phase 1: 解析フェーズ
- get_metadata でページ構造取得
- セクション分割計画作成
- 共通コンポーネント特定

#### Phase 2: 分割取得フェーズ
- セクションごとに get_design_context
- デザイントークン抽出
- アセットダウンロード

#### Phase 3: 統合実装フェーズ
- SCSS/PHP 生成
- コンポーネント統合
- ビジュアル検証

### 分割手順（基本）

```
1. get_metadata でページ構造を事前取得
2. トップレベルフレーム（セクション）を特定
3. 各セクションのnodeIdを抽出
4. セクションごとに get_design_context を実行
5. 結果を統合して実装
```

## コンポーネント再利用

### Code Connect 連携ルール

#### 利用可能な場合のみ（Enterprise/Team プラン限定）

Code Connect は Figma の Organization/Enterprise プラン限定機能。
**利用可能な場合のみ** Code Connect 情報を取得する:

```
mcp__figma__get_code_connect_map
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
```

**プラン制限により利用できない場合:**
- `component-catalog.yaml` による手動管理で代替
- `/figma-analyze` の Phase 4 カタログマッチングを使用

#### 利用可能時: add_code_connect_map 登録

Enterprise/Team プランで利用可能な場合、新規コンポーネント作成後に登録:

```
mcp__figma__add_code_connect_map
  nodeId: "{nodeId}"
  fileKey: "{fileKey}"
  source: "template-parts/components/{component-name}.php"
  componentName: "c-{component-name}"
  label: "PHP"
```

**登録対象:**
- 新規作成した再利用可能コンポーネント
- template-parts/common/ または template-parts/components/ に配置したもの
- FLOCSS の c-* (component) に該当するもの

**登録不要:**
- ページ固有のセクション（p-about-hero 等）
- 一度きりの使用要素

#### Code Connect 前提条件

- Figmaプランが Organization または Enterprise であること
- プラン制限により利用できない場合は、component-catalog.yaml のみ手動更新

### コンポーネントカタログ維持ルール

#### カタログファイル

`.claude/data/component-catalog.yaml`

#### 更新タイミング

| イベント | アクション |
|---------|----------|
| 新規コンポーネント作成 | カタログに追加 |
| コンポーネント削除 | カタログから削除 |
| props変更 | カタログを更新 |
| variant追加 | カタログを更新 |

#### 追加時の必須項目

```yaml
- name: c-{component-name}
  file: template-parts/{path}/{component-name}.php
  scss: src/scss/object/component/_c-{component-name}.scss
  type: {button|card|heading|navigation|etc}
  description: "コンポーネントの説明"
  variants: []
  props:
    required: []
    optional: []
  figma_patterns:
    - "Pattern/*"
```

### 再利用判定ルール

#### マッチングスコア計算

| 条件 | スコア |
|------|--------|
| Code Connect 登録済み（Enterprise/Team のみ） | 100%（即座に確定） |
| type 一致 | +40% |
| 必須props充足 | +30% |
| variant対応可能 | +20% |
| figma_patterns一致 | +10% |

#### 判定閾値

| スコア | 判定 | アクション |
|--------|------|----------|
| 70%以上 | 高一致（REUSE） | 既存コンポーネントをそのまま使用 |
| 40-69% | 中一致（EXTEND） | 既存ベース + カスタムスタイル |
| 40%未満 | 低一致（NEW） | 新規コンポーネント作成 |

#### 判定フロー

```
1. Code Connect 登録あり?（Enterprise/Team プランのみ）
   → Yes: 既存コンポーネント使用（100%）
   → No / プラン非対応: 次へ

2. カタログ照合（component-catalog.yaml）
   → type一致 + props充足 + variant対応
   → スコア算出

3. スコアに基づく判定
   → 70%以上: 既存使用（REUSE）
   → 40-69%: 既存ベース + カスタム（EXTEND）
   → 40%未満: 新規作成（NEW）

4. 新規作成の場合
   → カタログ更新（必須）
   → Code Connect 登録（Enterprise/Team プランの場合のみ）
```

## nodeベース実装（厳守）

### 正しい実装フロー

```
1. get_design_context でnode情報取得
2. nodeデータから色・フォント・スペーシング抽出
3. SCSS変数に変換
4. WordPress テンプレート実装
5. Playwright で検証
```

## アセット書き出し

### 2倍サイズ（必須）

```
Figma表示サイズ → 書き出しサイズ
300px × 200px  → 600px × 400px (@2x)
```

### アセット配置

```
themes/{{THEME_NAME}}/assets/images/
```

### プレースホルダー禁止

- 仮画像（placeholder.jpg等）の使用禁止
- 必ず実際のアセットをダウンロード

## Figma Variables

### 空オブジェクト時の対応

`get_variable_defs` が空オブジェクト `{}` を返した場合:

1. Figma側でVariablesが定義されていない可能性が高い
2. キャッシュまたは get_design_context の node 情報から手動抽出
3. 色・フォント・スペーシングを抽出して SCSS 変数に変換
4. 抽出した値は foundation/_variables.scss に追加

## Figma差分検出の許容差設定

| 項目 | 許容差 | 備考 |
|------|--------|------|
| 数値（px） | ±1px | 位置・サイズ |
| 色（RGB） | 完全一致 | 各チャンネル±0 |
| 透明度 | ±0.01 | opacity/alpha |

### 厳密モード

許容差0で検証する場合は `--strict` オプションを使用

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| スクリーンショットのみでの実装 | クラス名不正確、構造把握不可 |
| 推測によるスタイル値 | Figma nodeと乖離 |
| 独自解釈での数値変更 | デザイン崩れ |
| `get_screenshot` を実装データ源として使用 | nodeデータなし、構造把握不可。`get_metadata` + セクション分割で対処 |
| サイズオーバー時のスクリーンショットフォールバック | 実装精度低下。メタデータ + セクション分割で対処 |
| カタログ確認せずに新規作成 | 重複実装のリスク |
| カタログ更新忘れ | 照合精度低下 |
| 既存コンポーネントの無視 | 一貫性・保守性低下 |
| 手動照合のみ | 判定基準のブレ |

## チェックリスト

### セッション開始時
- [ ] キャッシュディレクトリ確認
- [ ] 24時間以内のキャッシュがあれば利用

### 実装前
- [ ] `/figma-analyze` を実行した（複数ページ時）
- [ ] 大規模ページの分割判断
- [ ] component-catalog.yaml を参照した
- [ ] 再利用判定表を作成した

### 実装中
- [ ] nodeデータから値を抽出（推測禁止）
- [ ] アセットは2倍サイズで書き出し
- [ ] kebab-case命名（FLOCSS + BEM）

### 実装後
- [ ] 新規作成時はカタログを更新した
- [ ] Code Connect 登録した（Enterprise/Team プランの場合のみ）
- [ ] Playwrightでセクション別検証
- [ ] production-reviewerでレビュー

## 関連ファイル

- `.claude/skills/figma-analyze/SKILL.md` - Figma複数ページ分析
- `.claude/skills/figma-implement/SKILL.md` - Figma実装ワークフロー
- `.claude/data/component-catalog.yaml` - コンポーネントカタログ
