"""Backward-compatible wrapper; prefer `atlas-api dev-token --sub ...`."""

from __future__ import annotations

import sys

from app.cli import main

if __name__ == "__main__":
    sys.argv = ["atlas-api", "dev-token", *sys.argv[1:]]
    main()
