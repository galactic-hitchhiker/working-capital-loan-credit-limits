"""Python launcher with project-local plotting and cache directories.

Example: .venv/bin/python run_research.py demo_workflow.py --output-dir results/demo
No system packages or third-party binaries are modified.
"""

import os
from pathlib import Path
import subprocess
import sys


def environment():
    env = os.environ.copy()
    root = Path(__file__).resolve().parent
    env.setdefault("MPLCONFIGDIR", str(root / "results" / ".matplotlib"))
    env.setdefault("XDG_CACHE_HOME", str(root / "results" / ".cache"))
    return env


if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise SystemExit(__doc__)
    raise SystemExit(
        subprocess.call([sys.executable, *sys.argv[1:]], env=environment())
    )
