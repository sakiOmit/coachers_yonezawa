# Figma Implement Workflow Steps

Detailed step-by-step instructions for the `/figma-implement` skill.
This file is referenced by [SKILL.md](SKILL.md) when detailed workflow guidance is needed.

---

## Usage

```
/figma-implement {pc_url} [--sp {sp_url}]
```

ユーザーにFigma URLを尋ねてください。PC/SP両方のURLがある場合は `--sp` オプションで指定可能。

**前提条件:** `/figma-prefetch` を事前に実行し、キャッシュが有効であること。

取得後、以下の9ステップワークフローを実行:

---

## Design Prerequisites（デザイン側の前提条件）

高い実装精度を得るために、Figmaデザインが以下の条件を満たしていることを確認:

### 必須条件

| 条件 | 理由 |
|------|------|
| Auto Layout の適切な使用 | JSX出力で正確なスペーシング・配置を取得可能 |
| セマンティックなレイヤー命名 | AIが要素の意味を推測可能 |
| ベクターグループのフラット化 | 複数の `<img>` タグ生成を防止 |

### 高精度で再現される要素

Auto Layout が適切に使用されている場合:
- フォントファミリー、ウェイト、サイズ、行間
- テキスト/背景/ボーダー色
- Auto Layout ベースの配置・余白

### 調整が必要な可能性がある要素

| 要素 | 理由 |
|------|------|
| 絶対配置（absolute）要素 | CSS調整が必要な場合あり |
| 複雑なベクターグラフィック | プレースホルダー化またはSVGエクスポート推奨 |

### ベクター要素の問題と対策

**問題:** 多数のベクターを含む要素は、個別の `<img>` タグとして認識される

**対策:**
1. ベクター多用要素はプレースホルダー化
2. SVGとして再度コピー・貼付け
3. 冗長なグループを解除してフラット化

---

## Prerequisites Check（前提条件確認）

> **重要:** このスキルを使用する前に `/figma-prefetch` を実行してください。

### キャッシュ確認

```bash
ls -la .claude/cache/figma/{page-name}/
```

**必須キャッシュ構造:**
```
.claude/cache/figma/{page-name}/
├── metadata.json          # get_metadata result
├── design-context.json    # get_design_context result
└── prefetch-info.yaml     # Prefetch metadata
```

**キャッシュがない場合:**
```
⚠️ キャッシュが見つかりません。
   先に /figma-prefetch を実行してください:

   /figma-prefetch {figma_url}
```

**大規模ページ（5000px以上）の場合:**
`/figma-prefetch` が以下を推奨します:
- `/figma-recursive-splitter` - 単独作業向け
- `/figma-section-splitter` - 並列作業向け

詳細: `.claude/skills/figma-prefetch/SKILL.md`

---

## Step 1: ノードID取得

### 1-1. URL解析

Figma URLからfileKeyとnodeIdを抽出:

```
URL形式: https://figma.com/design/{fileKey}/{fileName}?node-id={nodeId}

例:
https://figma.com/design/abc123xyz/MyDesign?node-id=1-2
→ fileKey: abc123xyz
→ nodeId: 1:2 (URLの1-2を1:2に変換)
```

### 1-2. ブランチURL対応

ブランチURLの場合は branchKey を fileKey として使用:

```
URL形式: https://figma.com/design/{fileKey}/branch/{branchKey}/{fileName}
→ fileKey として branchKey を使用
```

---

## Step 2: デザインコンテキスト取得

### 2-1. get_design_context 実行 (PC)

**キャッシュ確認（CLI事前取得済みの場合）:**

```bash
ls .claude/cache/figma/{page-name}/pc/*.json
```

**キャッシュが存在する場合:**
- ✅ MCP呼び出しスキップ
- ✅ Read ツールでキャッシュファイルを読み込み

**キャッシュが存在しない場合（MCP経由で取得）:**

```
mcp__figma__get_design_context
  fileKey: "{pc_fileKey}"
  nodeId: "{pc_nodeId}"
  clientLanguages: "php,scss,javascript"
  clientFrameworks: "wordpress"
```

### 2-1b. get_design_context 実行 (SP) ※ --sp オプション使用時

`--sp` オプションが指定されている場合、SP版のデザインコンテキストも取得:

```
mcp__figma__get_design_context
  fileKey: "{sp_fileKey}"
  nodeId: "{sp_nodeId}"
  clientLanguages: "php,scss,javascript"
  clientFrameworks: "wordpress"
```

**キャッシュ保存先:**
- PC: `.claude/cache/figma/{page-name}/pc/`
- SP: `.claude/cache/figma/{page-name}/sp/`

### 2-2. コンポーネント照合準備

デザインコンテキストから要素情報を抽出し、既存コンポーネントとの照合準備:

**照合対象の抽出:**
- ボタン要素（Button, CTA等）
- カード要素（Card, Article等）
- ナビゲーション要素（Nav, Menu等）
- フォーム要素（Input, Select等）

**照合実行:**
- Step 5-2で component-catalog.yaml と自動照合
- マッチングスコアに基づき再利用判定
- 80%以上: 既存使用、50-79%: 既存ベース、50%未満: 新規作成

### 2-3. トークン制限チェック

レスポンスに以下の警告が含まれている場合、トークン制限に達している:

```
⚠️ Output size too large - returning metadata and screenshot only
⚠️ Node data omitted due to size constraints
```

または、レスポンスにnodeの詳細情報（styles, layout, text等）が含まれていない場合。

### 2-4. セクション分割対応（トークン制限時）

**🚨 重要: nodeベース実装の徹底**

スクリーンショットのみでのコーディングは禁止:
- クラス名が不正確
- コンポーネント構造が把握できない
- FLOCSS + BEM命名規則に違反する可能性

トークン制限を検出したら、**必ず**ユーザーに以下を依頼:

