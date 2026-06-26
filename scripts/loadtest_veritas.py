"""Locust scenario for the Veritas API.

Run:
    pip install locust
    locust -f scripts/loadtest_veritas.py \
        --host https://api.veritas.example.com \
        --users 50 --spawn-rate 5 --run-time 5m \
        --csv loadtest-out \
        VeritasUser

Auth mode: each simulated user POSTs /auth/register on start to mint a
researcher account, then uses the returned JWT for the rest of the run. If
you'd rather hit an existing account, set `LOAD_FIXED_USER=<email>` +
`LOAD_FIXED_PASSWORD=<pw>` and the user will skip registration.

What it exercises (in order of weight):
    1. GET /leaderboard            — cheap, read-mostly path
    2. GET /datasets               — read-mostly; touches DB but no joins
    3. GET /pipelines              — same
    4. POST /requests              — write; checks DB write performance
    5. POST /jobs/preview/{id}     — write; bigger compute (sbatch generation)
    6. GET /notifications          — typical user polling cadence
    7. GET /auth/me                — JWT verify cost

Reads outweigh writes 10:1, matching the real read-mostly clinical UI.

Baseline rule of thumb on a single 4-CPU API host with Postgres on the same
box and HPC_MODE=mock: ~150 RPS sustained, p95 latency under 250 ms. Numbers
will differ wildly with a real Slurm cluster in the loop — preview generates
a 4 KB sbatch with no real submission, so the write side here is the
fast-path, not the slow path.
"""
from __future__ import annotations

import os
import random
import time
import uuid

from locust import HttpUser, between, events, task


# ───────────── helpers ─────────────


def _unique_email() -> str:
    """A monotonically-unique email so registration succeeds across runs."""
    return f"locust-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}@loadtest.local"


def _strong_password() -> str:
    return uuid.uuid4().hex + "Aa!1"


# ───────────── user class ─────────────


class VeritasUser(HttpUser):
    """One simulated researcher hitting the Veritas API."""

    wait_time = between(0.5, 2.0)  # human-ish think time
    abstract = False

    fixed_email = os.environ.get("LOAD_FIXED_USER", "").strip()
    fixed_password = os.environ.get("LOAD_FIXED_PASSWORD", "").strip()

    def on_start(self):
        """Authenticate. Either reuse a fixed account or register a fresh one."""
        if self.fixed_email and self.fixed_password:
            email, password = self.fixed_email, self.fixed_password
        else:
            email, password = _unique_email(), _strong_password()
            with self.client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": password, "full_name": "Locust Bot"},
                name="POST /auth/register",
                catch_response=True,
            ) as r:
                if r.status_code in (200, 201):
                    r.success()
                else:
                    r.failure(f"register {r.status_code}: {r.text[:140]}")

        with self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="POST /auth/login",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                token = r.json().get("access_token")
                if not token:
                    r.failure("login 200 but no access_token in body")
                self.client.headers.update({"Authorization": f"Bearer {token}"})
                r.success()
            else:
                r.failure(f"login {r.status_code}: {r.text[:140]}")

        # Cache some IDs for later writes; tolerate empty seeds.
        ds = self._safe_get_list("/api/v1/datasets")
        pipes = self._safe_get_list("/api/v1/pipelines")
        self.dataset_code = (ds[0].get("code") if ds else None) or "IDEAS"
        self.pipeline_name = (pipes[0].get("name") if pipes else None) or "meld-graph-fcd"

    def _safe_get_list(self, path: str) -> list:
        try:
            r = self.client.get(path, name=f"GET {path}")
            if r.status_code == 200:
                return r.json().get("data", []) or []
        except Exception:
            pass
        return []

    # ───── read-mostly tasks (weight = task() arg) ─────

    @task(8)
    def list_leaderboard(self):
        self.client.get("/api/v1/leaderboard", name="GET /leaderboard")

    @task(6)
    def list_datasets(self):
        self.client.get("/api/v1/datasets", name="GET /datasets")

    @task(6)
    def list_pipelines(self):
        self.client.get("/api/v1/pipelines", name="GET /pipelines")

    @task(4)
    def whoami(self):
        self.client.get("/api/v1/auth/me", name="GET /auth/me")

    @task(4)
    def poll_notifications(self):
        self.client.get("/api/v1/notifications?unread_only=true&limit=20", name="GET /notifications")

    @task(2)
    def hpc_summary(self):
        # Tolerated 401 in case the deployment hides this from researchers.
        with self.client.get("/api/v1/hpc/summary", name="GET /hpc/summary", catch_response=True) as r:
            if r.status_code in (200, 401, 403):
                r.success()
            else:
                r.failure(f"unexpected {r.status_code}")

    # ───── write tasks (rarer) ─────

    @task(1)
    def create_request(self):
        body = {
            "datasets": [self.dataset_code],
            "pipeline": self.pipeline_name,
            "description": f"loadtest {random.randint(0, 1_000_000)}",
        }
        with self.client.post(
            "/api/v1/requests", json=body, name="POST /requests", catch_response=True
        ) as r:
            if r.status_code in (200, 201):
                r.success()
                self.last_request_id = r.json().get("data", {}).get("id")
            elif r.status_code in (400, 422):
                # Likely the deployment doesn't seed datasets/pipelines; don't drown the run in red.
                r.success()
                self.last_request_id = None
            else:
                r.failure(f"requests {r.status_code}: {r.text[:140]}")

    @task(1)
    def preview_job(self):
        rid = getattr(self, "last_request_id", None)
        if not rid:
            return
        body = {
            "job_name": f"lt-{random.randint(0, 999999)}",
            "pipeline": "docker.io/example:1",
            "pipeline_name": self.pipeline_name,
            "dataset": self.dataset_code,
            "partition": "gpu",
            "resources": {"gpu": 1, "cpu": 16, "memory_gb": 64, "wall_time": "08:00:00"},
            "runtime_profile": "meld_graph",
            "meld_subject_id": "sub-001",
        }
        with self.client.post(
            f"/api/v1/jobs/preview/{rid}",
            json=body,
            name="POST /jobs/preview/{request_id}",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 400, 422):
                # 400/422 happen if the seeded pipeline doesn't match runtime_profile
                # — still a successful API round-trip from a latency perspective.
                r.success()
            else:
                r.failure(f"preview {r.status_code}: {r.text[:140]}")


# Print a summary that's easy to paste into the runbook after each run.
@events.quitting.add_listener
def _print_summary(environment, **_):
    stats = environment.stats
    print()
    print("=" * 60)
    print("Locust summary")
    print("=" * 60)
    for name, stat in sorted(stats.entries.items()):
        method = name[0]
        path = name[1]
        print(
            f"  {method:6} {path:40} "
            f"reqs={stat.num_requests:5d} fails={stat.num_failures:4d} "
            f"med={stat.median_response_time:5d}ms "
            f"p95={int(stat.get_response_time_percentile(0.95) or 0):5d}ms "
            f"rps={stat.total_rps:6.1f}"
        )
    total = stats.total
    print(
        f"  TOTAL  {' ':40} "
        f"reqs={total.num_requests:5d} fails={total.num_failures:4d} "
        f"rps={total.total_rps:6.1f}"
    )
