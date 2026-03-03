# Figma Cache Validator Agent

## Overview

Figma実装前のキャッシュ確認を強制するサブエージェント。
figma-implement スキルから Task ツールで呼び出され、キャッシュ確認が完了するまで次ステップに進めない。

## Role

- キャッシュディレクトリの存在確認
- キャッシュ有効期限（24時間）の検証
- 利用/新規取得の判断と報告

## Trigger

figma-implement スキルの Step 0 で自動的に Task ツール経由で起動される。

## Processing Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. キャッシュディレクトリ確認       │
│    ls -la .claude/cache/figma/      │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 2. 対象ページのキャッシュ存在確認   │
│    - metadata.json                  │
│    - design-context.json            │
│    - prefetch-info.yaml             │
└─────────────────────────────────────┘
  │
  ├─ 存在する場合
  │    │
  │    ▼
  │  ┌─────────────────────────────────┐
  │  │ 3a. 有効期限確認（24時間）      │
  │  │     stat -c %Y {cache_file}     │
  │  └─────────────────────────────────┘
  │    │
  │    ├─ 有効 → CACHE_VALID
  │    └─ 期限切れ → CACHE_EXPIRED
  │
  └─ 存在しない場合
       │
       ▼
     CACHE_NOT_FOUND
```

## Output Format

キャッシュ確認結果を構造化して返却する:

```yaml
cache_validation:
  status: CACHE_VALID | CACHE_EXPIRED | CACHE_NOT_FOUND
  page_slug: "{page-name}"
  cache_path: ".claude/cache/figma/{page-name}/"
  files_found:
    metadata: true | false
    design_context: true | false
    prefetch_info: true | false
  cache_age_hours: 12.5
  recommendation: USE_CACHE | RUN_PREFETCH | RUN_RECURSIVE_SPLITTER
  next_command: "/figma-prefetch {url}" | "Read cache files" | null
```

## Status Definitions

| Status | Meaning | Recommendation |
|--------|---------|----------------|
| CACHE_VALID | 24時間以内のキャッシュあり | USE_CACHE（Read ツールで読み込み） |
| CACHE_EXPIRED | キャッシュあるが24時間超過 | RUN_PREFETCH（再取得推奨） |
| CACHE_NOT_FOUND | キャッシュなし | RUN_PREFETCH（新規取得必須） |

## Required Tools

- Bash（ls, stat）
- Read（キャッシュ内容確認）
- Glob（ファイル検索）

## Integration with figma-implement

figma-implement は以下のように呼び出す:

```
Task ツール:
  subagent_type: figma-cache-validator
  prompt: |
    ページ "{page-name}" のFigmaキャッシュを検証してください。
    URL: {figma_url}
  run_in_background: false  # ブロッキング必須
```

**結果が CACHE_VALID 以外の場合:**
- figma-implement は次ステップに進まず、推奨コマンドを実行するよう指示

## Example Execution

### Case 1: キャッシュ有効

```
入力: ページ "environment" のキャッシュ検証

出力:
cache_validation:
  status: CACHE_VALID
  page_slug: "environment"
  cache_path: ".claude/cache/figma/environment/"
  files_found:
    metadata: true
    design_context: true
    prefetch_info: true
  cache_age_hours: 8.2
  recommendation: USE_CACHE
  next_command: null

→ figma-implement は Step 1 に進む
```

### Case 2: キャッシュなし

```
入力: ページ "company" のキャッシュ検証

出力:
cache_validation:
  status: CACHE_NOT_FOUND
  page_slug: "company"
  cache_path: ".claude/cache/figma/company/"
  files_found:
    metadata: false
    design_context: false
    prefetch_info: false
  cache_age_hours: null
  recommendation: RUN_PREFETCH
  next_command: "/figma-prefetch {url}"

→ figma-implement は停止し、ユーザーに prefetch 実行を指示
```

---

**Version**: 1.0.0
**Created**: 2026-02-01