```
📋 Figmaデザインのトークン数が大きいため、nodeベースの情報取得ができませんでした。

正確なクラス名とコンポーネント構造を把握するため、以下のセクションごとにFigma URLを送付してください:

例:
1. ヘッダーセクション: https://figma.com/design/...?node-id=xxx
2. メインビジュアルセクション: https://figma.com/design/...?node-id=xxx
3. コンテンツセクション: https://figma.com/design/...?node-id=xxx
4. フッターセクション: https://figma.com/design/...?node-id=xxx

各セクションのURLを1つずつ送付していただければ、nodeベースで正確に実装します。
```

**セクションごとにnode情報取得:**
1. 各セクションURLに対して `get_design_context` を実行
2. nodeデータが正しく取得できたか確認
3. クラス名、レイアウト、スタイル情報を記録
4. すべてのセクション情報を統合後、Step 3に進む

### 2-5. デザインシステムルール生成（初回推奨）

**初回実装時は `/create-design-rules` の実行を推奨**

プロジェクトでFigma実装を初めて行う場合、事前にデザインシステムルールを生成しておくと効率的:

```
/create-design-rules
```

**生成されるルール:**
- デザイントークン（色、タイポグラフィ、スペーシング）のSCSS変数マッピング
- コンポーネント命名規則
- レスポンシブ対応パターン

**利点:**
- Step 4-3 のデザイントークン変換が自動化
- 一貫したスタイル定義
- 複数ページ実装時の効率向上

**スキップ条件:**
- 既にデザインシステムルールが存在する場合
- 単発の小規模実装の場合

### 2-6. メモリ効率化（必須）

大規模データ取得時のメモリ管理:

1. **即時永続化**: get_design_context 取得後、直ちにキャッシュファイルに書き出す
2. **変数解放**: 書き出し後、大きなレスポンスオブジェクトは参照を解除
3. **必要部分のみ保持**: 実装に必要なセクションのみを変数に保持

**禁止事項:**
- 複数セクションのレスポンスを同時にメモリに保持
- キャッシュ書き出し前に次の取得を開始

**推奨フロー:**
```
1. セクションA取得
2. キャッシュに書き込み (.claude/cache/figma/{page}/section-a.json)
3. 変数クリア
4. セクションB取得
5. キャッシュに書き込み
6. 変数クリア
...
```

**大規模ページ（10セクション以上）の場合:**
- セクションごとに取得 → 書き込み → 解放を繰り返す
- 全取得完了後、必要な部分のみキャッシュから読み込み

---

## Step 3: ビジュアル参照（スクリーンショット取得）※ オプショナル

> **スキップ条件:** `--no-screenshot` オプション指定時はこのステップ全体をスキップ。
> JSXコードには正確な設計情報が含まれているため、デザイン忠実再現のみが目的の場合は不要。
> トークン節約に推奨。

### 3-1. get_screenshot 実行 (PC)

```
mcp__figma__get_screenshot
  fileKey: "{pc_fileKey}"
  nodeId: "{pc_nodeId}"
  clientLanguages: "php,scss,javascript"
  clientFrameworks: "wordpress"
```

### 3-1b. get_screenshot 実行 (SP) ※ --sp オプション使用時

`--sp` オプションが指定されている場合、SP版のスクリーンショットも取得:

```
mcp__figma__get_screenshot
  fileKey: "{sp_fileKey}"
  nodeId: "{sp_nodeId}"
  clientLanguages: "php,scss,javascript"
  clientFrameworks: "wordpress"
```

**保存先:**
- PC: `.claude/cache/visual-diff/figma_{section}_pc.png`
- SP: `.claude/cache/visual-diff/figma_{section}_sp.png`

**用途:**
- node情報では把握しづらい視覚的要素の確認
- レイアウト・間隔の目視確認
- 最終検証時の比較用
- **PC/SPデュアルモード:** SP検証時のFigma直接比較

**注意:**
- スクリーンショットは補助として使用。実装値は必ずnodeデータから取得
- AIの画像認識はピクセル単位の正確さを把握できない
- JSXコードには正確な設計情報が含まれているため、通常は不要
- 画像URLの断裂などリソース参照に問題がある場合のみ有効

---

## Step 4: アセット準備 + デザイントークン抽出

### 4-1. アセットダウンロード

`get_design_context` のレスポンスに含まれるアセットURLからダウンロード:

```javascript
// レスポンス例
{
  "assets": {
    "image_abc123": "https://figma-assets.com/...",
    "icon_xyz789": "https://figma-assets.com/..."
  }
}
```

**🚨 プレースホルダー禁止:**
- 実際のアセットをダウンロードして配置
- `placeholder.jpg` や仮画像の使用は禁止
- アセットは `themes/{{THEME_NAME}}/assets/images/` に配置

**Figma書き出し規則（2倍サイズ必須）:**
```
Figma表示サイズ → 書き出しサイズ
300px × 200px  → 600px × 400px (@2x)
```

### 4-2. Figma Variables自動取得【推奨】

`mcp__figma__get_variable_defs` を使用してFigmaで定義されたデザイントークンを自動取得:

```
mcp__figma__get_variable_defs
  fileKey: "{fileKey}"
  nodeId: "{nodeId}"
  clientLanguages: "scss"
  clientFrameworks: "wordpress"
```

**取得できるプロパティ:**
- Colors（色）
- Fonts（フォント）
- Sizes（サイズ）
- Spacings（スペーシング）

**出力形式:**
```json
{
  "color/primary": "#d71218",
  "color/accent": "#e60012",
  "spacing/section": "80px",
  "font/heading/h1": "48px"
}
```

**💡 Figma Variablesが空の場合:**
- Figma側でVariablesが定義されていない可能性
- 4-6「Node情報の補完的抽出」にフォールバック

### 4-3. 命名規則マッピング（自動変換）

Figma変数名をSCSS変数名（CSS Custom Properties）に変換:

