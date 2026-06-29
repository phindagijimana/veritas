# Internal security review — v0.1.0

**Date:** 2026-06-29 · **Reviewer:** maintainer self-review with `bandit`,
`pip-audit`, and `npm audit`.

This is **not** an external penetration test. It is a structured
internal scan whose output a reviewer or institutional security team
can read alongside `docs/threat-model.md` and `SECURITY.md`. The same
scans are reproducible from the commands in the appendix.

## Summary

| Surface              | Tool        | Findings (initial) | Fixed in 0.1.0 | Tracked open |
|----------------------|-------------|--------------------|----------------|--------------|
| Veritas API source   | bandit      | 6 (1 H, 5 M)       | 0              | 6 — see §1   |
| Atlas API source     | bandit      | 0                  | 0              | 0            |
| Veritas API deps     | pip-audit   | 15 across 4 pkgs   | 7 (multipart, pytest) | 8 — see §2 |
| Veritas UI deps      | npm audit   | 8 (1 C, 2 H, 4 M, 1 L) | 3 (transitive) | 5 dev-only — see §3 |
| Atlas API deps       | pip-audit   | 7 pip-itself CVEs  | n/a (env tool) | informational only |

Severities: **C**ritical / **H**igh / **M**oderate / **L**ow.

## 1. Source-code findings (bandit)

All six bandit findings on the Veritas backend are **known, documented,
and gated** — none are immediate-action bugs, but each is recorded for
traceability.

| ID | Severity | File:line | Disposition |
|----|----------|-----------|-------------|
| B104 (bind 0.0.0.0) | M / M | `app/cli.py:205` | **By design.** Default host is configurable via `VERITAS_HOST`; production deployments terminate TLS at a reverse proxy and bind the API to `127.0.0.1` (see `docs/VERITAS_PRODUCTION.md`). |
| B108 (`/tmp` usage) | M / M | `app/services/hidden_test_service.py:24`, `app/workers/atlas_phase_d_worker.py:16` | **Accepted.** Used for ephemeral fixtures in test-fixture services. Never executed in production paths. Tracked for replacement with `tempfile.mkdtemp(prefix=…)` in 0.2.0. |
| B310 (URL open) | M / H | `app/services/pipeline_yaml_validator.py:184` | **Tracked.** `urllib.request.urlopen` is called against URLs from a pipeline manifest. Validator currently restricts to `http://` / `https://` but a Bandit-style hard guard is added in 0.2.0 (deny `file:`, `ftp:`, `data:`). |
| B507 (SSH AutoAddPolicy) | H / M | `app/services/ssh_service.py:28` | **Gated by config.** `SSH_STRICT_HOST_KEY_CHECKING=true` is enforced by `validate_production_settings()` when `APP_ENV=production`. Development default of false is documented in the threat model. |
| B601 (paramiko exec_command) | M / M | `app/services/ssh_service.py:92` | **Inputs are vetted.** Slurm commands are templated from a fixed set (`sbatch`, `squeue`, `scancel`); no user-supplied shell strings are passed. Reviewed for command injection during this audit and confirmed safe. |

The Atlas API has **zero** bandit findings.

## 2. Python dependency vulnerabilities (pip-audit)

### Patched in v0.1.0

| Package | Pinned from → to | Reason |
|---------|------------------|--------|
| `python-multipart` | `==0.0.20` → `>=0.0.31,<0.1` | Closes 6 CVEs: CVE-2026-24486 (path traversal), CVE-2026-40347 / CVE-2026-42561 / CVE-2026-53540 / CVE-2026-53539 / CVE-2026-53538 (DoS variants on multipart parsing). |
| `pytest` | `==8.3.5` → `>=9.0.3,<10` | Closes CVE-2025-71176 (`/tmp/pytest-of-{user}` predictable path on UNIX). Dev/test extra only. |

### Open, tracked

| Package | Version | CVE(s) | Why not patched in 0.1.0 |
|---------|---------|--------|--------------------------|
| `starlette` | `0.47.3` | PYSEC-2026-161, PYSEC-2026-249, PYSEC-2026-248, CVE-2025-62727, CVE-2026-48818, CVE-2026-48817 (7 total) | FastAPI 0.116.1 pins `starlette<0.48`. Bumping starlette to 1.x requires bumping FastAPI to a release that supports it. Targeted for v0.2.0 (FastAPI ≥ 0.130, starlette ≥ 1.3.1). Mitigations in place: TLS terminates at reverse proxy, `max_request_body_bytes` cap, `TrustedHostMiddleware`. |
| `paramiko` | `3.4.0` | CVE-2026-44405 | **No upstream fix yet.** Issue is that `rsakey.py` still permits SHA-1. Workaround: configure the Slurm head node to refuse SHA-1 ssh-rsa (already the default on modern OpenSSH). Tracked upstream. |

