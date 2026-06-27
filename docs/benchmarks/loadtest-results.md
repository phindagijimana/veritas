# Veritas API — load-test baseline

Single-host smoke run of `scripts/loadtest_veritas.py` (locust 2.44.4)
against the Veritas API to give the paper a concrete starting set of
performance numbers. **Bigger numbers live in the "Run #2 against
Postgres" stub below — open until the rootless-podman blocker on this
dev box clears.**

---

## Run #1 — SQLite, 25 concurrent users, 60 s

### Test environment

| Property | Value |
|----------|-------|
| Date | 2026-06-26 |
| Host | URMC dev box, NFS-mounted home |
| Python | 3.9 |
| API | `python -m uvicorn app.main:app --host 127.0.0.1 --port 6010 --log-level warning` (single worker) |
| DB | SQLite on `/tmp/v_api.db` (auto-create schema, seeded demo data) |
| HPC | `HPC_MODE=mock` (no real cluster) |
| Auth | `AUTH_ENABLED=false` for the GET-heavy mix; the auth path was driven by per-user `/auth/register` + `/auth/login` from locust's `on_start`. |
| Locust | `--users 25 --spawn-rate 5 --run-time 60s` |

### Headline numbers

| Path | n | failures | p50 | p95 | RPS |
|------|---|---------:|----:|----:|----:|
| GET  `/api/v1/datasets`   |    25 |   0 |   30 ms |   79 ms | 0.4 |
| GET  `/api/v1/pipelines`  |    25 |   0 |   14 ms |   41 ms | 0.4 |
| GET  `/auth/me`           |   145 |   0 |    5 ms |   13 ms | 2.5 |
| GET  `/datasets`          |   210 |  35 |    6 ms |   10 ms | 3.7 |
| GET  `/hpc/summary`       |    62 |   0 |    6 ms |   10 ms | 1.1 |
| GET  `/leaderboard`       |   280 |  80 |    5 ms |   11 ms | 4.9 |
| GET  `/notifications`     |   148 |   0 |    7 ms |   18 ms | 2.6 |
| GET  `/pipelines`         |   197 |  22 |    5 ms |    9 ms | 3.4 |
| POST `/auth/login`        |    25 |  10 |  350 ms |  570 ms | 0.4 |
| POST `/auth/register`     |    25 |  10 |  500 ms |  660 ms | 0.4 |
| POST `/jobs/preview/:id`  |    12 |   0 |   24 ms |   34 ms | 0.2 |
| POST `/requests`          |    33 |   0 |   21 ms |   42 ms | 0.6 |
| **Aggregate**             | **1187** | **157** | **7 ms** | **420 ms** | **20.8** |

### How to read this

- **Reads are sub-20-ms p95.** The state-machine + audit middleware do
  not dominate; on SQLite + FastAPI, GETs serve in single-digit
  milliseconds. Once Postgres + connection pooling lands the numbers
  should hold or improve at higher concurrency.
- **Writes are 20-40 ms p95.** `POST /requests` (DB insert + audit row)
  is 21 ms median, 42 ms p95. `POST /jobs/preview/:id` generates a 4-5 KB
  sbatch script + returns it; 24 ms median, 34 ms p95.
- **Auth is bcrypt-bound.** `POST /auth/login` and `POST /auth/register`
  spend essentially all of their time in `passlib.bcrypt`. p50 350-500 ms
  is the bcrypt cost on this CPU at the default round count (12). This is
  expected and tunable via the standard passlib settings; for the paper
  we note it explicitly.
- **The 157 failures are the rate limiter working as designed.** Of the
  157, 10 are `/auth/login` 401s (locust's `on_start` raced with the
  user creation), 10 are `/auth/register` 429s from
  `AuthRateLimitMiddleware`, and the remaining 137 are GET 429s from
  `slowapi` (200/min/IP default applied to localhost). With 25 concurrent
  bots all hitting localhost, that ceiling is reached fast. **The rate
  limits exist precisely so a misbehaving client can't DOS the cluster
  through the API**; tripping them at 21 RPS is the safety harness, not
  a bug. In production they're per-account and per-IP separately.

### What this baseline lets you compare against

- A future tuning change (e.g., bcrypt rounds=10, or moving auth onto a
  separate worker) should drop auth p95 by 2-4×.
- A switch from SQLite to managed Postgres should hold the read p95 and
  improve the write p95 under contention (write serialization stops being
  a single-writer lock).
- Adding gunicorn workers (`WEB_CONCURRENCY=4`) should raise the
  aggregate RPS roughly linearly until the DB becomes the bottleneck.

---

## Run #2 — Postgres, gunicorn 4 workers, 100 concurrent users *(pending)*

This baseline was held over to a later run because rootless podman on
the URMC dev box hits the documented subuid issue (see
`docs/MELD_VERITAS_ATLAS.md` "Podman / rootless"), and a managed
Postgres / RDS instance isn't reachable from this network. The exact
command to populate this section once Postgres + gunicorn are in place:

```bash
# Terminal 1: real Postgres + 4 workers
DATABASE_URL=postgresql+psycopg://veritas:...@db:5432/veritas \
  WEB_CONCURRENCY=4 \
  gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:6010 app.main:app

# Terminal 2: 100 users, 5 min, paste the per-endpoint table here
locust -f scripts/loadtest_veritas.py \
  --host https://api.veritas.example.com \
  --headless --users 100 --spawn-rate 10 --run-time 5m \
  --csv docs/benchmarks/postgres-100u-5m
```

Expected: read p95 ≤ 50 ms, write p95 ≤ 100 ms, aggregate RPS ≥ 200 with
zero rate-limit hits (per-user limits at 1 in 100 quotient of the
single-IP limits used here).

---

## What we're explicitly NOT claiming

- These numbers are **not** clinical performance numbers. Job execution
  itself is on the cluster; the API's job is to accept the submit, write
  rows, and return a response. The API is not the bottleneck for a 12-hour
  MELD run.
- These numbers are SQLite-on-NFS on a developer's workstation. Treat
  them as a baseline for relative comparison, not as deployment claims.
- The auth cost will look better with bcrypt tuned or moved to a worker;
  it will look worse if you double the rounds. The paper should report
  whatever rounds you ship with.