| Figma変数名 | SCSS変数名 |
|-------------|------------|
| `color/primary` | `--color-primary` |
| `color/text/secondary` | `--color-text-secondary` |
| `spacing/section` | `--spacing-section` |
| `font/heading/h1` | `--font-heading-h1` |
| `fontSize/body` | `--font-size-body` |

**変換ルール:**

1. **スラッシュ → ハイフン**
   ```
   color/primary → color-primary
   ```

2. **camelCase → kebab-case**
   ```
   fontSize → font-size
   lineHeight → line-height
   ```

3. **CSS Custom Properties形式**
   ```
   color-primary → --color-primary
   ```

詳細: `.claude/rules/scss.md` の「Figma Variables連携」セクション参照

### 4-4. 既存変数との差分検出

`src/scss/foundation/_variables.scss` を読み込み、差分を検出:

```
📋 Figma Variables 差分レポート
================================

【新規追加】(5件)
  --color-accent-blue: #0066cc
  --spacing-component: 40px
  ...

【値変更】(2件)
  --color-primary: #d71218 → #e60012
  --spacing-section: 80px → 100px

【既存のみ】(3件) ※削除はしない
  --color-beige: #f6f4ef
  ...

================================
適用しますか？ [Y/n/選択]
```

**ユーザー確認後に適用。強制適用は禁止。**

### 4-5. SCSS出力

確認後、`_variables.scss` に追記または更新:

```scss
// ===== Figma Design Tokens (Auto-generated) =====
// Source: {fileKey} / {nodeId}
// Generated: {timestamp}
// ================================================

:root {
  // Colors
  --color-primary: #d71218;
  --color-accent: #e60012;
  --color-text-primary: #333333;

  // Spacing
  --spacing-section: 80px;
  --spacing-component: 40px;

  // Typography
  --font-size-h1: 48px;
  --font-size-body: 16px;
}
```

**マージ戦略:**
1. 既存の手動定義変数は保持
2. 自動生成セクションは `// ===== Figma Design Tokens` で識別
3. 再実行時は自動生成セクションのみ更新

### 4-6. Node情報の補完的抽出

Figma Variablesでカバーされない値は、`get_design_context` のnode情報から手動抽出:

#### レイアウト（Container & Grid）

nodeの `layoutMode`, `counterAxisSizingMode`, `primaryAxisSizingMode` から抽出:

```
コンテナ:
- 最大幅: 1200px
- 左右余白: 20px

グリッド:
- カラム数: 3カラム（PC） / 1カラム（SP）
- ギャップ: 32px / 16px
- アイテム配置: flex / start / center / space-between
```

#### ボーダー・影・角丸

nodeの `effects`, `cornerRadius`, `strokeWeight` から抽出:

```
角丸:
- ボタン: 8px
- カード: 12px
- 画像: 4px

ボーダー:
- デフォルト: 1px solid #E0E0E0
- 強調: 2px solid #FF6B00

シャドウ:
- カード: 0 2px 8px rgba(0, 0, 0, 0.1)
- ホバー: 0 4px 16px rgba(0, 0, 0, 0.15)
```

**💡 スキルでの一括実行:**

デザイントークン抽出は `/figma-design-tokens-extractor` スキルでも実行可能:

```
/figma-design-tokens-extractor {figma_url}
```

詳細: `.claude/skills/figma-design-tokens-extractor/SKILL.md`

---

## Step 5: プロジェクト規約へ翻訳

### 5-1. ページ情報の取得（自動抽出 + フォールバック）

#### 5-1a. デザインデータからタイトル自動抽出（推奨）

Step 2で取得した `design-context.json` からページタイトルを自動抽出:

**抽出パターン（優先順位順）:**

1. **大きなテキスト要素（h1相当）**
   - fontSize が 24px 以上のテキスト要素
   - ページ最上部に配置されている要素

2. **ページヘッダー内のテキスト**
   - レイヤー名に "header", "title", "heading" を含むフレーム内のテキスト
   - 視覚的に目立つ位置（上部20%以内）

3. **パンくずの末尾テキスト**
   - レイヤー名に "breadcrumb", "パンくず" を含むフレーム内の最後のテキスト

**抽出ロジック:**

```javascript
// 日本語タイトル候補
- 最初に見つかった日本語の大見出しテキスト（ひらがな・カタカナ・漢字を含む）
- 例: 「募集要項一覧」「会社概要」「企業理念」

// 英語タイトル候補
- 英単語パターンマッチ
- 例: "Job Description", "Requirements", "About Us", "Philosophy"

// スラッグ候補
- 英語タイトルをケバブケース化
- 例: "Job Description" → "job-description"
```

**抽出成功時の処理:**

```
✅ ページタイトルを自動抽出しました:
  - スラッグ: job-description
  - 日本語名: 募集要項一覧
  - 英語見出し: Job Description

※ 自動抽出値を使用します。変更が必要な場合はお知らせください。
```

#### 5-1b. フォールバック（抽出失敗時のみ）

デザインデータから抽出できなかった項目のみ、ユーザーに確認:

```
⚠️ 以下の情報を自動抽出できませんでした。入力してください:

- ページスラッグ: [入力]
- ページの日本語名: [入力]
- ページの英語見出し: [入力]
```

**入力例:**
- ページスラッグ: about, service, contact
- ページの日本語名: 会社概要、サービス、お問い合わせ
- ページの英語見出し: About Us, Service, Contact

### 5-2. 自動コンポーネント照合

Figma要素と既存コンポーネントの自動マッチングを行う。

#### 5-2-1. コンポーネントカタログ参照

`.claude/catalogs/component-catalog.yaml` を参照し、自動照合を実行:

**照合ロジック（優先順位順）:**

1. **type 一致** → +40%（button, card, heading 等）
2. **必須props充足** → +30%（Figma要素が必須propsを満たす）
3. **variant対応可能** → +20%（既存variantで対応可能）
4. **figma_patterns一致** → +10%（Figmaコンポーネント名がパターンに一致）

