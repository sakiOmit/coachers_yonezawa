# Changelog: figma-implement

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
