"""CLI entry point for gap analyzer. Delegates to renderer."""
import sys
import os

_base = os.path.join(os.path.dirname(__file__), "..", "..", "..")
sys.path.insert(0, _base)
# renderer.py 使用 flat import (from analysis.skill_map), 需要 scripts/ 在 sys.path 上
sys.path.insert(0, os.path.join(_base, "scripts"))

from scripts.analysis.gap_analyzer.renderer import main

if __name__ == "__main__":
    main()