#### 5-2-2. 再利用判定表（自動生成）

照合結果を以下の形式で出力:

| Figma要素 | 既存候補 | スコア | 判定 |
|-----------|----------|--------|------|
| Button/Primary | c-link-button--blue | 90% | 既存使用 |
| Card/Custom | c-article-card | 65% | 既存+カスタム |
| CustomWidget | - | 0% | 新規作成 |

**判定基準:**
- **80%以上** → 既存コンポーネント + Modifier（variant追加等）
- **50-79%** → 既存ベース + カスタムスタイル
- **50%未満** → 新規コンポーネント作成

#### 5-2-3. 新規コンポーネント作成時

新規コンポーネント作成後は、**必ず**以下を実行:

**カタログ更新（必須）:**
`.claude/catalogs/component-catalog.yaml` に新コンポーネントを追加

```yaml
- name: c-{component-name}
  file: template-parts/components/{component-name}.php
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

**詳細ルール:** `.claude/rules/figma-workflow.md` - コンポーネントカタログ維持ルール

### 5-3. Figma Node仕様の構造化

上記の情報を以下のフォーマットで整理し、**必ずastro-component-engineerエージェントに渡す**:

```markdown
## Figma Node仕様（厳守）

### 色定義
[上記の色情報をリスト化]

### タイポグラフィ
[上記のフォント情報をリスト化]

### スペーシング
[上記の余白情報をリスト化]

### レイアウト
[上記のコンテナ・グリッド情報をリスト化]

### ボーダー・影・角丸
[上記の装飾情報をリスト化]

**実装時の厳守事項:**
- すべての数値はこのnode仕様から取得すること
- 推測や独自解釈での数値変更は禁止
- Figma node情報にない装飾の追加は禁止
- 「だいたい合っていればOK」という判断は禁止
- 数値の根拠が不明な場合は実装を止めて質問すること
```

#### 5-3b. PC/SP差分表（--sp オプション使用時）

`--sp` オプションが指定されている場合、PC/SP間の差分を明示した表を生成:

```markdown
## PC/SP 差分仕様

| 要素 | PC | SP | 差分タイプ |
|------|----|----|-----------|
| .p-hero__title | font-size: 48px | font-size: 24px | サイズ変更 |
| .p-hero__container | max-width: 1200px | max-width: 100% | レイアウト変更 |
| .p-cards | display: grid; grid-template-columns: repeat(3, 1fr) | grid-template-columns: 1fr | カラム変更 |
| .p-nav | display: flex | display: none | 表示切替 |
| .p-hero__image | width: 600px | width: 100% | サイズ変更 |

### レスポンシブ実装指針

**PC First + SP Override:**
- 基本値はPCで定義
- `@include sp {}` でSP値をオーバーライド

**SP独自要素:**
- SPのみに存在する要素は `@include sp {}` 内で定義
- PCでは `display: none` を設定
```

**重要:** この差分表により、SP実装が推測ではなくFigma SP仕様に基づくことが保証される。

### 5-4. FLOCSS + BEM命名規則

**🚫 CRITICAL: 必ずケバブケース（kebab-case）を使用**

```scss
// ✅ CORRECT: kebab-case
.p-about__hero { }
.p-about__main-visual { }
.p-about__contact-form { }

// ❌ WRONG: camelCase - NEVER USE
.p-about__mainVisual { }     // ❌ Forbidden
.p-about__heroSection { }    // ❌ Forbidden
.p-about__contactForm { }    // ❌ Forbidden
```

---

## Step 6: ピクセルパーフェクト実装

### 6-1. Astro実装 (astro-component-engineer agent使用)

Task toolでastro-component-engineerを起動:

```markdown
Task tool prompt:
---
以下のFigma Node仕様に基づいて、[ページ名]ページをAstroで実装してください。

## Figma Node仕様（厳守）

[Step 5で構造化した情報を貼り付け]

## ページ情報

- ページスラッグ: [slug]
- ページ日本語名: [日本語名]
- ページ英語見出し: [英語名]

## 既存コンポーネント再利用

[Step 5-2で照合した結果を記載]

## 実装タスク

以下のタスクを実行してください:
---
```

### 6-2. エージェントへの必須タスク

1. Astroページ作成: `astro/src/pages/[slug].astro`
   - BaseLayout使用、bodyClass設定
   - ページ固有CSS/JSをslotで注入
   - FLOCSS + BEM準拠のクラス名（独立Block: `p-[page]-[section]`）

2. セクションコンポーネント作成: `astro/src/components/sections/[slug]/`
   - セクションごとに独立ファイル作成: `Hero.astro`, `Mission.astro`, `Contact.astro` 等
   - 各ファイルにProps interfaceを定義
   - `<ResponsiveImage />` コンポーネントを使用（`<img>` 直接記述禁止）

3. モックデータ作成: `astro/src/data/pages/[slug].json`
   - ACF構造を模倣したJSON
   - `data-helpers.ts` の `getField()`, `getRepeater()` 等で取得

4. SCSS作成:
   - `src/scss/object/project/[slug]/` ディレクトリ作成
   - セクション別SCSSファイル作成 (例: `_p-about-hero.scss`, `_p-about-mission.scss`)
   - `src/css/pages/[slug]/style.scss` エントリーポイント作成

#### 6-2b. PC/SP仕様に基づく実装（--sp オプション使用時）

`--sp` オプションが指定されている場合、Step 5-3bで生成したPC/SP差分表に基づいて実装:

**従来方式（--sp なし）:**
- PC実装後、SP値は推測で `@include sp {}` に記述
- ブレークポイントでの値変更は経験則に依存

**新方式（--sp あり）:**
- PC/SP差分表の値を**そのまま**使用
- SP値は推測ではなくFigma SPデザインから取得した正確な値

```scss
// 例: PC/SP差分表に基づく実装
.p-hero__title {
  font-size: rv(48);    // PC: Figma PC から取得

  @include sp {
    font-size: svw(24); // SP: Figma SP から取得（推測ではない）
  }
}

