# 03_serve_model.py
# Thin launcher for the Brussels FastAPI app in 03_fastapi/
# Tim Fraser
#
# From repo root: python 12_end/03_serve_model.py

import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "03_fastapi"


def pick_python() -> str:
    """Prefer the local venv interpreter when present."""
    if sys.platform == "win32":
        cand = APP_DIR / ".venv" / "Scripts" / "python.exe"
    else:
        cand = APP_DIR / ".venv" / "bin" / "python"
    return str(cand) if cand.exists() else sys.executable


def main() -> int:
    cmd = [
        pick_python(),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    return subprocess.run(cmd, cwd=str(APP_DIR), env=os.environ.copy()).returncode


if __name__ == "__main__":
    sys.exit(main())
