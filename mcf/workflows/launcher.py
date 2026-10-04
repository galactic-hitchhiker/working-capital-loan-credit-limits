"""Python launcher with project-local plotting and cache directories.

Example: .venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.demo --output-dir results/demo
No system packages or third-party binaries are modified.
"""

import os
from pathlib import Path
import subprocess
import sys


def environment():
    """Preserve caller settings, using project-local plotting caches by default."""
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[2]
    env.setdefault("MPLCONFIGDIR", str(root / "results" / ".matplotlib"))
    env.setdefault("XDG_CACHE_HOME", str(root / "results" / ".cache"))
    return env


if __name__ == "__main__":
    if len(sys.argv) == 1:
        raise SystemExit(__doc__)
    raise SystemExit(
        subprocess.call([sys.executable, *sys.argv[1:]], env=environment())
    )
