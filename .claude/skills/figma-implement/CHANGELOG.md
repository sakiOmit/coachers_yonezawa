# Changelog: figma-implement

## [3.0.0] - 2026-03-03

### Changed
- **BREAKING**: Astro-first ワークフローに移行
- Step 6: `wordpress-professional-engineer` → `astro-component-engineer` に変更
- Step 7: Playwright URL を `localhost:4321` に変更
- Step 8: PHP パターンチェック → Astro パターンチェック（`<img>`, `<style>` scoped, SCSS/JS インポート）
- Step 9: 完了案内に `/astro-to-wordpress` を追加
- WordPress変換は `/astro-to-wordpress` の範囲に分離

### Added
- `scripts/` ディレクトリ追加（`validate-cache.sh`, `validate-raw-jsx.sh`, `quality-check.sh`）
- Step 0, 0.5, 8 にスクリプト検証を明示的に追加
- `description` にトリガーフレーズ追加
- `references/troubleshooting.md` 追加

---

## [2.3.0] - 2026-02-xx

### Added
- `scripts/` ディレクトリ追加（公式スキルガイド準拠）
- Step 0, 0.5, 8 にスクリプト検証を明示的に追加
- Troubleshooting セクション追加

---

## [2.2.0] - 2026-02-xx

### Added
- Step 0.5: キャッシュ読み込み時の `raw_jsx` 検証
  - 不完全なキャッシュを検出して API 再取得
  - recruit-info/mvv の省略問題を防止
- 省略コメントパターン検出（"// Large JSX content" 等）

---

## [2.1.0] - 2026-01-31

### Changed
- **BREAKING**: Removed `context: fork` from main orchestrator
- **BREAKING**: Removed `agent: general-purpose` from main orchestrator
- Main context now only holds state.yaml (~1.3KB), not design-context.json (76KB)
- Step 6 directly calls wordpress-professional-engineer via Task tool

### Fixed
- Memory leak issue causing WSL crashes on large PC/SP dual implementations
- Design context data (76KB+) no longer held in main context
- Main orchestrator remains lightweight throughout 9-step workflow

### Architecture Change

```
Before (Memory Leak):
  figma-implement (context: fork)
    ├─ Holds design-context.json in memory (76KB) ❌
    └─ Task → wordpress-professional-engineer (fork)
        └─ Double fork + large data ❌

After (Memory Optimized):
  figma-implement (no fork)
    ├─ Only state.yaml in memory (1.3KB) ✅
    ├─ design-context.json read from file as needed ✅
    └─ Task → wordpress-professional-engineer (fork)
        └─ Single fork, lightweight main ✅
```

### Migration Guide

**No user-facing changes required.**

Usage remains the same:
```bash
/figma-implement {pc_url} [--sp {sp_url}]
```

---

## [2.0.0] - 2026-01-31

### Changed
- **BREAKING**: Moved Phase 0 (prefetch) to `/figma-prefetch` skill
- Prerequisites check now requires `/figma-prefetch` completion

---

## [1.0.0] - 2026-01-30

### Added
- Initial release
- 9-step workflow orchestration
- State persistence and resume capability
- PC/SP dual implementation support
- Design token extraction
- Visual validation with Playwright
