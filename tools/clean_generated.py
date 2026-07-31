#!/usr/bin/env python3
"""Remove disposable simulation evidence and Python bytecode caches."""

from pathlib import Path
import os
import shutil
import stat

ROOT = Path(__file__).resolve().parents[1]


def make_writable(function, path, error):
    os.chmod(path, stat.S_IWRITE)
    function(path)


targets = [ROOT / "build", ROOT / "tmp", *ROOT.rglob("__pycache__")]
removed = 0
for target in targets:
    if not target.exists():
        continue
    resolved = target.resolve()
    if ROOT not in resolved.parents:
        raise RuntimeError(f"Refusing path outside project: {resolved}")
    shutil.rmtree(resolved, onexc=make_writable)
    removed += 1

print(f"Removed {removed} generated directories")
