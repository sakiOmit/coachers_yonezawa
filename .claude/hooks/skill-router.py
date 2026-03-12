#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Skill Router

Detects user intent from prompt and suggests the appropriate skill command.
Consolidates logic from suggest-review.py and suggest-analysis.py.
"""
import json
import sys
import re

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)

prompt = input_data.get("prompt", "")

# Skip if prompt is already a slash command
if prompt.strip().startswith("/"):
    sys.exit(0)

# Skip very short prompts (unlikely to contain actionable intent)
if len(prompt.strip()) < 4:
    sys.exit(0)

FIGMA_URL_RE = r"figma\.com/(design|file|board|make)/"

suggestions = []


def has_figma_url(text):
    return bool(re.search(FIGMA_URL_RE, text))


def match_any(text, patterns):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


# --- Figma ---
if has_figma_url(prompt):
    figma_url_count = len(re.findall(FIGMA_URL_RE, prompt))
    prepare_words = [
        r"整理", r"prepare", r"cleanup", r"clean\s?up",
        r"リネーム", r"rename", r"構造", r"structure",
        r"グループ化", r"group", r"auto.?layout",
        r"レイヤー", r"layer", r"前処理", r"前裁き",
    ]
    analyze_words = [
        r"分析", r"analyze", r"比較", r"compare", r"横断",
        r"共通", r"common", r"戦略", r"strategy", r"計画", r"plan",
    ]
    impl_words = [
        r"実装", r"作成", r"作って", r"コーディング", r"implement",
        r"build", r"create", r"code",
    ]
    investigate_words = [
        r"調査", r"確認", r"調べ", r"見て",
        r"check", r"inspect", r"investigate",
    ]

    if match_any(prompt, prepare_words):
        suggestions.append(("/figma-prepare", "Figma structure preparation"))
    elif figma_url_count >= 2 or match_any(prompt, analyze_words):
        # Multiple URLs or analyze keywords → figma-analyze
        suggestions.append(("/figma-analyze", "Multi-page Figma analysis"))
    elif match_any(prompt, investigate_words):
        suggestions.append(("/figma-to-code", "Figma design investigation"))
    elif match_any(prompt, impl_words):
        suggestions.append(("/figma-implement", "Figma to WordPress implementation"))
    else:
        # Default for single Figma URL without clear intent
        suggestions.append(("/figma-implement", "Figma to WordPress implementation"))

# --- Astro ---
elif match_any(prompt, [r"[Aa]stro"]):
    if match_any(prompt, [r"[Ww]ord[Pp]ress", r"変換", r"PHP", r"convert"]):
        suggestions.append(("/astro-to-wordpress", "Astro to WordPress conversion"))
    elif match_any(prompt, [r"ページ", r"作成", r"作って", r"page", r"create", r"生成"]):
        suggestions.append(("/astro-page-generator", "Astro page generation"))

# --- WordPress page ---
elif match_any(prompt, [r"[Ww]ord[Pp]ress"]) and match_any(
    prompt, [r"ページ", r"テンプレート", r"page", r"template", r"作成", r"create"]
):
    suggestions.append(
        ("/wordpress-page-generator", "WordPress page template generation")
    )

# --- SCSS component ---
elif match_any(prompt, [r"[Ss][Cc][Ss][Ss]", r"コンポーネント"]) and match_any(
    prompt, [r"コンポーネント", r"component", r"作成", r"create", r"生成"]
):
    suggestions.append(("/scss-component-generator", "SCSS component generation"))

# --- Review / QA / Fix / Delivery ---
elif match_any(prompt, [r"レビュー", r"review"]) and not match_any(
    prompt, [r"修正", r"fix"]
):
    suggestions.append(("/review", "Code review"))

elif match_any(prompt, [r"修正", r"fix"]) and match_any(
    prompt, [r"レビュー", r"review", r"指摘", r"issue"]
):
    suggestions.append(("/fix", "Fix review issues"))

elif match_any(prompt, [r"[Qq][Aa]", r"品質", r"quality"]):
    suggestions.append(("/qa", "QA check"))

elif match_any(prompt, [r"納品", r"delivery", r"デリバリー"]):
    suggestions.append(("/delivery", "Delivery quality check"))

# --- Implementation complete keywords (from suggest-review.py) ---
elif match_any(
    prompt,
    [
        r"実装完了",
        r"実装しました",
        r"完成しました",
        r"できました",
        r"終わりました",
        r"修正しました",
        r"対応しました",
        r"作成しました",
        r"implementation complete",
        r"^done$",
        r"^finished$",
    ],
):
    suggestions.append(("/review", "Code review"))
    suggestions.append(("/qa", "QA check"))
    suggestions.append(("/delivery", "Delivery check (pre-release)"))


# --- Output ---
if suggestions:
    lines = ["", "---", "[Skill Router] Suggested command(s):"]
    for cmd, desc in suggestions:
        lines.append(f"  `{cmd}` - {desc}")
    lines.append("")
    lines.append("Type the command to execute, or continue with your request.")
    lines.append("---")
    print("\n".join(lines))

sys.exit(0)
