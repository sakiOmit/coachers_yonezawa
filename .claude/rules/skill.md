---
globs: [".claude/skills/**"]
---

# Skill Rules

## Overview

このルールファイルは、Claude Code スキルの作成・管理に関する規約を定義します。
公式 SKILL.md 形式への準拠を保証し、チーム開発での一貫性を確保します。

## スキル形式規約

新規スキルは必ず公式 SKILL.md 形式で作成する。

### 必須構造

```
.claude/skills/{skill-name}/
└── SKILL.md           # 必須
```

### YAML Frontmatter 必須フィールド

| フィールド | 必須 | 説明 |
|-----------|------|------|
| name | ✅ | スキル名（kebab-case） |
| description | ✅ | 1文の説明（Claude自動呼び出し判断用） |
| allowed-tools | ✅ | 使用可能ツール一覧 |
| context | 推奨 | `fork`（サブエージェント実行） |
| agent | 推奨 | `general-purpose`, `Explore`, `Plan` |

### SKILL.md テンプレート

```yaml
---
name: skill-name
description: "1文の説明"
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
context: fork
agent: general-purpose
---

# Skill Name

## Overview
...

## Usage
/skill-name [args]

## Input Parameters
| Parameter | Required | Description |

## Processing Flow
...

## Error Handling
| Error | Response |
```

## 禁止事項

| 禁止 | 理由 |
|------|------|
| skill.json + instructions.md 形式 | 旧形式（非推奨） |
| 設計書形式での新規作成 | 二度手間 |

## マイグレーション完了後の削除（必須）

SKILL.md 形式への移行が完了したスキルは、旧形式ファイルを**必ず削除**すること。

### 削除対象
- `skill.json`
- `instructions.md`

### 確認方法
```bash
# 旧形式ファイルの検出
find .claude/skills -name "skill.json" -o -name "instructions.md"
```

### 理由
- 旧形式と新形式の混在は保守性を低下させる
- SKILL.md に統一することで一貫性を確保

## サブエージェントでのスキルプリロード

```yaml
# .claude/agents/*.md のフロントマター
skills:
  - figma-page-analyzer
  - figma-recursive-splitter
```

## スキル保存場所

| 場所 | パス | 適用対象 |
|------|------|---------|
| Personal | ~/.claude/skills/<skill-name>/SKILL.md | 全プロジェクト |
| Project | .claude/skills/<skill-name>/SKILL.md | このプロジェクトのみ |

## チェックリスト

- [ ] SKILL.md 形式で作成
- [ ] name は kebab-case
- [ ] description は1文で明確
- [ ] allowed-tools を適切に設定
- [ ] context: fork を設定（推奨）
