"""Remote path helpers for Slurm submission over SSH."""

from app.services.hpc_adapter import remote_path_for_shell, shell_double_quote


def test_remote_path_for_shell_expands_tilde_slash():
    assert remote_path_for_shell("~/veritas/jobs") == "$HOME/veritas/jobs"
    assert remote_path_for_shell("  ~/a/b  ") == "$HOME/a/b"


def test_remote_path_for_shell_absolute_unchanged():
    assert remote_path_for_shell("/scratch/veritas/x") == "/scratch/veritas/x"


def test_shell_double_quote_allows_home_expansion():
    q = shell_double_quote("$HOME/veritas/jobs/REQ-1/job")
    assert q.startswith('"')
    assert "$HOME" in q


def test_shell_double_quote_escapes_embedded_quote():
    assert shell_double_quote('a"b') == '"a\\"b"'
