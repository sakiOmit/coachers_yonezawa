#!/usr/bin/env python3
"""
PostToolUse Hook: デバッグコード検出警告
ファイル編集後に console.log, var_dump, dd() などを検出して警告
"""
import json
import sys
import os
import re

# 検出パターン定義
DEBUG_PATTERNS = {
    ".js": [
        (r'\bconsole\.(log|debug|info|warn|error)\s*\(', "console.log系"),
        (r'\bdebugger\b', "debugger文"),
    ],
    ".ts": [
        (r'\bconsole\.(log|debug|info|warn|error)\s*\(', "console.log系"),
        (r'\bdebugger\b', "debugger文"),
    ],
    ".php": [
        (r'\bvar_dump\s*\(', "var_dump()"),
        (r'\bprint_r\s*\(', "print_r()"),
        (r'\bdd\s*\(', "dd()"),
        (r'\berror_log\s*\(', "error_log()"),
        (r'<\?php\s+echo\s+[\'"]debug', "debugエコー"),
    ],
    ".scss": [
        (r'@debug\s+', "@debug"),
        (r'@warn\s+[\'"]debug', "@warn debug"),
    ],
}

def get_file_extension(file_path: str) -> str:
    """ファイル拡張子を取得"""
    _, ext = os.path.splitext(file_path)
    return ext.lower()

def detect_debug_code(file_path: str) -> list:
    """ファイル内のデバッグコードを検出"""
    ext = get_file_extension(file_path)
    patterns = DEBUG_PATTERNS.get(ext, [])

    if not patterns:
        return []

    if not os.path.exists(file_path):
        return []

    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            for pattern, name in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # コメント内のものは除外
                    stripped = line.strip()
                    if ext in ['.js', '.ts'] and stripped.startswith('//'):
                        continue
                    if ext == '.php' and (stripped.startswith('//') or stripped.startswith('*')):
                        continue
                    if ext == '.scss' and stripped.startswith('//'):
                        continue

                    findings.append({
                        "line": line_num,
                        "type": name,
                        "content": line.strip()[:60]
                    })
    except Exception:
        pass

    return findings

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ["Edit", "Write"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # デバッグコード検出
    findings = detect_debug_code(file_path)

    if findings:
        print(f"\n⚠️ デバッグコード検出: {os.path.basename(file_path)}")
        for f in findings[:5]:  # 最大5件表示
            print(f"   L{f['line']}: {f['type']} - {f['content']}")
        if len(findings) > 5:
            print(f"   ... 他 {len(findings) - 5} 件")
        print("   💡 本番環境では削除してください")

    sys.exit(0)

if __name__ == "__main__":
    main()