.p-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);  // PC: Figma PC

  @include sp {
    grid-template-columns: 1fr;  // SP: Figma SP から取得
  }
}
```

**エージェントへの指示追加:**
```markdown
## PC/SP仕様（差分表に基づく）

[Step 5-3bで生成した差分表を貼り付け]

**実装時の注意:**
- SP値は差分表から取得すること（推測禁止）
- 差分表にない要素はPC値のみで実装
- 差分表と異なる値を使用する場合は理由を明記
```

5. **禁止事項の遵守:**
   - `.astro` 内での SCSS/JS インポート禁止
   - `<style>` scoped ブロック禁止
   - `<script>` インライン禁止
   - SCSS/JS は `src/css/` `src/js/` 経由でプリコンパイル

### 6-3. ビルド実行

```bash
npm run astro:build
```

ビルド成功を確認後、開発サーバーを起動:

```bash
npm run astro:dev
```

開発サーバーが起動したら、ユーザーにローカルURL（例: http://localhost:4321/[slug]/）を確認してもらう。

### 6-4. SCSSルール準拠チェック（自動修正ループ）

実装完了後、SCSSルール違反を自動検出・修正:

```bash
npm run lint:css
```

#### チェック項目

| ルール | 内容 | 自動修正 |
|--------|------|----------|
| Container ルール | `*container*` クラスは `@include container()` のみ | ✅ Yes |
| BEM ネスト | `&-` 禁止（`&__` または `&--` を使用） | ✅ Yes |
| FLOCSS 命名 | `p-`, `c-`, `l-`, `u-` プレフィックス | ⚠️ Manual |

#### 自動修正フロー

```
npm run lint:css 実行
       │
       ▼
  違反検出？ ─── No ──→ Step 7 へ進む
       │
      Yes
       │
       ▼
  ┌─────────────────────────────────┐
  │  Container ルール違反の場合:    │
  │  1. __inner クラスを追加        │
  │  2. 禁止プロパティを移動        │
  │  3. Astro テンプレートも更新     │
  └─────────────────────────────────┘
       │
       ▼
  npm run lint:css 再実行
       │
       ▼
  違反 0 件？ ─── No ──→ 最大3回まで繰り返し
       │
      Yes
       │
       ▼
  Step 7 へ進む
```

#### 修正例: Container ルール

**違反:**
```scss
&__container {
  @include container(1200px);
  position: relative;  // ❌ 禁止
  z-index: 1;          // ❌ 禁止
}
```

**修正後:**
```scss
&__container {
  @include container(1200px);
}

&__inner {
  position: relative;
  z-index: 1;
}
```

**Astro テンプレートも更新:**
```astro
<div class="p-section__container">
  <div class="p-section__inner">
    <!-- content -->
  </div>
</div>
```

#### 最大試行回数

- **3回まで**: 自動修正を試行
- **3回超過**: ユーザーに報告し、手動確認を依頼

```
⚠️ SCSSルール違反が3回の修正で解消できませんでした。
残存違反:
- src/scss/xxx.scss: [違反内容]

手動確認が必要です。続行しますか？ [Y/n]
```

---

## Step 7: Figmaとの検証（自動差分検出）

### 7-1. Playwright でページを開く

```
mcp__playwright__browser_navigate
  url: "http://localhost:4321/[slug]/"
```

### 7-2. Figmaメタデータからセクション構造を自動抽出

Step 2で取得した `get_metadata` のXML形式メタデータから、以下を自動実行:

#### 1. トップレベルフレームを全て抽出

検出ロジック:
- ページ直下の大きなフレーム
- 複数の要素を含むグループ化されたフレーム
- 「Section」「セクション」などのキーワードを含むフレーム（優先度高）

#### 2. セクション名を自動推測・正規化

各フレームに対して、**内容を解析してセクション名を提案**:

**推測ロジック（優先順位順）:**

1. **フレーム内のテキストコンテンツから推測**
   ```
   フレーム名: "Frame 123"
   含まれるテキスト: "企業理念", "Philosophy"
   → 推測セクション名: "philosophy"
   ```

2. **フレーム内の画像・要素構成から推測**
   ```
   フレーム名: "Group 456"
   構成: 大きな背景画像 + キャッチコピー + CTAボタン
   → 推測セクション名: "hero"
   ```

3. **フレームの位置・順序から推測**
   ```
   フレーム名: "Frame 789"
   位置: ページ最下部、連絡先情報を含む
   → 推測セクション名: "contact"
   ```

#### 3. ユーザーにセクション命名を確認

自動推測したセクション名を**必ずユーザーに確認**:

```
📋 以下のセクション構造を検出しました。セクション名を確認してください:

1. Figmaフレーム名: "Frame 123"
   検出内容: テキスト「企業理念」を含む
   → 推測セクション名: "philosophy"
   → BEMクラス: .p-about__philosophy
   [OK / 別名を入力]

すべてOKであれば「確定」と入力してください。
```

### 7-3. セクション別スクリーンショット取得（並列実行）

**Figma側:**
```
for each section:
  mcp__figma__get_screenshot
    fileKey: "{fileKey}"
    nodeId: section.figmaNodeId
```
→ 保存先: `.claude/cache/visual-diff/figma_{section}.png`

**Astro側:**
```
for each section:
  mcp__playwright__browser_take_screenshot
    ref: section.astroSelector
    type: "png"
    filename: ".claude/cache/visual-diff/astro_{section}.png"
```

### 7-4. セクション別自動差分検証

**🚨 重要: 自動差分検出を使用**

各セクションについて `visual-diff.js` を実行し、ピクセル単位で差分を検出:

```bash
# 各セクションごとに実行
node scripts/visual-diff.js \
  .claude/cache/visual-diff/figma_{section}.png \
  .claude/cache/visual-diff/astro_{section}.png \
  --preset default \
  --output .claude/cache/visual-diff/diff_{section}.png \
  --json
