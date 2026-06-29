---
title: 'Veritas & Atlas Data API: a reproducible, audit-grade evaluation surface for clinical AI biomarkers on HPC'
tags:
  - Python
  - FastAPI
  - clinical AI
  - biomarker evaluation
  - reproducibility
  - HPC
  - Slurm
  - neuroimaging
  - epilepsy
authors:
  - name: Philbert Ndagijimana
    orcid: 0000-0000-0000-0000
    corresponding: true
    affiliation: 1
affiliations:
  - name: University of Rochester Medical Center, Rochester, NY, USA
    index: 1
date: 29 June 2026
bibliography: paper.bib
---

# Summary

`Veritas` is a web service and researcher portal that turns a containerized
clinical-AI pipeline (for example, the MELD Graph FCD detector for
epilepsy [@spitzer2022meld]) into a request-tracked, auditable
evaluation. A researcher selects a registered pipeline, picks a dataset
made available through the companion `Atlas Data API`, submits an
evaluation request, and receives a signed report bundle (PDF + JSON +
CSV + HTML + run manifest) with a per-request append-only audit trail.
Veritas owns auth, RBAC, personal access tokens, an in-app + email
notification fan-out, a per-disease leaderboard, and an admin surface
(users, dataset governance, audit log export); Atlas owns dataset
metadata, staging requests, grants, and Pennsieve integration. Jobs
execute on a Slurm cluster the API reaches over SSH, using Apptainer or
Docker as the container runtime. The platform ships a versioned OpenAPI
contract, a smoke-test CI path, a synthetic BIDS [@gorgolewski2016bids]
fixture so reviewers can boot without holding clinical data-use
agreements, and a Prometheus metrics surface for operations.

# Statement of need

There is no shortage of tools that *run* neuroimaging pipelines.
NiPype [@gorgolewski2011nipype] composes them in Python; BIDS Apps
[@gorgolewski2017bidsapps] standardize their container interface;
Snakemake [@molder2021snakemake] schedules their DAGs on clusters.
MedPerf [@karargyris2023medperf] coordinates federated benchmarking
across sites. MONAI Label [@diazpinto2024monailabel] solves AI-assisted
annotation. FUTURE-AI [@lekadir2025futureai] gives the *principles* a
trustworthy clinical-AI program should satisfy.

None of those tools answer the day-to-day questions a clinical research
site actually faces when handing a pre-trained model to a clinician or
trainee: *who is authorized to submit, against which consented dataset,
with what report, where the audit log lives, who is notified when a
12-hour Slurm job finishes, and how to revoke access without redeploying
the cluster.* Sites either glue together bespoke wrappers around a
queue manager and a spreadsheet, or they don't run evaluations on real
data at all.

Veritas + Atlas fill that gap. They sit between a workflow runner and a
clinical-AI quality program: a researcher portal in front, a Slurm
cluster behind, with RBAC, personal access tokens, an append-only audit
log, a per-disease leaderboard, in-app + email notifications, dataset
staging, and a clean OpenAPI surface between them. The intended users
are clinical informatics teams who already have HPC and one or more
containerized models but lack the safe, reproducible, multi-user
front door that a journal reviewer (or an institutional auditor)
will recognize as adequate.

# Functionality

Veritas exposes 61 endpoints under `/api/v1/` (full contract in
`docs/api/openapi-v0.1.0.json`). Highlights:

- **Auth & access control.** Bcrypt-hashed local accounts, JWT for
  interactive sessions, prefixed personal access tokens (`veritas_pat_…`)
  for programmatic use, an admin-only `require_jwt` anti-pivot on
  token mint, role-based guards on every write path, and an
  audit-logged password-reset path.
- **Pipeline + dataset model.** Operators register a pipeline by
  declaring the container image, the runtime profile (Docker /
  Apptainer / Singularity), a sample input descriptor, and the resource
  envelope. Datasets are registered separately through Atlas, with
  metadata, consent flags, and a staging recipe.
- **Evaluation lifecycle.** A request transitions through
  `submitted → staged → queued → running → completed | failed | cancelled`,
  driven by a Celery + Redis worker plus a Slurm poller. Each state
  change is timestamped, appended to the audit log, and (optionally)
  emailed.
- **Reports.** On completion, a signed bundle (PDF / JSON / CSV / HTML
  / `run_manifest.json`) is written to the configured artifact backend
  (local FS or S3-compatible) and surfaced through the UI with a
  download button.
- **Leaderboard.** Researchers can opt in to publish a row per
  completed run, grouped by disease + dataset.
- **Operability.** Prometheus metrics, a Grafana dashboard, an audit-log
  retention script, a Postgres backup script, and a deploy runbook
  (`docs/VERITAS_PRODUCTION.md`) accompany the code.

The companion `Atlas Data API` handles dataset registration, grants,
staging, and Pennsieve manifest integration. It can run standalone for
sites that want only the data-access surface.

# Architecture

\autoref{fig:architecture} (see `docs/architecture/veritas-architecture.md`)
shows the four logical layers: a React + Vite UI, a FastAPI + SQLAlchemy
API with Audit and Prometheus middleware, a Celery + Redis queue, and
an SSH/Slurm submission path. All long-running work flows through the
queue, and all writes flow through the audit log.

# Quality control

The repository ships 126 backend pytest cases, 29 Atlas-side pytest
cases, 7 Vitest frontend cases, and a Playwright-driven UI smoke. A
GitHub Actions workflow runs SQLite + mock-HPC integration tests on
every push. Load-test results from a 25-user / 60-second `locust` run
against a SQLite + single-worker baseline are in
`docs/benchmarks/loadtest-results.md`; a Postgres + gunicorn baseline is
the next planned benchmark.

# Acknowledgements

We thank the MELD team [@spitzer2022meld] for the FCD detection
pipeline used as the first end-to-end target, and the BIDS community
[@gorgolewski2016bids] for the dataset convention that made the
synthetic fixture possible.

# References
