#!/usr/bin/env python3
"""
End-to-end local smoke: Atlas + Veritas (live) — list datasets, staging request, manifest, Phase C.

Prerequisites:
  - Postgres/Redis from scripts/dev-stack.sh (or equivalent)
  - alembic upgrade head for both apps
  - Atlas on ATLAS_URL (default http://127.0.0.1:8000), Veritas on VERITAS_URL (default http://127.0.0.1:6000)
  - Matching secrets: ATLAS_VERITAS_CLIENT_SECRET (Atlas) == ATLAS_API_CLIENT_SECRET (Veritas)

Usage:
  export ATLAS_VERITAS_CLIENT_SECRET=dev-shared-atlas-veritas-secret
  export ATLAS_API_CLIENT_SECRET="$ATLAS_VERITAS_CLIENT_SECRET"
  # Veritas process needs: ATLAS_INTEGRATION_MODE=live ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1
  python3 scripts/full_local_e2e.py

Optional:
  DATASET_ID=ideas  REQUEST_ID=e2e-local-1  python3 scripts/full_local_e2e.py

On success, writes .veritas_last_e2e.json at the repo root (staging + phase_c) for scripts/meld_veritas_full_run.sh.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# Written for downstream steps (e.g. MELD bridge script)
E2E_ARTIFACT = Path(__file__).resolve().parent.parent / ".veritas_last_e2e.json"

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)


def _env(name: str, default: str) -> str:
    return (os.environ.get(name) or "").strip() or default


def _wait_ready(
    client: httpx.Client,
    label: str,
    url: str,
    timeout_s: float = 120.0,
    interval_s: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout_s
    last_err = ""
    while time.monotonic() < deadline:
        try:
            r = client.get(url, timeout=5.0)
            if r.status_code == 200:
                print(f"  OK {label}: {url}")
                return
            last_err = f"{r.status_code} {r.text[:200]}"
        except Exception as exc:
            last_err = str(exc)
        print(f"  waiting for {label}... ({last_err[:80]})")
        time.sleep(interval_s)
    raise SystemExit(f"Timeout waiting for {label} at {url}. Start the API and ensure DB is up.")


def main() -> None:
    atlas_base = _env("ATLAS_URL", "http://127.0.0.1:8000").rstrip("/")
    veritas_base = _env("VERITAS_URL", "http://127.0.0.1:6000").rstrip("/")
    api_prefix = "/api/v1"
    secret = _env("ATLAS_API_CLIENT_SECRET", "") or _env("ATLAS_VERITAS_CLIENT_SECRET", "")
    if not secret:
        print(
            "Set ATLAS_API_CLIENT_SECRET or ATLAS_VERITAS_CLIENT_SECRET (must match Atlas ATLAS_VERITAS_CLIENT_SECRET).",
            file=sys.stderr,
        )
        sys.exit(1)

    client_id = _env("ATLAS_API_CLIENT_ID", "veritas")
    dataset_id = _env("DATASET_ID", "ideas")
    request_id = _env("REQUEST_ID", f"E2E-{int(time.time())}")

    headers = {
        "X-Atlas-Client-Id": client_id,
        "X-Atlas-Client-Secret": secret,
    }

    print("== Full local E2E: Atlas + Veritas (live) ==\n")
    print(f"Atlas:    {atlas_base}")
    print(f"Veritas:  {veritas_base}")
    print(f"Dataset:  {dataset_id}  Request: {request_id}\n")

    with httpx.Client(timeout=60.0) as client:
        print("1) Wait for Atlas /ready ...")
        _wait_ready(client, "Atlas", f"{atlas_base}/ready")
        print("2) Wait for Veritas /ready ...")
        _wait_ready(client, "Veritas", f"{veritas_base}{api_prefix}/ready")

        print("\n3) GET Atlas /datasets (Veritas service headers) ...")
        r = client.get(f"{atlas_base}{api_prefix}/datasets", headers=headers)
        r.raise_for_status()
        atlas_body = r.json()
        data = atlas_body.get("data") or []
        print(f"   count={atlas_body.get('count', len(data))} first={data[0].get('atlas_dataset_id') if data else 'none'}")

        print("\n4) GET Veritas /atlas/datasets (proxy) ...")
        r = client.get(f"{veritas_base}{api_prefix}/atlas/datasets")
        r.raise_for_status()
        vdata = r.json().get("data") or []
        print(f"   items={len(vdata)} first={vdata[0].get('atlas_dataset_id') if vdata else 'none'}")

        print("\n5) POST Veritas /atlas/staging/request ...")
        staging_payload: dict[str, Any] = {
            "request_id": request_id,
            "atlas_dataset_id": dataset_id,
            "purpose": "benchmark_validation",
        }
        r = client.post(
            f"{veritas_base}{api_prefix}/atlas/staging/request",
            json=staging_payload,
        )
        r.raise_for_status()
        staging_out = r.json()
        staging_block = staging_out.get("data") or {}
        st = staging_block.get("staging") or {}
        plan = staging_block.get("plan") or {}
        print(f"   atlas_staging_id={st.get('atlas_staging_id')} status={st.get('status')}")
        print(f"   staged_dataset_path={plan.get('staged_dataset_path', '')[:120]}")

        print("\n6) POST Veritas /atlas/phase-c/prepare ...")
        r = client.post(
            f"{veritas_base}{api_prefix}/atlas/phase-c/prepare",
            json={"request_id": request_id, "atlas_dataset_id": dataset_id},
        )
        r.raise_for_status()
        pc = r.json()
        print(f"   phase-c keys: {list(pc.keys())}")

        artifact = {
            "request_id": request_id,
            "atlas_dataset_id": dataset_id,
            "veritas_base": veritas_base,
            "atlas_base": atlas_base,
            "staging": staging_block,
            "phase_c": pc,
        }
        E2E_ARTIFACT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        print(f"\n   Wrote {E2E_ARTIFACT} (for MELD / automation follow-up)")

    print("\n== E2E completed successfully ==")
    print(json.dumps({"request_id": request_id, "atlas_dataset_id": dataset_id}, indent=2))


if __name__ == "__main__":
    main()