### Informational

The `pip` binary in the Atlas environment is `23.2.1`, which has 7
historical CVEs. This is the **build tool**, not a runtime dependency
of either application. Operators should upgrade pip in CI / build
images as a matter of hygiene; no runtime exposure.

## 3. JavaScript dependency vulnerabilities (npm audit)

`npm audit fix` (non-force) was applied. 3 transitive findings resolved
automatically. 5 remain — all are in `devDependencies` (`vite`,
`vitest`, `esbuild`), reachable only when a developer runs the local
dev server or the test runner on their own machine.

| Package | Severity | Why not patched in 0.1.0 |
|---------|----------|--------------------------|
| `vitest` | Critical | Vitest UI server file-read CVE. Vitest UI is not invoked by `npm test` (only by `npm run test:ui`, which we don't ship). Upgrading requires Vite 7 which requires Node 20.19+; tracked for v0.2.0. |
| `vite` | High | Path-traversal and Windows UNC issues in dev server. Production builds are emitted by `vite build`; the dev server is not exposed in any deployment scenario. |
| `vite-node`, `@vitest/mocker`, `esbuild` | Moderate | All transitive on vite/vitest above. Resolved together when vite is bumped. |

There are **zero** vulnerabilities in shipped runtime JS (the React app
itself), only in build-time tooling.

## 4. Other manual checks performed

- ✅ JWT signing key is config-gated; `validate_production_settings`
  refuses placeholder secrets at boot.
- ✅ PAT tokens are SHA-256-hashed at rest with a distinct prefix
  (`veritas_pat_…`) for grep-able revocation.
- ✅ `require_jwt` enforced on `POST /auth/tokens` — PATs cannot mint
  PATs (anti-pivot).
- ✅ RBAC declared on every state-changing route in `app/api/v1/` —
  reviewed during this pass; no missing guards.
- ✅ Audit log is append-only at the application layer; no UPDATE or
  DELETE route over `audit_events`.
- ✅ CORS allowlist refuses `*` in production
  (`validate_production_settings`).
- ✅ Login + register paths rate-limited via SlowAPI; defaults
  documented in `app/core/config.py`.
- ✅ `.env`, `license.txt`, `meld_license.txt`, secrets are all in
  `.gitignore`; reviewed git history with `git log --all --diff-filter=A
  -- 'license*'` and confirmed never tracked.

## 5. Not equivalent to an external pen test

This review is internal, automated, and bounded by the tools above. It
does **not** substitute for:

- A red-team exercise against a deployed instance (auth fuzzing, SSRF
  probes, rate-limit bypass, session fixation, file-upload abuse).
- A formal SAST run with a commercial tool (Semgrep Pro, Veracode,
  Snyk, etc.) configured against this stack's specific patterns.
- A SOC 2 / HIPAA controls audit.

Those remain on the "remaining external" list and are owned by URMC
security / a contracted vendor. The published cost estimate for an
appropriately-scoped external pen test is in the order of $5k–$15k
USD.

## Appendix — reproducing this review

From the repo root:

```bash
# Python static analysis
pip install --user bandit pip-audit
mkdir -p $HOME/tmp-audit && export TMPDIR=$HOME/tmp-audit

# Source-code scan (Veritas backend)
( cd veritas/veritas_full_repo/backend && \
  bandit -r app/ -ll -f json -o /tmp/bandit-backend.json )

# Source-code scan (Atlas backend)
( cd atlas_api/atlas_api_app && \
  bandit -r atlas_api/ -ll -f json -o /tmp/bandit-atlas.json )

# Dependency CVE scan (Veritas backend)
( cd veritas/veritas_full_repo/backend && \
  pip-audit -r requirements.txt --format=json --progress-spinner=off \
  > /tmp/pip-audit-backend.json )

# Frontend npm audit
( cd veritas/veritas_full_repo/frontend && \
  npm audit --json > /tmp/npm-audit-ui.json )
```

Re-run after any dependency bump and update this document. CI does
**not** currently gate on these scanners (intentional — false positives
are common); a `make security-scan` target is planned for v0.2.0.
