---
name: astro-page-generator
description: "Generate Astro page with section components, mock data, and SCSS wiring interactively"
argument-hint: "[page-slug]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
model: opus
context: fork
agent: general-purpose
---

# Astro Page Generator

## Dynamic Context

```
Existing Astro pages:
!`ls astro/src/pages/*.astro 2>/dev/null || echo "No pages yet"`
```

## Overview

Astro静的コーディング環境で新規ページを対話的に生成する。
ページ名、セクション構成、データ構造を収集し、Astroページ・セクションコンポーネント・モックデータJSON・SCSS接続を一括生成する。

## Pipeline Position

| Position | Skill |
|----------|-------|
| **前工程** | `/figma-analyze`（任意） |
| **後工程** | `/figma-implement`, `/astro-to-wordpress` |
| **呼び出し元** | ユーザー直接 |
| **呼び出し先** | なし |

## Usage

```
/astro-page-generator
```

## Input Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| (interactive) | Yes | ページ名（日本語） |
| (interactive) | Yes | ページスラッグ（kebab-case） |
| (interactive) | Yes | セクション一覧（カンマ区切り） |
| (interactive) | No | 既存WordPress PHPテンプレートパス（あれば参照） |

## Output

### Generated Files

**Astroページ:**
- `astro/src/pages/{slug}.astro`

**セクションコンポーネント:**
- `astro/src/components/sections/{slug}/{Section}.astro` (各セクション)

**モックデータ:**
- `astro/src/data/pages/{slug}.json`

**SCSS（既存なければ）:**
- `src/scss/object/projects/{slug}/` ディレクトリ
- `_p-{slug}.scss` + 各セクションファイル
- `src/css/pages/{slug}/style.scss` エントリーポイント

### Updated Files

- `vite.config.js` — エントリー追加（SCSSが新規の場合のみ）

## Processing Flow

```
1. 情報収集（対話）
   ├─ ページ名（日本語）
   ├─ ページスラッグ（kebab-case）
   ├─ セクション一覧
   └─ 既存PHPテンプレートの有無

2. 既存パターン確認
   ├─ 同名SCSSファイルの存在チェック
   ├─ 同名PHPテンプレートの参照（あれば構造を踏襲）
   └─ 既存共通コンポーネントの確認

3. ファイル生成
   ├─ モックデータJSON（ACF構造を模倣）
   ├─ セクションコンポーネント（Props interface付き）
   ├─ ページファイル（BaseLayout + import + sections）
   └─ SCSS構造（既存なければ新規作成）

4. ビルド設定更新
   └─ vite.config.js エントリー追加（SCSSが新規の場合）

5. 検証
   ├─ npm run astro:build
   └─ 生成ファイル一覧と変換先の対応表出力
```

## Generation Rules (Mandatory)

Page/Section/Data テンプレートと命名規則は references に定義。

**詳細**: → [references/generation-templates.md](references/generation-templates.md)（テンプレート + Naming Rules + 実装例）

## Error Handling

| Error | Detection | Response |
|-------|-----------|----------|
| Slug duplicate | ファイル存在チェック | 確認してから上書きまたは別名提案 |
| SCSS already exists | Glob 検索 | 既存SCSSを再利用、エントリーポイントのみ接続 |
| Invalid kebab-case | 正規表現 `/^[a-z][a-z0-9-]*$/` | バリデーションして修正提案 |
| astro/package.json 不在 | File not found | `npm run astro:install` の実行を案内 |
| `npm run astro:build` 失敗 (import error) | exit code != 0 + "Cannot find module" | インポートパスを確認、`@root-src` alias の存在を検証 |
| `npm run astro:build` 失敗 (type error) | exit code != 0 + "Type error" | Props interface を確認、型不一致を修正 |
| `npm run astro:build` 失敗 (SCSS compile) | exit code != 0 + "SassError" | SCSS 構文を確認、`@use` パスの正当性を検証 |
| BaseLayout.astro 不在 | File not found | layouts/ ディレクトリの確認を促す |

## Related Files

| File | Purpose |
|------|---------|
| `.claude/rules/astro.md` | Astroワークフロー規約 |
| `.claude/rules/scss.md` | SCSS/BEM命名規約 |
| `astro/src/layouts/BaseLayout.astro` | 共通レイアウト |
| `astro/src/lib/data-helpers.ts` | データヘルパー |
| `astro/src/components/common/` | 共通コンポーネント |

---

**Instructions for Claude:**

## 引数パース

`$ARGUMENTS` を以下のルールでパースする:

1. **引数あり** (`{page-slug}`): 非対話モードで直接生成を開始
   - `--sections s1,s2,s3` オプション: セクション一覧をカンマ区切りで指定
   - 例: `/astro-page-generator about --sections hero,mission,team`
2. **引数なし**: 対話モード（従来通りユーザーに質問）

## 実行手順

1. **ファイル存在確認**
   - `astro/package.json` が存在するか確認
   - 存在しない場合: 「Astro環境が未セットアップです。`npm run astro:install` を実行してください」と案内して終了
   - 同名ページ `astro/src/pages/{slug}.astro` が存在する場合: 上書き確認

2. **セクション確定**
   - 引数に `--sections` あり → カンマ区切りでパース
   - 引数に `--sections` なし → 対話で収集（非対話モードでも）
   - 各セクション名を kebab-case でバリデーション

3. **生成実行**
   - Processing Flow のステップ1-5に従ってファイルを生成
   - `scripts/generate-astro-page.sh` が利用可能であれば先行実行
   - スクリプトが利用できない場合は直接 Write/Edit で生成

4. **検証**
   - `npm run astro:build` を実行してビルド成功を確認
   - 生成ファイル一覧と WordPress 変換先の対応表を出力

## Scripts

スクリプト標準規約: [scripts-standard.md](../scripts-standard.md)

| スクリプト | 目的 | 入力 | 出力 |
|-----------|------|------|------|
| `scripts/generate-astro-page.sh` | テンプレートベースの Astro ページ足場生成 | slug, sections | .astro + .json + .scss files |

### generate-astro-page.sh

```bash
bash .claude/skills/astro-page-generator/scripts/generate-astro-page.sh <page-slug> <sections>
# Example:
bash .claude/skills/astro-page-generator/scripts/generate-astro-page.sh about hero,mission,team
```

- **入力**: page-slug (kebab-case), sections (カンマ区切り)
- **出力**: Astro ページ, セクションコンポーネント, モックデータ JSON, SCSS 構造
- **生成ファイル**:
  - `astro/src/pages/{slug}.astro` - ページファイル
  - `astro/src/components/sections/{slug}/{Pascal}.astro` - セクションコンポーネント
  - `astro/src/data/pages/{slug}.json` - モックデータ
  - `src/scss/object/project/{slug}/` - SCSS ファイル群
  - `src/css/pages/{slug}/style.scss` - CSS エントリーポイント
- **前提**: `astro/package.json` が存在すること
- **終了コード**: 0=成功, 1=バリデーションエラー

## Agent Integration

Step 3（ファイル生成）が複雑な場合、astro-component-engineer エージェントに委譲可能:

```
Task tool:
  subagent_type: astro-component-engineer
  prompt: |
    以下の仕様で Astro ページを生成してください:
    - slug: {slug}
    - sections: {sections}
    - データ構造: {data_structure}

    生成ルール: references/generation-templates.md を参照。
    SCSS は src/scss/object/project/{slug}/ に配置。
    npm run astro:build で検証してください。
```

**委譲条件**: セクション数 >= 5 またはモックデータが複雑な場合
**Fallback**: エージェント不在時は直接 Write/Edit で生成

## Related Skills

| Skill | Purpose |
|-------|---------|
| `wordpress-page-generator` | WordPress PHP版ページ生成 |
| `astro-to-wordpress` | Astro→WordPress変換 |
| `scss-component-generator` | SCSSコンポーネント追加 |

---

**Version**: 1.0.0
**Created**: 2026-02-18