```

**閾値設定（必須）:**

| プリセット | threshold | maxDiffPixelRatio | 用途 |
|-----------|-----------|-------------------|------|
| strict | 0.1 | 0.01 (1%) | ピクセルパーフェクト重視 |
| default | 0.2 | 0.05 (5%) | 標準（推奨） |
| lenient | 0.3 | 0.10 (10%) | レスポンシブ・フォント差許容 |

**検証結果の解釈:**

```json
{
  "passed": true,
  "statistics": {
    "totalPixels": 1440000,
    "diffPixels": 1200,
    "diffRatio": 0.000833,
    "diffPercentage": 0.0833
  },
  "thresholds": {
    "threshold": 0.2,
    "maxDiffPixelRatio": 0.05,
    "preset": "default"
  },
  "diffImage": ".claude/cache/visual-diff/diff_hero.png"
}
```

- `passed: true` → 検証合格、次のセクションへ
- `passed: false` → 差分画像を確認し、修正が必要

**差分画像:**
- 差分ピクセルはマゼンタ（ピンク）でハイライト
- 差分画像を確認して問題箇所を特定

### 7-5. 差分修正の自動イテレーション

差分が閾値を超過したセクションのみ修正（最大5回まで自動イテレーション）:

```
for each failedSection:
  iteration = 0
  while iteration < 5 and not passed:
    1. 差分画像から問題箇所を特定
    2. astro-component-engineer に修正指示
       - 差分画像パス: .claude/cache/visual-diff/diff_{section}.png
       - 差分統計: diffPixels, diffPercentage
    3. ビルド待機（Vite自動リビルド）
    4. ページリロード
    5. 該当セクションのみ再キャプチャ
    6. visual-diff.js で再検証
    7. iteration++

  if iteration >= 5 and not passed:
    ⚠️ 5回イテレーションで解決できず。人間に報告:
    - 差分画像を提示
    - 残存する差分の詳細を説明
    - 手動確認を依頼
```

### 7-6. レスポンシブ検証（SP）

**PC検証:** デフォルト 1440x900（7-3〜7-5で実施済み）
**SP検証:** 375x812

```
mcp__playwright__browser_resize
  width: 375
  height: 812
```

#### 7-6a. 従来方式（--sp オプションなし）

SP検証は幅変更後のAstroページをキャプチャし、PC用Figmaスクリーンショットと比較:

```bash
# SP用の検証（PCのFigmaを参照）
node scripts/visual-diff.js \
  .claude/cache/visual-diff/figma_{section}_pc.png \
  .claude/cache/visual-diff/astro_{section}_sp.png \
  --preset lenient \
  --output .claude/cache/visual-diff/diff_{section}_sp.png
```

**課題:** PC Figmaとの比較のため、SP固有のデザイン差異を正確に検証できない。

#### 7-6b. Figma SP直接比較（--sp オプション使用時）

`--sp` オプションが指定されている場合、**Figma SPスクリーンショットと直接比較**:

```bash
# SP用の検証（SP用のFigmaを参照）
node scripts/visual-diff.js \
  .claude/cache/visual-diff/figma_{section}_sp.png \
  .claude/cache/visual-diff/astro_{section}_sp.png \
  --preset default \
  --output .claude/cache/visual-diff/diff_{section}_sp.png
```

**メリット:**
- SP固有のレイアウト・サイズ・表示/非表示が正確に検証される
- 推測ではなく実際のFigma SPデザインとの差分を検出
- SP実装の品質が向上

**検証フロー（--sp 使用時）:**
1. Playwright でブラウザ幅を375pxにリサイズ
2. Astro SPページをスクリーンショット
3. Step 3-1bで取得したFigma SPスクリーンショットと比較
4. 差分検出 → 7-5と同様のイテレーション修正

**プリセット推奨:**
| モード | プリセット | 理由 |
|--------|-----------|------|
| --sp なし | lenient | PC Figmaとの比較のため許容度を上げる |
| --sp あり | default | Figma SPとの直接比較のため標準精度で可 |

**注意:** SPはフォントレンダリングの差異が発生しやすいため、差分が大きい場合はフォント起因かレイアウト起因かを確認すること。

### 7-7. 差分検証レポート出力

全セクションの検証完了後、サマリレポートを出力:

```
📊 Visual Diff Report
================================

【PC検証結果】
Section      | Status | Diff%  | Iterations
-------------|--------|--------|------------
hero         | ✅ PASS | 0.08%  | 1
philosophy   | ✅ PASS | 0.12%  | 2
services     | ✅ PASS | 0.03%  | 1
contact      | ⚠️ WARN | 4.50%  | 5 (要確認)

【SP検証結果】
Section      | Status | Diff%  | Iterations
-------------|--------|--------|------------
hero         | ✅ PASS | 1.20%  | 1
philosophy   | ✅ PASS | 2.10%  | 1
services     | ✅ PASS | 0.80%  | 1
contact      | ✅ PASS | 3.20%  | 2

【差分画像】
- .claude/cache/visual-diff/diff_contact.png (要確認)

================================
```

### 7-8. フルページスクリーンショット（最終確認）

全セクションの検証が完了したら、フルページで最終確認:

```
mcp__playwright__browser_take_screenshot
  fullPage: true
  type: "png"
  filename: ".claude/cache/visual-diff/final_fullpage.png"
```

**フルページ差分検証（オプション）:**

```bash
node scripts/visual-diff.js \
  .claude/cache/visual-diff/figma_fullpage.png \
  .claude/cache/visual-diff/final_fullpage.png \
  --preset default
