"""CLI for Veritas backend API: `veritas-api` or `python -m app`.

Subcommands:

  serve                                 Run the HTTP API (default)
  users create-admin --email E [--password P]
                                        Create or promote a user to admin
  users set-password --email E [--password P]
                                        Reset a user's password (ops-mediated)
  users set-role --email E --role R     Change a user's role
  users list                            List users (email, role, is_active)
"""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys
from pathlib import Path

_MIN_PASSWORD_LEN = 12  # minimum for any user-set value; auto-generated are 24+


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
    if argv[0] in ("serve", "users"):
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


def _prompt_password(action: str, allow_generate: bool = True) -> str:
    """Read a password from --password / stdin / interactive prompt.

    Auto-generates a strong one if interactive and allow_generate=True and the
    user just hits Enter.
    """
    if allow_generate and sys.stdin.isatty():
        prompt = f"Password for {action} (Enter to auto-generate): "
    else:
        prompt = f"Password for {action}: "
    pw = getpass.getpass(prompt) if sys.stdin.isatty() else sys.stdin.readline().rstrip("\n")
    if not pw:
        if not allow_generate:
            raise SystemExit("Password is required.")
        pw = secrets.token_urlsafe(24)
        print(f"(generated password: {pw})", file=sys.stderr)
        return pw
    if len(pw) < _MIN_PASSWORD_LEN:
        raise SystemExit(f"Password must be at least {_MIN_PASSWORD_LEN} characters.")
    if sys.stdin.isatty():
        confirm = getpass.getpass("Confirm password: ")
        if confirm != pw:
            raise SystemExit("Passwords do not match.")
    return pw


def _get_or_make_password(args: argparse.Namespace, action: str) -> str:
    if args.password:
        if len(args.password) < _MIN_PASSWORD_LEN:
            raise SystemExit(f"--password must be at least {_MIN_PASSWORD_LEN} characters.")
        return args.password
    return _prompt_password(action)


def _resolve_user(db, email: str):
    """Return the User row for `email` (lowercased) or None."""
    from app.models.user import User

    return db.query(User).filter(User.email == email.strip().lower()).one_or_none()


def _cmd_users_create_admin(args: argparse.Namespace) -> None:
    from app.core.passwords import hash_password
    from app.db.session import SessionLocal
    from app.models.user import User

    email = args.email.strip().lower()
    db = SessionLocal()
    try:
        existing = _resolve_user(db, email)
        if existing is not None:
            # Promote in place instead of erroring; idempotent for ops.
            password = args.password
            if existing.role == "admin" and not password:
                print(f"User {email!r} already exists with role=admin. Nothing to do.")
                return
            if password:
                if len(password) < _MIN_PASSWORD_LEN:
                    raise SystemExit(f"--password must be at least {_MIN_PASSWORD_LEN} characters.")
                existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.is_active = True
            db.add(existing)
            db.commit()
            print(f"Promoted {email!r} to admin." + (" Password updated." if password else ""))
            return

        password = _get_or_make_password(args, f"new admin {email}")
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=args.full_name,
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created admin user {email!r}.")
    finally:
        db.close()


def _cmd_users_set_password(args: argparse.Namespace) -> None:
    from app.core.passwords import hash_password
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        user = _resolve_user(db, args.email)
        if user is None:
            raise SystemExit(f"No user with email {args.email!r}.")
        password = _get_or_make_password(args, f"{user.email}")
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()
        print(f"Password updated for {user.email!r}.")
    finally:
        db.close()


def _cmd_users_set_role(args: argparse.Namespace) -> None:
    from app.db.session import SessionLocal

    role = args.role.strip().lower()
    if role not in ("admin", "researcher"):
        raise SystemExit("Role must be one of: admin, researcher.")
    db = SessionLocal()
    try:
        user = _resolve_user(db, args.email)
        if user is None:
            raise SystemExit(f"No user with email {args.email!r}.")
        user.role = role
        db.add(user)
        db.commit()
        print(f"Role for {user.email!r} set to {role!r}.")
    finally:
        db.close()


def _cmd_users_list(_args: argparse.Namespace) -> None:
    from app.db.session import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        # admin first (asc puts 'admin' before 'researcher'), then by email.
        rows = db.query(User).order_by(User.role.asc(), User.email.asc()).all()
        if not rows:
            print("(no users)")
            return
        width_email = max(20, max(len(u.email) for u in rows))
        print(f"{'EMAIL':<{width_email}}  {'ROLE':<11}  {'ACTIVE':<6}  CREATED")
        for u in rows:
            print(
                f"{u.email:<{width_email}}  {u.role:<11}  "
                f"{'yes' if u.is_active else 'no':<6}  {u.created_at.isoformat()}"
            )
    finally:
        db.close()


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

    p_users = sub.add_parser("users", help="User management (ops, no HTTP needed)")
    users_sub = p_users.add_subparsers(dest="users_cmd", required=True)

    p_create = users_sub.add_parser("create-admin", help="Create or promote a user to admin")
    p_create.add_argument("--email", required=True)
    p_create.add_argument("--password", default=None, help="Min 12 chars. If omitted, prompted (or auto-generated in TTY).")
    p_create.add_argument("--full-name", default=None)
    p_create.set_defaults(_run=_cmd_users_create_admin)

    p_pwd = users_sub.add_parser("set-password", help="Reset a user's password (ops-mediated)")
    p_pwd.add_argument("--email", required=True)
    p_pwd.add_argument("--password", default=None, help="Min 12 chars. If omitted, prompted (or auto-generated in TTY).")
    p_pwd.set_defaults(_run=_cmd_users_set_password)

    p_role = users_sub.add_parser("set-role", help="Change a user's role")
    p_role.add_argument("--email", required=True)
    p_role.add_argument("--role", required=True, choices=["admin", "researcher"])
    p_role.set_defaults(_run=_cmd_users_set_role)

    p_list = users_sub.add_parser("list", help="List users")
    p_list.set_defaults(_run=_cmd_users_list)

    argv = _argv_with_default_serve(list(raw))
    if raw in (["-h"], ["--help"]):
        parser.print_help()
        return

    args = parser.parse_args(argv)
    args._run(args)


if __name__ == "__main__":
    main()
