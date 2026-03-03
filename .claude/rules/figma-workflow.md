# Figma Workflow Rules

## Overview

このルールファイルは、Figma → WordPress 実装ワークフローにおける
Code Connect 連携とコンポーネント再利用のルールを定義します。

## 実装前分析（推奨）

### /figma-analyze の実行

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

## Code Connect 連携ルール

### 利用可能な場合のみ（Enterprise/Team プラン限定）

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

### 利用可能時: add_code_connect_map 登録

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

## Code Connect制限事項

### プラン制限

Code Connectは Organization/Enterprise プラン限定。
利用不可の場合は component-catalog.yaml による手動管理を推奨。

### 前提条件

Code Connect機能を使用する前に、以下を確認せよ:

- Figmaプランが Organization または Enterprise であること
- プラン制限により利用できない場合は、component-catalog.yaml のみ手動更新

## コンポーネントカタログ維持ルール

### カタログファイル

`.claude/data/component-catalog.yaml`

### 更新タイミング

| イベント | アクション |
|---------|----------|
| 新規コンポーネント作成 | カタログに追加 |
| コンポーネント削除 | カタログから削除 |
| props変更 | カタログを更新 |
| variant追加 | カタログを更新 |

### 追加時の必須項目

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

## 再利用判定ルール

### マッチングスコア計算

| 条件 | スコア |
|------|--------|
| Code Connect 登録済み（Enterprise/Team のみ） | 100%（即座に確定） |
| type 一致 | +40% |
| 必須props充足 | +30% |
| variant対応可能 | +20% |
| figma_patterns一致 | +10% |

### 判定閾値

| スコア | 判定 | アクション |
|--------|------|----------|
| 70%以上 | 高一致（REUSE） | 既存コンポーネントをそのまま使用 |
| 40-69% | 中一致（EXTEND） | 既存ベース + カスタムスタイル |
| 40%未満 | 低一致（NEW） | 新規コンポーネント作成 |

### 判定フロー

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

## 禁止事項

| 禁止項目 | 理由 |
|---------|------|
| カタログ確認せずに新規作成 | 重複実装のリスク |
| カタログ更新忘れ | 照合精度低下 |
| 既存コンポーネントの無視 | 一貫性・保守性低下 |
| 手動照合のみ | 判定基準のブレ |
| `get_screenshot` を実装データ源として使用 | nodeデータなし、構造把握不可。`get_metadata` + セクション分割で対処 |
| サイズオーバー時のスクリーンショットフォールバック | 実装精度低下。メタデータ + セクション分割で対処 |

## チェックリスト

Figma実装時に確認:

- [ ] `/figma-analyze` を実行した（複数ページ時）
- [ ] component-catalog.yaml を参照した
- [ ] 再利用判定表を作成した
- [ ] 新規作成時はカタログを更新した
- [ ] Code Connect 登録した（Enterprise/Team プランの場合のみ）

## 分割実装ルール（3フェーズワークフロー）

5セクション以上のページは以下の3フェーズで実施:

### Phase 1: 解析フェーズ
- get_metadata でページ構造取得
- セクション分割計画作成
- 共通コンポーネント特定

### Phase 2: 分割取得フェーズ
- セクションごとに get_design_context
- デザイントークン抽出
- アセットダウンロード

### Phase 3: 統合実装フェーズ
- SCSS/PHP 生成
- コンポーネント統合
- ビジュアル検証

## Figma Variables空時の対応

get_variable_defs が空オブジェクト {} を返した場合:

1. Figma側でVariablesが定義されていない可能性が高い
2. キャッシュまたは get_design_context の node 情報から手動抽出
3. 色・フォント・スペーシングを抽出して SCSS 変数に変換
4. 抽出した値は foundation/_variables.scss に追加

## 関連ファイル

- `.claude/skills/figma-analyze/SKILL.md` - Figma複数ページ分析
- `.claude/skills/figma-implement/SKILL.md` - Figma実装ワークフロー
- `.claude/data/component-catalog.yaml` - コンポーネントカタログ

## Figma差分検出の許容差設定

| 項目 | 許容差 | 備考 |
|------|--------|------|
| 数値（px） | ±1px | 位置・サイズ |
| 色（RGB） | 完全一致 | 各チャンネル±0 |
| 透明度 | ±0.01 | opacity/alpha |

### 厳密モード
許容差0で検証する場合は `--strict` オプションを使用