```

### 7-8b. ブラウザリソース解放（必須）

検証完了後、ブラウザインスタンスを明示的に閉じる:

```
mcp__playwright__browser_close
```

**注意:** メモリリーク防止のため、以下のタイミングで必ず実行:
- 各セクション検証完了後（長時間実行時）
- Step 7 全体完了後（必須）
- エラー発生時（finally ブロック相当）

**長時間実行時の推奨:**
- 10セクション以上のページ → 5セクションごとにブラウザを閉じて再起動
- 連続実装（複数ページ） → 各ページ完了後に必ず閉じる

**ブラウザ再起動手順:**
```
1. mcp__playwright__browser_close
2. mcp__playwright__browser_navigate (新規セッション開始)
```

---

## Step 8: 品質チェック

### 8-1. Astro品質チェック（自動実行 - SCRIPT REQUIRED）

**MUST** run quality check script:

```bash
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  {実装したSCSSファイル} \
  {実装したAstroファイル}
```

Example:
```bash
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  src/scss/object/project/_p-about.scss \
  astro/src/pages/about.astro
```

### 8-2. ビルドチェック

```bash
npm run astro:build
```

### 8-3. production-reviewer 実行

Task toolでproduction-reviewerを起動:

レビュー項目:
- コーディング規約遵守（kebab-case等）
- FLOCSS + BEM命名規則
- レスポンシブ対応
- Props interface定義
- ResponsiveImage使用
- `.astro` 内 SCSS/JS インポート禁止

---

## Step 9: トークン効率レポート

実装完了後、トークン使用量のサマリを出力:

### 9-1. レポート出力

```
📊 トークン効率レポート
================================

【キャッシュ利用状況】
- キャッシュ利用: [あり/なし]
- キャッシュファイル: {fileKey}_{nodeId}_{timestamp}.json

【デザインコンテキスト取得】
- 初回取得: [回数] 回
- キャッシュ参照: [回数] 回
- セクション分割: [あり/なし]（[セクション数] セクション）

【推定トークン削減】
- キャッシュ未使用時推定: ~77,000 tokens/取得
- 実際の使用量: ~[実測値] tokens
- 削減率: [X]%

【コンポーネント照合】
- カタログ照合実施: [あり/なし]
- 再利用コンポーネント: [リスト]
- 新規作成コンポーネント: [リスト]

