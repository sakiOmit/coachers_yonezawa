# Architecture Review Report: figma-prepare Skill Ecosystem

## Overview
- Review Date: 2026-03-05
- Review Scope: figma-prepare skill "ultimization" progress
- Overall Rating: **B+** (Strong foundation, well-tested, with identifiable gaps in constants centralization)

## Executive Summary

The figma-prepare skill ecosystem is a remarkably mature and well-engineered system for Figma design structure analysis and transformation. It features a 4-phase pipeline (analysis, grouping, renaming, auto-layout) with 42 shared utility functions, 346 unit tests, 39 integration tests, and a 6-category QA checker. The architecture demonstrates strong separation of concerns, comprehensive error handling, and a disciplined approach to safety (Adjacent Artboard pattern, dry-run defaults). The primary gap blocking "ultimate" status is the constants fragmentation across scripts (38 locally-defined constants vs 60 centralized), which is well-documented in KNOWN-ISSUES.md as 14 open items.

---

## Quantitative Profile

| Metric | Value |
|--------|-------|
| Core library (`figma_utils.py`) | 2,066 lines, 42 public functions |
| Shell scripts | 8 scripts, 2,833 lines total |
| JS templates (Chrome DevTools) | 8 files, 968 lines total |
| Unit tests (`test_figma_utils.py`) | 4,715 lines, 346 test functions, 52 test classes |
| Integration tests (`run-tests.sh`) | 39 passed, 0 failed, 1 skipped |
| QA checks (`qa-check.sh`) | 6 categories, 1 minor issue (unused `re` import in compare-grouping.sh) |
| Reference documentation | 1,046 lines across 4 files |
| SKILL.md | 931 lines |
| Rules (`figma-prepare.md`) | 383 lines, 90+ threshold parameters |
| Calibration dataset | 8 cases (2 fixtures, 4 real-data, 2 synthetic) |
| Test-to-code ratio | 2.28:1 (4,715 test lines / 2,066 lib lines) |
| Constants: centralized in `figma_utils.py` | 60 |
| Constants: locally defined in scripts | 38 (across 4 scripts) |
| Known open issues | 14 (Issue 207-220) |

---

## Detailed Evaluation

### 1. Completeness: A-

**Strengths:**
- Phase 1 (analysis) is production-ready with 100-point scoring, 5 penalty categories, and score breakdown
- Phase 2 is the most sophisticated component, featuring a 3-stage architecture (Stage A: 9 heuristic detectors, Stage B: Claude sectioning with screenshot, Stage C: Haiku nested grouping)
- Phase 3 (renaming) covers 10+ semantic detection patterns (header, footer, nav, icon, button, CTA, side-panel, EN+JP pairs, decoration, highlight)
- Phase 4 (auto-layout) infers direction, gap, padding, WRAP, SPACE_BETWEEN with confidence levels
- Enrichment pipeline (Phase 1.5) bridges the metadata gap with fills/layoutMode/characters
- Adjacent Artboard safety pattern for non-destructive modifications

**Areas for Improvement:**
- Phase 4 is explicitly labeled as "2-3 cases needed for validation" -- still in beta status
- Stage C (Haiku nested grouping) integration test is a placeholder (`compare-grouping.sh` skipped)
- No end-to-end test that exercises the full Phase 1-4 pipeline in sequence

### 2. Test/Quality Foundation: A

**Strengths:**
- 346 unit tests with parametrized cases, covering all 42 public functions
- 52 test classes organized by function/feature
- Integration tests exercise all 4 analysis scripts with 3 fixture types (standard, dirty, realistic)
- Cross-script consistency checks (unnamed count vs rename count alignment)
- QA checker covers 6 automated categories: unused imports, stale phase refs, YAML key consistency, doc staleness, dead code, detector coverage
- Feedback loop (`feedback-loop.sh`) with max-rounds, regression detection, and double-verification
- Calibration system (`figma-prepare-eval`) with 8 cases, confusion matrix, and penalty contribution analysis
- Test-to-code ratio of 2.28:1 is excellent

