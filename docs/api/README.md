# Versioned API contract

We snapshot the FastAPI-generated OpenAPI 3.x spec at each release tag so
clients can:

1. Pin against a known contract (and we can detect breakages in PRs).
2. Cite a stable contract in the paper / preprint without having to
   actually run the API.

## Snapshots

| File | Source | Notes |
|------|--------|-------|
| `openapi-v0.1.0.json` | `GET /openapi.json` on commit `25579fa` of the Veritas API | First versioned snapshot. 61 paths, including `/auth/*`, `/admin/users/*`, `/admin/audit/export`, `/auth/bootstrap-status` + `/auth/bootstrap-admin`, `/notifications/*`, `/jobs/*/logs`, `/reports/*/download/*/file`, and the standard CRUD surfaces. |

## How to regenerate

```bash
# Boot the API against any DB (we use SQLite for the snapshot).
cd veritas/veritas_full_repo/backend
DATABASE_URL=sqlite:////tmp/v_api.db DATABASE_AUTO_CREATE_SCHEMA=true \
  SEED_DEMO_DATA_ON_STARTUP=false AUTH_ENABLED=false HPC_MODE=mock \
  python3 -m uvicorn app.main:app --port 6010 --log-level warning &

# Wait for /health, then dump the spec.
curl -sS http://127.0.0.1:6010/openapi.json | python3 -m json.tool \
  > docs/api/openapi-v$(git describe --tags --abbrev=0 | sed 's/^v//').json
```

## Versioning policy

- **`x.y.z` semver** for the spec, tracking the API host's `info.version`
  field.
- **Major bump** (`x` → `x+1`) for any breaking change: removed endpoint,
  removed/required field, changed status-code semantics, renamed path.
- **Minor bump** (`y` → `y+1`) for any new endpoint, new optional field,
  or new response shape that doesn't affect existing clients.
- **Patch bump** for documentation-only changes (descriptions, examples,
  tag reorganisation) that don't change the JSON Schema.

## Cross-version diffs

A simple `jq` invocation surfaces breaking renames:

```bash
diff \
  <(jq -r '.paths | keys[]' docs/api/openapi-v0.1.0.json) \
  <(curl -s http://127.0.0.1:6010/openapi.json | jq -r '.paths | keys[]')
```

If we add an OpenAPI diff CI check later, it would live in
`.github/workflows/openapi-diff.yml` and run on PRs.
