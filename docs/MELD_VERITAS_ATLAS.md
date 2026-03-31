# Veritas / Atlas → MELD Graph (containerized)

This document connects the **validator** stack (Atlas staging via Veritas) with the **MELD Graph** FCD pipeline shipped as Docker images by [MELDProject/meld_graph](https://github.com/MELDProject/meld_graph).

## Platform catalog (Veritas + Atlas like any user)

On **every Veritas API startup**, the backend idempotently ensures:

- **Pipeline** `meld-graph-fcd` (`docker.io/meldproject/meld_graph:latest`, `runtime_profile: meld_graph`, `atlas_dataset_id: ideas`) is present so **`GET /api/v1/pipelines`** lists it for everyone.
- **Dataset** `code=IDEAS`, **`name=ideas`** matches Atlas `dataset_id` for **`GET /api/v1/datasets`** and job payloads.

**Atlas** exposes public datasets (including `ideas`) through the same JWT/API-key flows as other users: list datasets, request staging, and complete staging phases—no special-case “admin only” for IDEAS in the validator stack.

### MELD as a YAML plugin (FreeSurfer + MELD in one job)

The catalog pipeline `meld-graph-fcd` stores a **`plugin`** block alongside `runtime_profile: meld_graph`:

- **`plugin.type: meld_graph`** — selects the MELD runtime (BIDS prep + `new_pt_pipeline.py`, license mounts).
- **`plugin.secrets`** — basenames of **FreeSurfer** (`license.txt`) and **MELD** (`meld_license.txt`) files expected under `meld_license_host_dir` / `$MELD_LICENSE_HOST_DIR` on the compute node.
- **`plugin.container_env`** — optional; defaults to `/run/secrets/...` paths matching the official MELD image.
- **`plugin.containers`** — optional but recommended: separate **FreeSurfer** and **MELD** image references (`freesurfer`, `meld`). The generated Slurm script **runs the MELD image** using **`RUNTIME_ENGINE`**: `docker run`, or **`apptainer` / `singularity run`** with **`docker://…`** for registry images (see below). It also exports **`FREESURFER_IMAGE`** when set so operators can run recon or preprocessing in the FreeSurfer container before/around the bundled MELD step (`--fastsurfer` inside MELD still uses FS tooling in that image).

Validate with **`POST /api/v1/pipelines/validate`**. Example file: `veritas/veritas_full_repo/backend/pipelines/examples/meld-graph-fcd.yaml`.

When submitting a job, Veritas loads that YAML from the **`Pipeline`** row by matching **`pipeline_name`** (catalog name, e.g. `meld-graph-fcd`) or by **`pipeline`** image string, and embeds the resolved license mounts in the Slurm job script.

## Veritas pipeline submission (Slurm job)

When a user submits **MELD** as the pipeline image and **IDEAS** (Atlas `atlas_dataset_id=ideas`) as the dataset context, use **`POST /api/v1/jobs/submit/{request_id}`** with:

| Field | Value |
|-------|--------|
| `pipeline` | `meldproject/meld_graph:latest` (or your mirrored tag) |
| `dataset` | `ideas` (label only; staging path resolved below) |
| `runtime_profile` | `meld_graph` |
| `meld_subject_id` | BIDS subject, e.g. `sub-01` |
| `meld_session` | Optional; session folder name without `ses-` (e.g. `preop`, `2WK`) if data live under `ses-*` |
| `staged_dataset_path` | Optional absolute BIDS root on the **compute node**. If omitted, the generated job script uses `$VERITAS_STAGED_DATASET_PATH` (from Atlas staging prep), then falls back to **`meld_ideas_default_staging_path`** in Veritas settings (default `/ood/share/datasets/ideas`). |
| `pipeline_name` | Optional: Veritas **`Pipeline.name`** (e.g. `meld-graph-fcd`) so the job uses the stored YAML plugin (license file names + container env). If omitted, YAML is resolved by **`pipeline`** image match. |

**Compute node requirements:**

- `VERITAS_STAGED_DATASET_PATH` exported in the job environment after Atlas/Veritas staging (see `DatasetStagingService` / Phase B), **or** a valid `staged_dataset_path` / **`MELD_IDEAS_DEFAULT_STAGING_PATH`** in Veritas (`.env`) pointing at your BIDS root (e.g. a local `bids_IDEAS` extract).
- Directory **`meld_license_host_dir`** in Veritas settings, or **`MELD_LICENSE_HOST_DIR`** on the node, containing **`license.txt`** (FreeSurfer) and **`meld_license.txt`** (MELD).

Veritas generates a **bash** runtime script (T1-only BIDS config, `--fastsurfer`) and embeds it in the Slurm wrapper via **base64** so multiline MELD commands are safe.

### `RUNTIME_ENGINE` (Docker vs Apptainer / Singularity on HPC)

Set **`RUNTIME_ENGINE`** in the Veritas API (`backend/.env`) to **`docker`** (default), **`apptainer`**, or **`singularity`**. The first is for nodes with Docker; the latter two generate Slurm scripts that use **`apptainer run`** or **`singularity run`** with **`docker://registry/image:tag`** for OCI images (or an absolute path to a local `.sif`). Pair with **`HPC_JOB_PROLOGUE_SH`** (e.g. `module load apptainer`) as required by your cluster.

Example JSON body:

```json
{
  "job_name": "meld-ideas-t1",
  "pipeline": "meldproject/meld_graph:latest",
  "pipeline_name": "meld-graph-fcd",
  "dataset": "ideas",
  "partition": "gpu",
  "runtime_profile": "meld_graph",
  "meld_subject_id": "sub-01",
  "meld_session": null,
  "staged_dataset_path": null,
  "resources": {
    "gpu": 1,
    "cpu": 16,
    "memory_gb": 64,
    "wall_time": "24:00:00"
  }
}
```

## Why this is not a single generic container

Veritas `PipelineRunnerService` builds a generic `docker run … --input /input --output /output`. The official MELD workflow uses **their** `compose.yml`, a **`meld_data`** volume layout, **FreeSurfer** and **MELD** license files, and scripts such as `prepare_classifier.py` / `new_patient_pipeline`. You bridge staging output into that layout instead of reusing the stock Veritas pipeline image string unchanged.

## End-to-end flow

1. **Run Veritas + Atlas** with matching client secrets; ensure staging writes to a path your MELD host can read (shared NFS, or same machine).
2. **Run** `./scripts/meld_veritas_full_run.sh` (or `python3 scripts/full_local_e2e.py` alone). This writes **`.veritas_last_e2e.json`** at the repo root with the staging block and `plan.staged_dataset_path`.
3. **Prepare data for MELD** per [MELD prepare data](https://meld-graph.readthedocs.io/) (BIDS layout, T1 required, FLAIR optional). Copy or bind-mount staged files into the `meld_data/input` tree expected by their release.
4. **Install/run MELD** using their Docker instructions: [Install Docker](https://meld-graph.readthedocs.io/en/latest/install_docker.html). Typical verification: from the extracted release directory, `DOCKER_USER="$(id -u):$(id -g)" docker compose run meld_graph pytest`.
5. **Prediction** follows their “run the prediction pipeline” docs (not duplicated here).

## Scripts in this repo

| Script | Role |
|--------|------|
| `scripts/full_local_e2e.py` | Live HTTP: datasets, staging request, phase-c; writes `.veritas_last_e2e.json`. |
| `scripts/meld_veritas_full_run.sh` | Runs E2E, prints staged path, optionally `pytest` inside MELD if `MELD_GRAPH_DIR` is set. |

## Licenses in this repo

Place **two files** at the **validator repo root** (same layout as [upstream `compose.yml`](https://github.com/MELDProject/meld_graph/blob/main/compose.yml)):

| File | Purpose |
|------|---------|
| `license.txt` | FreeSurfer (`FS_LICENSE`) |
| `meld_license.txt` | MELD Graph (`MELD_LICENSE`) |

They are listed in `.gitignore` so they are not committed. `scripts/meld-compose.validator.yml` mounts them as Docker secrets from `${VALIDATOR_ROOT}`; `scripts/meld_veritas_full_run.sh` sets `VALIDATOR_ROOT` automatically.

## Prerequisites (upstream)

- **Registration / license**: MELD Graph v2.2.4+ expects a license file; see the [project README](https://github.com/MELDProject/meld_graph).
- **Model weights**: Automated download may fail; see [issue #102](https://github.com/MELDProject/meld_graph/issues/102) for manual Figshare workaround.
- **GPU**: Optional; `meldproject/meld_graph` tags include GPU variants for large VRAM setups.
- **Harmonisation**: Recommended for new scanners (separate MELD step).

## Environment quick reference

```bash
export ATLAS_API_CLIENT_SECRET=...   # must match Atlas ATLAS_VERITAS_CLIENT_SECRET
./scripts/meld_veritas_full_run.sh

# MELD pytest only (licenses in repo root; no meld_graph clone required)
RUN_E2E=0 MELD_VERIFY=1 ./scripts/meld_veritas_full_run.sh

# Optional: use upstream tree — licenses are symlinked from this repo into MELD_GRAPH_DIR
export MELD_GRAPH_DIR=/path/to/extracted/meld_graph
RUN_E2E=0 MELD_VERIFY=1 MELD_PULL=1 ./scripts/meld_veritas_full_run.sh
```

## IDEAS dataset — T1-only MELD run

Atlas seeds `ideas` with secondary path **`/ood/share/datasets/ideas`** (BIDS on your OOD/HPC mirror). On the machine where Docker and the data live:

1. Ensure **`license.txt`** and **`meld_license.txt`** are in the validator repo root.
2. Point **`IDEAS_BIDS_ROOT`** at the IDEAS BIDS root (or a Veritas-staged copy of the same tree).
3. Run:

```bash
export IDEAS_BIDS_ROOT=/ood/share/datasets/ideas   # or your staged path
export SUBJECT=sub-XXXXX                           # optional — default: first T1w subject
./scripts/meld_run_ideas_t1.sh
```

This runs [`new_pt_pipeline.py`](https://meld-graph.readthedocs.io/en/latest/run_prediction_pipeline.html) with **`--fastsurfer`** (T1 primary; no FLAIR in `meld_bids_config.json`). Outputs go under `meld_docker_data/output/` per upstream layout.

To only prepare `input/` without starting Docker:

```bash
python3 scripts/meld_prepare_bids_input.py --bids-root "$IDEAS_BIDS_ROOT" --reset-input
```

### Smoke test (minimal fixture)

```bash
./scripts/test_meld_ideas_smoke.sh
```

Defaults to `scripts/fixtures/ideas_minimal_bids` (one subject, placeholder T1w) so you can verify **prepare/link + JSON** without an IDEAS mount. Set **`IDEAS_BIDS_ROOT`** to a real IDEAS path when available. **`RUN_MELD_CONTAINER=1`** runs the MELD container after prepare (needs working Docker and valid NIfTI for a real prediction).

### Podman / rootless image pulls

Compose files use fully qualified names (e.g. `docker.io/meldproject/meld_graph:latest`). If you still see **`insufficient UIDs or GIDs`** when pulling, your login is missing **`/etc/subuid`** and **`/etc/subgid`** entries (common on LDAP names like `user@realm`).

**Fix (one-time, sudo):** from the repo root run:

```bash
sudo ./scripts/fix_podman_rootless_subuid.sh
```

Then **log out and back in** (or a new SSH session), run **`podman system migrate`**, and retry. `scripts/dev-stack.sh up` checks this when the `docker` CLI is Podman and exits with the same hint.

**Alternative (no Podman/Docker):** run MELD with **Apptainer** — same pipeline as `docker compose`, but pulls/runs the OCI image via `apptainer` (often available on HPC login nodes):

```bash
export IDEAS_BIDS_ROOT=/path/to/bids_IDEAS
export APPTAINER_TMPDIR="$PWD/meld_docker_data/.apptainer_tmp"   # not /tmp if `noexec`
mkdir -p "$APPTAINER_TMPDIR"
./scripts/meld_run_apptainer.sh
```

The script prepares `meld_docker_data/input/`, then **`apptainer pull`**s to `meld_docker_data/meld_graph.sif` (first run is slow) and **`apptainer run`** with license bind mounts. NFS xattr warnings during pull are usually harmless.

If **`apptainer pull`** fails with **`noexec` on /tmp**, set **`APPTAINER_TMPDIR`** to a directory on your home or project filesystem (as above).

Disclaimer: MELD is **research software**; see the upstream disclaimer in their repository.
