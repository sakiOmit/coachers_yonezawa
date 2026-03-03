#!/usr/bin/env python3
"""
Claude Code Skill Usage Analyzer

Analyzes JSONL conversation logs to determine which skills are being used,
how often, and which remain unused.

Usage:
    python3 .claude/scripts/analyze-usage.py [command] [options]

Commands:
    skills      Skill usage analysis (default)

Options:
    --days N    Analyze past N days (default: 30)
    --sort X    Sort by: count, name, date (default: count)
    --csv       Output as CSV
    --report    Save Markdown report to .claude/reports/
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    script_dir = Path(__file__).resolve().parent
    # .claude/scripts/ -> project root
    return script_dir.parent.parent


def get_log_dir():
    """Get the JSONL log directory."""
    return Path.home() / ".claude" / "projects" / "-home-sakiomit-proj-wordpress-template"


def get_hook_log_path(project_root):
    """Get the hook-based skill usage log file path."""
    return project_root / ".claude" / "logs" / "skill-usage.jsonl"


def parse_hook_log(hook_log_path, cutoff_date=None):
    """Parse the hook-generated skill usage log (fast path).

    Returns:
        list of {skill, timestamp, source}
    """
    skill_calls = []
    if not hook_log_path.exists():
        return skill_calls

    try:
        with open(hook_log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                timestamp_str = entry.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(timestamp_str)
                    # Ensure timezone-aware for comparison
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except (ValueError, AttributeError):
                    continue

                if cutoff_date and ts < cutoff_date:
                    continue

                skill_name = entry.get("skill", "")
                if skill_name:
                    skill_calls.append({
                        "skill": skill_name,
                        "timestamp": ts,
                        "source": "hook",
                    })
    except (OSError, IOError):
        pass

    return skill_calls


def get_skill_definitions(project_root):
    """Get all skill names from .claude/skills/*/SKILL.md."""
    skills_dir = project_root / ".claude" / "skills"
    skills = []
    if skills_dir.exists():
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            skill_name = skill_md.parent.name
            skills.append(skill_name)
    return skills


def parse_jsonl_file(filepath, cutoff_date=None):
    """Parse a single JSONL file and extract skill usage data.

    Returns:
        dict with:
            - skill_calls: list of {skill, timestamp, source}
            - session_id: str or None
            - first_ts: datetime or None
    """
    skill_calls = []
    session_id = None
    first_ts = None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                timestamp_str = obj.get("timestamp")
                if not timestamp_str:
                    continue

                try:
                    ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue

                if cutoff_date and ts < cutoff_date:
                    continue

                if first_ts is None:
                    first_ts = ts

                if session_id is None:
                    session_id = obj.get("sessionId")

                msg_type = obj.get("type")

                # 1. Detect Skill tool_use in assistant messages
                if msg_type == "assistant":
                    message = obj.get("message", {})
                    content = message.get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                                skill_input = block.get("input", {})
                                skill_name = skill_input.get("skill", "unknown")
                                # Normalize: strip prefix like "ms-office-suite:"
                                if ":" in skill_name:
                                    skill_name = skill_name.split(":")[-1]
                                skill_calls.append({
                                    "skill": skill_name,
                                    "timestamp": ts,
                                    "source": "tool_use",
                                })

                # 2. Detect /skill-name in user messages
                if msg_type in ("human", "user"):
                    message = obj.get("message", {})
                    content = message.get("content", "")
                    texts = []
                    if isinstance(content, str):
                        texts.append(content)
                    elif isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                texts.append(block.get("text", ""))
                            elif isinstance(block, str):
                                texts.append(block)

                    for text in texts:
                        m = re.match(r"^/([\w][\w-]*)", text.strip())
                        if m:
                            cmd = m.group(1)
                            # Exclude built-in CLI commands
                            builtins = {
                                "help", "clear", "compact", "config", "cost",
                                "doctor", "init", "login", "logout", "memory",
                                "mcp", "model", "permissions", "status", "terminal-setup",
                                "vim", "home", "fast", "slow", "tasks",
                            }
                            if cmd not in builtins:
                                skill_calls.append({
                                    "skill": cmd,
                                    "timestamp": ts,
                                    "source": "slash_command",
                                })

    except (OSError, IOError):
        pass

    return {
        "skill_calls": skill_calls,
        "session_id": session_id,
        "first_ts": first_ts,
    }


def analyze_skills(days=30, sort_by="count"):
    """Analyze skill usage from hook log + JSONL logs.

    1. Hook log (.claude/logs/skill-usage.jsonl) を優先的に読み込む（高速）
    2. JSONL会話ログからも補完的にスキャン（hook導入前のデータ用）
    3. 両ソースをマージして重複排除
    """
    project_root = get_project_root()
    log_dir = get_log_dir()

    # Get defined skills
    defined_skills = get_skill_definitions(project_root)

    # Calculate cutoff date
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    skill_usage = defaultdict(lambda: {"count": 0, "last_used": None, "sources": set()})
    earliest_ts = None
    latest_ts = None
    total_sessions = 0

    # --- Source 1: Hook log (fast path) ---
    hook_log_path = get_hook_log_path(project_root)
    hook_calls = parse_hook_log(hook_log_path, cutoff_date=cutoff)

    for call in hook_calls:
        skill = call["skill"]
        skill_usage[skill]["count"] += 1
        skill_usage[skill]["sources"].add(call["source"])
        if (
            skill_usage[skill]["last_used"] is None
            or call["timestamp"] > skill_usage[skill]["last_used"]
        ):
            skill_usage[skill]["last_used"] = call["timestamp"]

    hook_has_data = len(hook_calls) > 0

    # --- Source 2: JSONL conversation logs (slow path, supplementary) ---
    log_files = sorted(glob.glob(str(log_dir / "*.jsonl")))

    for fpath in log_files:
        result = parse_jsonl_file(fpath, cutoff_date=cutoff)
        if result["first_ts"]:
            total_sessions += 1
            if earliest_ts is None or result["first_ts"] < earliest_ts:
                earliest_ts = result["first_ts"]
            if latest_ts is None or result["first_ts"] > latest_ts:
                latest_ts = result["first_ts"]

        for call in result["skill_calls"]:
            skill = call["skill"]
            skill_usage[skill]["count"] += 1
            skill_usage[skill]["sources"].add(call["source"])
            if (
                skill_usage[skill]["last_used"] is None
                or call["timestamp"] > skill_usage[skill]["last_used"]
            ):
                skill_usage[skill]["last_used"] = call["timestamp"]

    # Separate used and unused
    used_skills = []
    for skill_name, data in skill_usage.items():
        used_skills.append({
            "name": skill_name,
            "count": data["count"],
            "last_used": data["last_used"],
            "defined": skill_name in defined_skills,
            "sources": data["sources"],
        })

    never_used = [s for s in defined_skills if s not in skill_usage]

    # Sort used skills
    if sort_by == "count":
        used_skills.sort(key=lambda x: (-x["count"], x["name"]))
    elif sort_by == "name":
        used_skills.sort(key=lambda x: x["name"])
    elif sort_by == "date":
        used_skills.sort(key=lambda x: (x["last_used"] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)

    never_used.sort()

    return {
        "used_skills": used_skills,
        "never_used": never_used,
        "total_defined": len(defined_skills),
        "total_sessions": total_sessions,
        "period_start": earliest_ts,
        "period_end": latest_ts,
        "days": days,
        "data_sources": ["hook"] if hook_has_data else [] + ["jsonl"],
    }


def format_table(data):
    """Format analysis results as a CLI table."""
    lines = []
    lines.append("=== Skill Usage Report ===")

    period_start = data["period_start"].strftime("%Y-%m-%d") if data["period_start"] else "N/A"
    period_end = data["period_end"].strftime("%Y-%m-%d") if data["period_end"] else "N/A"
    lines.append(f"Period: {period_start} ~ {period_end} ({data['total_sessions']} sessions, last {data['days']} days)")
    lines.append("")

    if data["used_skills"]:
        lines.append(f"  # | {'Skill Name':<40} | {'Count':>5} | {'Last Used':<10} | Defined")
        lines.append(f"----+{'-' * 42}+{'-' * 7}+{'-' * 12}+---------")
        for i, skill in enumerate(data["used_skills"], 1):
            last_used = skill["last_used"].strftime("%Y-%m-%d") if skill["last_used"] else "N/A"
            defined = "yes" if skill["defined"] else "no"
            lines.append(f" {i:2d} | {skill['name']:<40} | {skill['count']:>5} | {last_used:<10} | {defined}")
    else:
        lines.append("  No skill usage detected in the analyzed period.")

    lines.append("")
    lines.append(f"=== Never Used Skills ({len(data['never_used'])}) ===")
    for skill in data["never_used"]:
        lines.append(f"  - {skill}")

    lines.append("")
    lines.append("=== Summary ===")
    total_used = len(data["used_skills"])
    total_defined = data["total_defined"]
    total_never = len(data["never_used"])
    used_pct = (total_used / total_defined * 100) if total_defined > 0 else 0
    never_pct = (total_never / total_defined * 100) if total_defined > 0 else 0
    lines.append(f"  Total defined skills: {total_defined}")
    lines.append(f"  Used: {total_used} ({used_pct:.0f}%)")
    lines.append(f"  Never used: {total_never} ({never_pct:.0f}%)")
    lines.append(f"  Undefined but invoked: {sum(1 for s in data['used_skills'] if not s['defined'])}")
    sources = data.get("data_sources", [])
    if sources:
        lines.append(f"  Data sources: {', '.join(sources)}")

    return "\n".join(lines)


def format_csv(data):
    """Format analysis results as CSV."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "Skill Name", "Count", "Last Used", "Defined", "Status"])

    for i, skill in enumerate(data["used_skills"], 1):
        last_used = skill["last_used"].strftime("%Y-%m-%d") if skill["last_used"] else ""
        writer.writerow([i, skill["name"], skill["count"], last_used, skill["defined"], "used"])

    for skill in data["never_used"]:
        writer.writerow(["", skill, 0, "", True, "never_used"])

    return output.getvalue()


def format_markdown(data):
    """Format analysis results as Markdown."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    period_start = data["period_start"].strftime("%Y-%m-%d") if data["period_start"] else "N/A"
    period_end = data["period_end"].strftime("%Y-%m-%d") if data["period_end"] else "N/A"

    lines.append("# Skill Usage Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Period: {period_start} ~ {period_end} ({data['total_sessions']} sessions, last {data['days']} days)")
    lines.append("")

    # Summary
    total_used = len(data["used_skills"])
    total_defined = data["total_defined"]
    total_never = len(data["never_used"])
    used_pct = (total_used / total_defined * 100) if total_defined > 0 else 0

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total defined | {total_defined} |")
    lines.append(f"| Used | {total_used} ({used_pct:.0f}%) |")
    lines.append(f"| Never used | {total_never} |")
    lines.append("")

    # Used skills table
    lines.append("## Used Skills")
    lines.append("")
    if data["used_skills"]:
        lines.append("| # | Skill | Count | Last Used |")
        lines.append("|---|-------|-------|-----------|")
        for i, skill in enumerate(data["used_skills"], 1):
            last_used = skill["last_used"].strftime("%Y-%m-%d") if skill["last_used"] else "N/A"
            name = skill["name"]
            if not skill["defined"]:
                name += " *"
            lines.append(f"| {i} | {name} | {skill['count']} | {last_used} |")
        lines.append("")
        lines.append("\\* = not in `.claude/skills/`")
    else:
        lines.append("No skill usage detected.")
    lines.append("")

    # Never used
    lines.append(f"## Never Used Skills ({total_never})")
    lines.append("")
    for skill in data["never_used"]:
        lines.append(f"- {skill}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Skill Usage Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="skills",
        choices=["skills"],
        help="Analysis command (default: skills)",
    )
    parser.add_argument("--days", type=int, default=30, help="Analyze past N days (default: 30)")
    parser.add_argument("--sort", choices=["count", "name", "date"], default="count", help="Sort order (default: count)")
    parser.add_argument("--csv", action="store_true", help="Output as CSV")
    parser.add_argument("--report", action="store_true", help="Save Markdown report to .claude/reports/")

    args = parser.parse_args()

    if args.command == "skills":
        data = analyze_skills(days=args.days, sort_by=args.sort)

        if args.csv:
            print(format_csv(data))
        elif args.report:
            project_root = get_project_root()
            reports_dir = project_root / ".claude" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"skill-usage_{timestamp}.md"
            content = format_markdown(data)
            report_path.write_text(content, encoding="utf-8")
            print(f"Report saved to: {report_path}")
            print()
            print(format_table(data))
        else:
            print(format_table(data))


if __name__ == "__main__":
    main()