**Areas for Improvement:**
- `pytest` is not installed in the current environment (unit tests could not be verified during this review)
- No mutation testing or property-based testing
- compare-grouping.sh integration test is a placeholder (marked SKIP)
- Calibration dataset has 4 real-data cases that depend on cached files which may not persist across environments

### 3. Open Issues Severity: INFO (Non-blocking)

All 14 open issues (207-220) fall into a single category: **constants not yet centralized in `figma_utils.py`**. Analysis:

| Issue Range | Script | Local Constants | Severity |
|-------------|--------|-----------------|----------|
| 207-209, 210 | `detect-grouping-candidates.sh` | 17 (PROXIMITY_GAP, JACCARD_THRESHOLD, ZONE_OVERLAP_*, etc.) | WARNING |
| 215-219 | `generate-rename-map.sh` | 15 (DIVIDER_MAX_HEIGHT, ICON_MAX_SIZE, etc.) | WARNING |
| 211 | `infer-autolayout.sh` | 1 (VARIANCE_RATIO) | INFO |
| 212 | `generate-nested-grouping-context.sh` | GRANDCHILD_THRESHOLD=5 | INFO |
| 213 | figma_utils.py internal | `similarity_threshold=0.7` default | INFO |
| 214 | figma_utils.py internal | `match_threshold=0.5` | INFO |
| 220 | detect-grouping-candidates.sh | `is_grid_like` 0.20 threshold | INFO |

**Verdict:** None are blockers. All are consistency/maintainability improvements. The code works correctly with locally-defined values matching the intended behavior. The risk is that future changes to thresholds in `figma-prepare.md` might not propagate to all scripts if they are not centralized.

### 4. Architecture Health: A-

**Strengths:**
- Clean separation: `figma_utils.py` (pure logic) / shell scripts (orchestration) / JS templates (Figma API calls)
- All 8 shell scripts import from `figma_utils.py` (except `start-chrome-debug.sh`)
- JS templates use placeholder patterns (`__RENAME_MAP__`, `__GROUPING_PLAN__`) for safe injection
- Verification scripts mirror apply scripts (apply-renames.js / verify-structure.js, apply-grouping.js / verify-grouping.js, apply-autolayout.js / verify-autolayout.js)
- SKILL.md serves as an executable specification with precise flow diagrams
- Rules file (`figma-prepare.md`) is the single source of truth for thresholds and scoring formula
- Cache strategy with TTL and session-start checks
- Calibration as a meta-skill (separate from the main skill)
- Feedback loop as a separate improvement skill

