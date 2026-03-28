"""CLI for Veritas Atlas API: `atlas-api` or `python -m app`."""

from __future__ import annotations

import argparse
import os
import sys

import jwt


def _argv_with_default_serve(argv: list[str]) -> list[str]:
    if not argv:
        return ["serve"]
    if argv[0] in ("serve", "dev-token", "celery-worker"):
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


def _cmd_celery_worker(args: argparse.Namespace) -> None:
    from app.celery_app import celery_app

    argv = ["worker", "--loglevel", args.loglevel, "-Q", args.queues]
    if args.concurrency:
        argv.extend(["--concurrency", str(args.concurrency)])
    celery_app.worker_main(argv)


def _cmd_dev_token(args: argparse.Namespace) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    token = jwt.encode(
        {
            "sub": args.sub,
            "roles": [r.strip() for r in args.roles.split(",") if r.strip()],
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.dev_bearer_secret,
        algorithm="HS256",
    )
    print(token)


def main(argv: list[str] | None = None) -> None:
    raw = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="atlas-api", description="Veritas Atlas API")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="Run the HTTP API (default if you omit the subcommand)")
    p_serve.add_argument("--host", default=os.environ.get("ATLAS_HOST", "0.0.0.0"))
    p_serve.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ATLAS_PORT", "8000")),
    )
    p_serve.add_argument("--reload", action="store_true", help="Dev auto-reload")
    p_serve.set_defaults(_run=_cmd_serve)

    p_celery = sub.add_parser("celery-worker", help="Run Celery worker for async tasks")
    p_celery.add_argument("--loglevel", default="info")
    p_celery.add_argument("--concurrency", type=int, default=None)
    p_celery.add_argument("--queues", default="atlas", help="Comma-separated queue names")
    p_celery.set_defaults(_run=_cmd_celery_worker)

    p_tok = sub.add_parser("dev-token", help="Print an HS256 dev JWT (ATLAS_ENV=dev/local)")
    p_tok.add_argument("--sub", required=True)
    p_tok.add_argument("--roles", default="researcher")
    p_tok.set_defaults(_run=_cmd_dev_token)

    argv = _argv_with_default_serve(list(raw))
    if raw in (["-h"], ["--help"]):
        parser.print_help()
        return

    args = parser.parse_args(argv)
    args._run(args)


if __name__ == "__main__":
    main()