【検証イテレーション】
- 差分修正回数: [回数] 回
- 最終検証結果: [PASS/セクション名]
================================
```

### 9-2. 効率化の振り返り

以下を確認し、次回実装の改善点を特定:

| 項目 | 今回 | 改善案 |
|------|------|--------|
| キャッシュ利用 | - | 24時間以内なら再利用 |
| セクション分割 | - | 大規模ページは事前分割 |
| コンポーネントカタログ | - | 汎用化候補の追加 |
| 既存コンポーネント再利用 | - | 照合精度向上 |

---

## 完了条件

✅ FigmaデザインとAstro実装が一致（ピクセルパーフェクト）
✅ CODING_GUIDELINES.md完全準拠
✅ レスポンシブ動作確認（PC/SP）
✅ production-reviewerのレビュー合格
✅ アセットは全て実ファイル（プレースホルダーなし）
✅ `.astro` 内 SCSS/JS インポートなし
✅ `<ResponsiveImage />` 使用（`<img>` 直接記述なし）

完了後、ユーザーに以下を案内:

1. Astro開発サーバー（localhost:4321）で表示確認
2. 問題なければ承認
3. WordPress変換は `/astro-to-wordpress [slug]` で実行

---

## Step 0.5 詳細: raw_jsx 検証条件

### 検証条件（6項目）

キャッシュファイル `nodes/{nodeId}.json` の `raw_jsx` フィールドが以下を満たすか検証:

| # | 条件 | 理由 |
|---|------|------|
| 1 | 文字列長 >= 500文字 | 省略されていないか |
| 2 | `export default function` を含む | JSXコードか |
| 3 | `return (` を含む | JSX return文があるか |
| 4 | `className=` を含む | Tailwindクラスがあるか |
| 5 | `data-node-id=` を含む | Figmaノード対応があるか |
| 6 | 省略コメントを含まない | 抽象化されていないか |

### 省略コメントパターン（検出対象）

```
- "// Large JSX content"
- "// Section heading"
- "// Cards"
- "// Contains"
- "// Key styles:"
```

### 検証フロー (SCRIPT REQUIRED)

**MUST** run validation script for each cached node:

```bash
for node_file in .claude/cache/figma/{page-slug}/nodes/*.json; do
  node_id=$(basename "$node_file" .json)
  bash .claude/skills/figma-implement/scripts/validate-raw-jsx.sh \
    "$node_file" "$node_id"
done
```

Exit code handling:
- Exit 0 (PASS) → キャッシュを使用
- Exit 1 (FAIL) → get_design_context を直接呼び出し

### 例: 検証失敗

```
⚠️ raw_jsx validation FAILED for 5:2687 (MVV Section):
   - Too short: 423 chars (min: 500)
   - Missing 'export default function'
   - Contains abstraction comment: '// Key styles:'

→ キャッシュは使用せず、get_design_context を直接呼び出します。
```

### 例: 検証成功

```
✅ raw_jsx validated: 5:2687 (12,847 chars)
   - export default function: ✓
   - return statement: ✓
   - className attributes: ✓
   - data-node-id attributes: ✓
   - No abstraction comments: ✓

→ キャッシュからの読み込みを使用します。
```

---

## Step 5 詳細: ページタイトル自動抽出パターン

### 抽出パターン（優先順位順）

| Priority | Pattern | Criteria |
|----------|---------|----------|
| 1 | 大きなテキスト要素（h1相当） | fontSize ≥ 24px かつページ最上部 |
| 2 | ページヘッダー内のテキスト | レイヤー名に "header", "title", "heading" を含む |
| 3 | パンくずの末尾テキスト | レイヤー名に "breadcrumb" or "パンくず" を含む |

### 抽出ロジック

```javascript
// 日本語タイトル
- 最初に見つかった日本語の大見出しテキスト（ひらがな・カタカナ・漢字を含む）
- 例: "募集要項一覧", "会社概要", "企業理念"

// 英語タイトル
- 英単語パターンマッチ
- 例: "Job Description", "Requirements", "About Us", "Philosophy"

// スラッグ
- 英語タイトルをケバブケース化
- 例: "Job Description" → "job-description"
```

### 抽出成功時

```
✅ ページタイトルを自動抽出しました:
  - スラッグ: job-description
  - 日本語名: 募集要項一覧
  - 英語見出し: Job Description

※ 自動抽出値を使用します。変更が必要な場合はお知らせください。
```

### フォールバック（抽出失敗時）

抽出できなかった項目のみユーザーに確認（H3 介入）:

```
⚠️ 以下の情報を自動抽出できませんでした。入力してください:

- ページスラッグ: [入力必須]
- ページの日本語名: [入力必須]
- ページの英語見出し: [入力必須]
```

---

## Step 6 詳細: SCSS実装品質チェックリスト

### コンテナ構造

- [ ] `__container` は `@include container()` のみ
- [ ] レイアウト（display, flex, gap）は `__inner` に分離
- [ ] `__container` 直下に `__inner` がある

### BEM命名

- [ ] 全てのクラスが kebab-case
- [ ] 二重アンダースコアがない（`__heading__en` 禁止）
- [ ] ハイフン区切りで統一（`__hero-container`, `__field-label`）

### プロパティ順序

- [ ] position 系が最初
- [ ] display, flex 系が次
- [ ] サイズ系（width, height, margin, padding）
- [ ] タイポグラフィ系（font, line-height, color）
- [ ] ビジュアル系（background, border）

### Astroコンポーネント禁止事項

- [ ] `.astro` 内での SCSS/JS インポートがない
- [ ] `<style>` scoped ブロックがない
- [ ] `<script>` インラインがない
- [ ] `<img>` 直接記述がない（`<ResponsiveImage />` を使用）
- [ ] Props interface が定義されている

---

## Step 7 詳細: Playwrightによる検証フロー

### 7-1. ページ表示

```
mcp__playwright__browser_navigate
  url: "http://localhost:4321/[slug]/"
```

### 7-2. セクション自動抽出ロジック

**推測ロジック（優先順位順）:**

1. フレーム内のテキストコンテンツから推測
   ```
   フレーム名: "Frame 123"
   含まれるテキスト: "企業理念", "Philosophy"
   → 推測セクション名: "philosophy"
   ```

2. フレーム内の画像・要素構成から推測
   ```
   フレーム名: "Group 456"
   構成: 大きな背景画像 + キャッチコピー + CTAボタン
   → 推測セクション名: "hero"
   ```

3. フレームの位置・順序から推測
   ```
   フレーム名: "Frame 789"
   位置: ページ最下部、連絡先情報を含む
   → 推測セクション名: "contact"
   ```

### 7-3〜7-4. セクション別スクリーンショット + 差分検証

```bash
# Figma側
mcp__figma__get_screenshot (各セクション)
# → .claude/cache/visual-diff/figma_{section}.png

# Astro側
mcp__playwright__browser_take_screenshot (各セクション)
# → .claude/cache/visual-diff/astro_{section}.png

# 差分検証
node scripts/visual-diff.js \
  .claude/cache/visual-diff/figma_{section}.png \
  .claude/cache/visual-diff/astro_{section}.png \
  --preset default \
  --output .claude/cache/visual-diff/diff_{section}.png \
  --json
```

**閾値プリセット:**

| プリセット | threshold | maxDiffPixelRatio | 用途 |
|-----------|-----------|-------------------|------|
| strict | 0.1 | 0.01 (1%) | ピクセルパーフェクト重視 |
| default | 0.2 | 0.05 (5%) | 標準（推奨） |
| lenient | 0.3 | 0.10 (10%) | レスポンシブ・フォント差許容 |

### 7-5. 差分修正イテレーション

```
for each failedSection:
  iteration = 0
  while iteration < 5 and not passed:
    1. 差分画像から問題箇所を特定
    2. astro-component-engineer に修正指示
    3. ビルド待機（Vite自動リビルド）
    4. 該当セクションのみ再キャプチャ
    5. visual-diff.js で再検証
    6. iteration++

  if iteration >= 5 and not passed:
    → H5: 人間に報告（差分画像提示 + 手動確認依頼）
```

### 7-8b. ブラウザリソース解放（必須）

```
mcp__playwright__browser_close
```

**実行タイミング:**
- Step 7 全体完了後（必須）
- 10セクション以上: 5セクションごとに閉じて再起動
- 複数ページ連続実装: 各ページ完了後に必ず閉じる

---

## Step 8 詳細: Quick Quality Check の検出パターン

### 検出パターンと対応

| Pattern | Severity | Fix |
|---------|----------|-----|
| `<img ` (非ResponsiveImage) | **BLOCK** | `<ResponsiveImage />` に変更 |
| `<style` scoped | **BLOCK** | 削除し `src/scss/` に移動 |
| `import.*\.scss` | **BLOCK** | 削除し `src/css/` エントリーに追加 |
| `import.*\.js` | **BLOCK** | 削除し `src/js/` に移動 |
| ビルドエラー | **BLOCK** | エラー内容に基づき修正 |
| Lint警告 | WARN | 次回修正（続行可） |

### 自動実行コマンド

```bash
# スクリプト実行（MUST）
bash .claude/skills/figma-implement/scripts/quality-check.sh \
  {実装したSCSSファイル} \
  {実装したAstroファイル}

# 追加チェック
npm run astro:build
npm run lint:css
grep -rn '<img ' {Astroファイル}
grep -rn '<style' {Astroファイル}
grep -rn 'import.*\.scss' {Astroファイル}
grep -rn 'import.*\.js' {Astroファイル}
```

### エラー時のフロー

```
Step 8 実行
    ↓
エラー検出?
    ├─ YES → 修正を実行 → Step 8 再実行
    └─ NO  → Step 9 へ進む
```