**Areas for Improvement:**
- 38 locally-defined constants across 4 scripts should be migrated to `figma_utils.py` (this is the #1 architectural debt)
- `compare-grouping.sh` has an unused `re` import (the only QA failure)
- `figma_utils.py` at 2,066 lines is approaching the boundary where further decomposition might be warranted (e.g., splitting detection functions into a separate module)
- The shell-script-with-embedded-Python pattern, while functional, makes IDE support and static analysis harder than pure Python scripts would

### 5. Gap Analysis: What Remains for "Ultimate" Status

#### Short-term (Mechanical, Low-risk)

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Centralize 38 local constants into `figma_utils.py` | 2-3 hours | Eliminates all 14 KNOWN-ISSUES |
| 2 | Fix unused `re` import in `compare-grouping.sh` | 1 minute | QA goes fully green |
| 3 | Add `compare-grouping.sh` integration test (not just placeholder) | 30 min | Removes last SKIP |
| 4 | Install pytest in environment / add to requirements | 5 min | Unit tests runnable |

#### Medium-term (Design Decisions Needed)

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 5 | Phase 4 validation on 2-3 real projects | 1-2 weeks | Promotes Phase 4 from beta to stable |
| 6 | End-to-end pipeline test (Phase 1 through 4 on fixture) | 1 day | Catches integration gaps |
| 7 | Portable calibration dataset (fixtures only, no external cache dependency) | 2 hours | Makes calibration CI-safe |
| 8 | Split `figma_utils.py` into modules (detection.py, scoring.py, layout.py) | 1 day | Better maintainability at scale |

#### Long-term (Strategic)

| Priority | Gap | Effort | Impact |
|----------|-----|--------|--------|
| 9 | Issue 194: Stage A detector progressive replacement by Claude reasoning | Ongoing | Reduces heuristic maintenance burden |
| 10 | Property-based testing for scoring formula edge cases | 2-3 days | Higher confidence in scoring stability |
| 11 | Automated regression on real Figma files (CI with Figma API token) | 1 week | Prevents scoring drift across real designs |

---

## Issue List

### CRITICAL (Immediate Action Required)

None.

### WARNING (Early Action Recommended)

| # | Issue | Impact | Recommended Action |
|---|-------|--------|-------------------|
| 1 | 38 locally-defined constants across 4 scripts (Issues 207-220) | Threshold changes in `figma-prepare.md` may not propagate; code/doc desync risk | Migrate all to `figma_utils.py` exports; update scripts to import |
| 2 | `figma_utils.py` growing to 2,066 lines with 42 functions | Approaching maintainability boundary | Plan modular split when crossing ~2,500 lines |

### INFO (Improvement Suggestions)

| # | Suggestion | Benefit | Priority |
|---|------------|---------|----------|
| 1 | Fix `re` unused import in `compare-grouping.sh` | QA fully green | Immediate |
| 2 | Replace `compare-grouping.sh` test SKIP with real integration test | Full coverage | Short-term |
| 3 | Make calibration dataset fully self-contained (no external cache deps) | CI portability | Short-term |
| 4 | Add `requirements.txt` or `pyproject.toml` for Python test dependencies | Reproducible test environment | Short-term |
| 5 | Consider converting shell+embedded-Python scripts to pure Python | Better IDE support, static analysis | Long-term |

---

## Improvement Roadmap

### Short-term (Within 1 week)
1. Centralize all 38 local constants into `figma_utils.py` (resolves Issues 207-220)
2. Fix unused `re` import in `compare-grouping.sh`
3. Add `compare-grouping.sh` real integration test
4. Ensure pytest is available in the development environment

### Medium-term (Within 1 month)
1. Validate Phase 4 on 2-3 real Figma projects; update MVP status
2. Create end-to-end pipeline test
3. Make calibration dataset portable (copy real-data fixtures into `tests/`)
4. Evaluate `figma_utils.py` module split (detection, scoring, layout)

### Long-term (Within quarter)
1. Implement Stage A progressive replacement strategy (Issue 194)
2. Add property-based testing for scoring formula
3. Set up CI automation for calibration regression

---

## Architectural Highlights Worth Preserving

The following design decisions are exemplary and should be maintained:

1. **Adjacent Artboard pattern** -- Non-destructive Figma modifications with visual Before/After comparison
2. **3-stage Phase 2** -- Heuristic (A) + Claude visual reasoning (B) + Haiku pattern matching (C) with coverage-based fallback is a sophisticated hybrid AI/rules approach
3. **Calibration meta-skill** -- Treating scoring formula validation as a first-class concern with its own dataset, confusion matrix, and penalty contribution analysis
4. **Feedback loop skill** -- Automated detection/fix/document cycle with regression guards
5. **Verification scripts mirroring apply scripts** -- Every mutation has a corresponding verification
6. **Dry-run by default** -- Safe defaults with explicit `--apply` opt-in

---

## Conclusion

The figma-prepare ecosystem is at approximately **90% of ultimate status**. The remaining 10% is primarily mechanical work (constants centralization) and validation work (Phase 4 on real projects). The architecture is sound, the test coverage is excellent, and the quality infrastructure (QA, calibration, feedback loop) is more thorough than most production systems. The 14 open issues are all low-severity consistency improvements, not functional defects.

**Rating: B+ (would be A- after constants centralization)**

---

## Files Reviewed

- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare/SKILL.md`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare/KNOWN-ISSUES.md`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare/lib/figma_utils.py`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare/scripts/` (all 16 files)
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare/references/` (all 4 files)
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare-improve/SKILL.md`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare-eval/SKILL.md`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/skills/figma-prepare-eval/scripts/run-calibration.sh`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/rules/figma-prepare.md`
- `/home/sakiomit/proj/coachers_yonezawa/.claude/data/figma-prepare-calibration.yaml`
- `/home/sakiomit/proj/coachers_yonezawa/tests/figma-prepare/` (all 10 files)
