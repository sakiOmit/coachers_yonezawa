"""Shared test helpers for figma-prepare tests."""
import json
import os
import subprocess
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills", "figma-prepare")
SCRIPTS_DIR = os.path.join(SKILLS_DIR, "scripts")


def run_script(script_name, *args, timeout=30):
    """Run a shell script and return parsed JSON output."""
    script = os.path.join(SCRIPTS_DIR, script_name)
    result = subprocess.run(
        ["bash", script, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    assert result.returncode == 0, f"{script_name} failed: {result.stderr}"
    return json.loads(result.stdout)


def write_fixture(data):
    """Write JSON fixture to temp file, return path (caller must delete)."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, f)
    f.close()
    return f.name
