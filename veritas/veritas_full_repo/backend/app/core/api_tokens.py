from __future__ import annotations

import hashlib
import hmac
import secrets

PREFIX = "veritas_pat_"
# Random body length (hex chars) — 32 bytes → 64 hex chars, plenty of entropy.
_BODY_BYTES = 32


def generate_token() -> str:
    """Return a fresh plaintext PAT, e.g. 'veritas_pat_<64 hex chars>'."""
    return PREFIX + secrets.token_hex(_BODY_BYTES)


def hash_token(token: str) -> str:
    """Stable sha256 hex of the plaintext token, used as the DB lookup key."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def looks_like_pat(token: str) -> bool:
    return isinstance(token, str) and token.startswith(PREFIX)


def short_prefix(token: str, n: int = 12) -> str:
    """Safe-to-display prefix for the UI ('veritas_pat_a1b2…')."""
    return token[: len(PREFIX) + n]


def verify(presented: str, stored_hash: str) -> bool:
    """Constant-time compare of sha256(presented) against the stored hex."""
    if not isinstance(presented, str) or not isinstance(stored_hash, str):
        return False
    return hmac.compare_digest(hash_token(presented), stored_hash)
