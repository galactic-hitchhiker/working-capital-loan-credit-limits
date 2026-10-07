"""Run Python commands with project-local plotting and cache directories.

Run from the repository root:
    .venv/bin/python -m mcf.workflows.launcher -m MODULE [module parameters]

Parameters (all arguments are forwarded to the same Python interpreter):
    -m MODULE: Execute a module, e.g. mcf.workflows.demo.
    SCRIPT: Alternatively, execute a Python script path instead of -m MODULE.
    Remaining arguments: Parameters accepted by the selected module or script.
    -h, --help: Before a target, show Python help; after it, show the target's help.
    No arguments: Print this launcher documentation and exit.

Environment:
    MPLCONFIGDIR: Matplotlib cache directory (default: results/.matplotlib).
    XDG_CACHE_HOME: General cache directory (default: results/.cache).
    Defaults are relative to the repository root; existing environment values win.
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
