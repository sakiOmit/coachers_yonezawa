"""Shared pytest configuration for figma-prepare tests.

Ensures figma_utils is importable by adding its directory to sys.path
before any test module is collected.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(PROJECT_ROOT, ".claude", "skills", "figma-prepare")
sys.path.insert(0, os.path.join(SKILLS_DIR, "lib"))
