# Claude Code カスタムコマンド

全コマンドは `.claude/skills/*/SKILL.md` 形式に移行済み。

## スキル一覧

`/skill-name` で実行可能。詳細は各 `.claude/skills/{name}/SKILL.md` を参照。

### Figma ワークフロー
| スキル | 説明 |
|--------|------|
| `/figma-implement` | Figma → WordPress完全実装（メインワークフロー） |
| `/figma-to-code` | Figma → 静的コード生成（調査用） |
| `/figma-design-diff-checker` | Figmaデザインと実装の視覚差分検証 |
| `/figma-implementation-verifier` | Figma実装の第三者検証 |
| `/figma-implement-orchestrator` | 大規模ページ実装のオーケストレーター |
| `/figma-variables-to-scss` | Figma Variables → SCSS変数変換 |
| `/figma-page-analyzer` | ページ規模事前分析 |
| `/figma-recursive-splitter` | 大規模ページBFS分割 |
| `/figma-section-splitter` | セクション分割並列実装 |
| `/figma-component-analyzer` | 共通コンポーネント自動検出 |
| `/figma-text-extractor` | テキストコンテンツ抽出 |
| `/figma-visual-diff-runner` | Playwright + pixelmatch検証 |
| `/figma-design-tokens-extractor` | デザイントークン抽出 |
| `/figma-container-width-calculator` | コンテナ幅算出 |
| `/figma-url-parser` | Figma URL → fileKey/nodeId変換 |
| `/figma-prefetch` | Figmaデータ事前取得 |
| `/figma-workflow-validator` | ワークフロー準拠チェック |
| `/figma-form-generator` | フォーム → SCSS + CF7 |
| `/code-connect` | Code Connect連携 |
| `/create-design-rules` | デザインシステムルール生成 |

### コード生成
| スキル | 説明 |
|--------|------|
| `/wordpress-page-generator` | WordPressページテンプレート生成 |
| `/astro-page-generator` | Astroページ対話的生成 |
| `/astro-to-wordpress` | Astro → WordPress PHP変換 |
| `/scss-component-generator` | FLOCSS準拠SCSSコンポーネント生成 |
| `/scss-naming-normalizer` | Figmaレイヤー名 → kebab-case変換 |
| `/acf-field-generator` | ACFフィールドグループ生成 |
| `/acf-admin-ui` | ACF管理画面UI最適化 |
| `/create-importer` | YAML + PHPインポート機能生成 |
| `/favicon-generator` | ファビコン一式生成 |
| `/plugin-scaffold` | Claude Codeプラグイン雛形 |

### レビュー・品質
| スキル | 説明 |
|--------|------|
| `/review` | 全コードレビュー（SCSS + JS + PHP） |
| `/fix` | レビュー指摘の自動修正 |
| `/qa` | QA統合チェック・修正 |
| `/delivery` | 納品品質チェック |
| `/implementation-quality-validator` | BEM/container/ACF品質検証 |
| `/component-integration-detector` | 計画vs実装差分検出 |
| `/comment-cleaner` | 冗長コメント検出・削除 |
| `/typo-checker` | 日本語誤字脱字チェック |
| `/seo-check` | SEO品質チェック |
| `/review-format-spec` | レビュー結果フォーマット仕様 |

### プロジェクト管理
| スキル | 説明 |
|--------|------|
| `/analyze-project` | プロジェクト分析 |
| `/architecture-review` | アーキテクチャレビュー |
| `/suggest-rules` | ルール改善提案 |
| `/reflect` | 自動振り返りと改善実行 |
| `/learn` | 知見の手動記録 |
| `/next` | 次のステップ自動案内 |
| `/usage-analyzer` | スキル使用統計分析 |

### ユーティリティ
| スキル | 説明 |
|--------|------|
| `/skill-generator` | 新規スキル雛形生成 |
| `/skill-format-converter` | 旧形式 → SKILL.md変換 |
| `/skill-yaml-validator` | SKILL.md YAML検証 |
| `/placeholder-detector` | プレースホルダー形式検出 |
| `/directory-structure-analyzer` | ディレクトリ構造分析 |
| `/docs-sync-checker` | ドキュメント同期チェック |
| `/claude-directory-cleaner` | .claude不要ファイル削除 |
