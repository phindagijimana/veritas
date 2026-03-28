# Pipeline: code → Docker image → registry → YAML → job → user reports

This is the intended Veritas workflow when **you** own the container.

## 1. Define the pipeline

Implement your inference or scoring code (e.g. Python entrypoint), with a clear **input** layout (BIDS, nifti, etc.) and **output** paths (metrics JSON, PDF, CSV, masks).

## 2. Build a Docker image

Write a `Dockerfile` that installs dependencies and sets `ENTRYPOINT` / `CMD` to your runner (e.g. `python /app/run.py`). Build locally:

```bash
docker build -t my-biomarker:v1 .
```

## 3. Push to your registry

Tag and push the image to **your** namespace (example: Docker Hub user `phindagijimana321`):

```bash
docker tag my-biomarker:v1 docker.io/phindagijimana321/my-biomarker:v1
docker push docker.io/phindagijimana321/my-biomarker:v1
```

Use the same reference in Veritas (and on compute nodes: cluster must be allowed to `docker pull` / `apptainer pull` that image).

## 4. Describe it in Veritas pipeline YAML

Register a pipeline whose YAML includes:

| Field | Role |
|--------|------|
| `image` | **Exactly** the image you pushed, e.g. `docker.io/phindagijimana321/my-biomarker:v1` — this is the container Slurm runs. |
| `entrypoint` | How the container is invoked (may match image metadata). |
| `inputs` / `outputs` | Contract: what the job mounts and what artifacts exist after the run. |
| `resources` | CPU (and optional GPU/memory in job payload). |
| `reports` (optional) | **User-facing** deliverables: names and types (PDF, JSON, CSV) that operations attach when notifying the requester. |

Validate with **`POST /api/v1/pipelines/validate`** before saving.

Example file: `veritas/veritas_full_repo/backend/pipelines/examples/biomarker-dockerhub-namespace.yaml`.

## 5. Submit the job

Use **`POST /api/v1/jobs/submit/{request_id}`** with `pipeline` set to that **same image string** (and dataset, partition, resources). Veritas generates the Slurm wrapper that runs your container and collects artifacts under the job layout.

## 6. Reports to the user

After the job completes, **outputs** from the YAML (and any `reports` you listed) map to the files operators send through the platform (PDF summary, `metrics.json`, `results.csv`). The admin UI and APIs are the place to attach those URLs or bundles to the evaluation request and notify the requester.

**MELD / special images:** For `runtime_profile: meld_graph`, the same idea applies: the `image` is still the container reference; extra `plugin` blocks describe licenses and env. Generic pipelines use the standard `docker run` style command from Veritas.
