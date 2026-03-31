"""CLI for Veritas backend API: `veritas-api` or `python -m app`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_dotenv_for_cli() -> None:
    """Load backend/.env before parsing so VERITAS_HOST / VERITAS_PORT apply to `serve`."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _argv_with_default_serve(argv: list[str]) -> list[str]:
    if not argv:
        return ["serve"]
    if argv[0] in ("serve",):
        return argv
    if argv[0] in ("-h", "--help"):
        return argv
    return ["serve", *argv]


def _cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        factory=False,
        reload=args.reload,
    )


def main(argv: list[str] | None = None) -> None:
    _load_dotenv_for_cli()
    raw = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="veritas-api", description="Veritas validation / Atlas integration API")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="Run the HTTP API (default if you omit the subcommand)")
    p_serve.add_argument("--host", default=os.environ.get("VERITAS_HOST", "0.0.0.0"))
    p_serve.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("VERITAS_PORT", "6000")),
    )
    p_serve.add_argument("--reload", action="store_true", help="Dev auto-reload")
    p_serve.set_defaults(_run=_cmd_serve)

    argv = _argv_with_default_serve(list(raw))
    if raw in (["-h"], ["--help"]):
        parser.print_help()
        return

    args = parser.parse_args(argv)
    args._run(args)


if __name__ == "__main__":
    main()
