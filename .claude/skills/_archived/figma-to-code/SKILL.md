---
name: figma-to-code
description: "Figma design to WordPress theme coding workflow with visual review iteration."
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
  - Task
  - mcp__figma__get_design_context
  - mcp__figma__get_metadata
  - mcp__figma__get_screenshot
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_take_screenshot
context: fork
agent: general-purpose
---

# Figma to Code Workflow

FigmaデザインからWordPressテーマのコーディング、そしてビジュアルレビューまでを自動化する。

## Usage

```
/figma-to-code
```

実行後、以下を入力:
- Figma URL
- ページスラッグ（例: about, contact）
- ページの日本語名（例: 会社概要、お問い合わせ）

## Processing Flow

1. **Figma解析**
   - デザインコンテキストを取得
   - コンポーネント構造を理解
   - スタイル情報を抽出

2. **WordPress実装** (wordpress-professional-engineer)
   - CODING_GUIDELINES.mdに従ってコーディング
   - ページテンプレート作成 (pages/page-*.php)
   - SCSS作成 (FLOCSS + BEM)
   - vite.config.jsにエントリー追加
   - template-partsの作成（必要に応じて）

3. **ビルド & 開発サーバー起動**
   - `npm run dev`を実行
   - ローカル環境でページを確認可能にする

4. **ビジュアル検証** (Playwright)
   - 実装したページのスクリーンショット取得
   - Figmaデザインと比較
   - 差分があれば修正点を特定

5. **修正イテレーション**
   - 差分に基づいてコード修正
   - 再度スクリーンショット取得
   - デザインと一致するまで繰り返し

6. **最終レビュー** (production-reviewer)
   - コーディング規約遵守チェック
   - アクセシビリティチェック
   - パフォーマンスチェック

## Prerequisites

- Docker環境が起動していること (`docker compose up -d`)
- Figma URLがDev Modeでアクセス可能であること
- 初回実装後、WordPressで固定ページを作成しテンプレートを選択

## Error Handling

| Error | Response |
|-------|----------|
| Figma token limit exceeded | セクション分割取得に切り替え |
| Docker not running | `docker compose up -d` を案内 |
| Build error | エラーログを分析して修正 |

## Related Skills

- `/figma-implement` - Figma → WordPress完全実装（本番用）
- `/code-connect` - Code Connect連携
- `/create-design-rules` - デザインシステムルール生成
