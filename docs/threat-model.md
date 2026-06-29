# Veritas & Atlas — threat model (STRIDE)

A one-page reference for operators and reviewers. Pairs with
`SECURITY.md` (reporting policy, supported versions) and
`docs/architecture/veritas-architecture.md` (component diagram).

## Trust boundaries

```
┌──────────────────────────────────────────────────────────────────────┐
│ Untrusted: public internet                                           │
└──────────────────────────────────────────────────────────────────────┘
       │ HTTPS only (operator-managed TLS termination)
┌──────────────────────────────────────────────────────────────────────┐
│ Semi-trusted: institutional network (authenticated researchers)      │
│   Veritas UI  ──►  Veritas API (FastAPI)  ──►  Atlas API             │
└──────────────────────────────────────────────────────────────────────┘
       │ SSH (key-based, known_hosts pinned in production)
┌──────────────────────────────────────────────────────────────────────┐
│ Trusted: HPC cluster (Slurm + Apptainer)                             │
│   sbatch, container runtime, dataset staging path                    │
└──────────────────────────────────────────────────────────────────────┘
```

Anything that crosses a boundary is logged in `audit_events`.

## Assets

| Asset                          | Sensitivity                       |
|--------------------------------|-----------------------------------|
| User credentials (bcrypt hash) | High (password recovery vector)   |
| Personal access tokens         | High (full API as the user)       |
| JWT signing key                | Critical (forges any session)     |
| Audit log                      | High (compliance + forensics)     |
| Patient-derived BIDS data      | Critical (PHI; never enters DB)   |
| Report artifacts (PDF/JSON)    | Medium-high (derived from PHI)    |
| FreeSurfer license             | License-sensitive (not PHI)       |
| Slurm SSH key                  | Critical (cluster pivot)          |

## STRIDE

### Spoofing
- **Threats:** session-token theft, PAT theft, replay against `/auth/me`.
- **Controls:** JWT short-expiry (60 min default), PATs are sha256-hashed
  at rest with a unique prefix for grep-able revocation, `require_jwt`
  on `/auth/tokens` prevents a stolen PAT from minting a new PAT, login
  + register rate-limited via SlowAPI.
- **Residual risk:** session fixation on the UI before MFA lands.
  Mitigation: HTTPS-only cookies + short JWT expiry.

### Tampering
- **Threats:** audit-log mutation, report substitution, schema drift.
- **Controls:** `audit_events` is append-only at the application layer
  (no UPDATE/DELETE routes); report bundles carry a `run_manifest.json`
  with checksums; Alembic enforces migration ordering and
  `database_auto_create_schema=false` is required in production.
- **Residual risk:** a DBA with direct Postgres access can rewrite
  history. Mitigation: out-of-band Postgres backups + WAL archiving.

### Repudiation
- **Threats:** "I never submitted that run."
- **Controls:** every state-changing request is captured in
  `audit_events` with `user_email`, `action`, `target_type`,
  `target_id`, `ip`, `user_agent`, and `created_at`. Admin can export
  to CSV/JSON for legal hold.
- **Residual risk:** clock skew on the API host. Mitigation: NTP.

### Information disclosure
- **Threats:** dataset listing for a user who has no grant, audit-log
  exposure to a non-admin, PHI in error responses, secret leakage in
  logs.
- **Controls:** RBAC on every read; `require_admin` for audit endpoints;
  config validator refuses placeholder secrets at production boot;
  error responses are scrubbed of stack traces in production.
- **Residual risk:** report PDFs sitting on a misconfigured S3 bucket.
  Mitigation: bucket policy review at deploy time.

### Denial of service
- **Threats:** large multipart uploads, bcrypt amplification on `/auth/login`,
  unbounded queue fan-in.
- **Controls:** `max_request_body_bytes` (default 50 MB), per-route
  rate limits, Celery queue with bounded retries, Slurm submission
  funneled through one SSH connection at a time.
- **Residual risk:** sustained L4 flood. Mitigation: front with a CDN /
  rate-limiter (Cloudflare, AWS WAF, institutional proxy).

### Elevation of privilege
- **Threats:** researcher → admin pivot, PAT → JWT pivot, dataset grant
  bypass.
- **Controls:** every write-path route declares
  `Depends(require_role("admin"))` or `Depends(require_role("researcher"))`;
  PAT auth path cannot satisfy `require_jwt` (anti-pivot); Atlas grants
  are checked server-side per request, never trusted from the client.
- **Residual risk:** initial admin bootstrap is intentionally
  publicly reachable when no admin exists. Mitigation: first-admin
  bootstrap UI is gated by "zero admins in DB" check and disabled
  thereafter.

## What is explicitly out of scope

- **PHI inside the DB.** Veritas stores metadata, references, hashes —
  never patient pixels. PHI lives on the cluster filesystem.
- **Cluster-side controls.** OS-level hardening, SELinux, FreeSurfer
  license handling, and Apptainer rootless mode are the cluster
  admin's job. Veritas calls `sbatch` over SSH; it does not assume
  anything beyond that.
- **End-to-end encryption of report artifacts at rest.** Operators
  who need this should configure the S3 backend with SSE-KMS or
  encrypt the local artifact volume at the LUKS layer.

## Known gaps (tracked, not yet fixed)

- OIDC SSO is scaffolded (`auth_mode=oidc` config knob exists) but not
  wired to a real IdP. Local auth is the only supported mode in 0.1.0.
- No external penetration test has been performed. Internal review
  only.
- No formal disaster-recovery drill has been performed against the
  Postgres backup script.

These three are explicit pre-`1.0.0` items.
