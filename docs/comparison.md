# Veritas + Atlas vs. adjacent tooling

Honest, narrow comparison against six tools / frameworks that overlap with
parts of what Veritas + Atlas do. The point is **not** to claim Veritas is
better than each — it's to map the niche we actually fill, and to make the
"why not just use X?" question answerable for a reviewer.

---

## Tools considered

1. **NiPype** — Python workflow library for neuroimaging pipelines.
   https://nipype.readthedocs.io
2. **BIDS Apps** — convention + reference implementations for Dockerized
   BIDS-format pipelines. https://bids-apps.neuroimaging.io
3. **MedPerf** — federated benchmarking framework for medical AI from MLCommons.
   https://github.com/mlcommons/medperf
4. **MONAI Label** — AI-assisted medical-image annotation server.
   https://monai.io/label.html
5. **FUTURE-AI** — a *guideline* (not a tool) for trustworthy clinical AI,
   covering fairness, universality, traceability, usability, robustness,
   and explainability. https://future-ai.eu
6. **Snakemake (with medical extensions)** — DAG-based workflow manager,
   widely used in bioinformatics, increasingly seen in medical pipelines.
   https://snakemake.readthedocs.io

---

## Feature comparison

The matrix below maps capabilities. **✔** = first-class, **○** = partial /
possible with custom glue, **—** = out of scope.

| Capability | **Veritas + Atlas** | NiPype | BIDS Apps | MedPerf | MONAI Label | FUTURE-AI | Snakemake |
|---|---|---|---|---|---|---|---|
| Define a multi-step pipeline as code | ○ (operator YAML) | ✔ | ○ (container is opaque) | — | — | guideline | ✔ |
| Submit to HPC (Slurm) from an API | ✔ (over SSH) | ○ (via plugin) | ○ (via wrappers) | ✔ | — | — | ✔ (cluster profile) |
| First-class **container** image as the unit of evaluation | ✔ | ○ | ✔ | ✔ | ✔ | guideline | ○ |
| Dataset registry with metadata + staging | ✔ (Atlas) | — | — | ✔ | ○ | guideline | — |
| Per-user / per-role **RBAC + audit log** | ✔ | — | — | ✔ (federation roles) | — | guideline | — |
| Researcher-facing **web UI** | ✔ | — (CLI) | — (CLI) | partial | ✔ | — | — |
| **In-app + email notifications** for long-running jobs | ✔ | — | — | — | — | — | — |
| **Leaderboard** + consented publishing of metrics | ✔ | — | — | ✔ | — | guideline | — |
| **Reproducibility audit** (audit log, signed report manifest) | ✔ | ○ (provenance trace) | ○ (container hash only) | ✔ | — | guideline | ○ (DAG snapshot) |
| **Pipeline-validation API** (preview / dry-run sbatch) | ✔ | — | — | — | — | — | ○ (`--dryrun`) |
| **Public REST API** with OpenAPI contract | ✔ | — (lib) | — | ✔ | ✔ | — | — |
| **Personal access tokens** + admin reset / lockout | ✔ | — | — | partial | — | guideline | — |
| **Compliance-friendly defaults** (HSTS, CORS allowlist, RBAC, audit) | ✔ | — | — | partial | — | guideline | — |
| **Federated** evaluation across sites | ○ (single API, multi-site possible) | — | — | ✔ | ○ | guideline | ○ |
| Image annotation UI | — | — | — | — | ✔ | — | — |
| Built-in active-learning loop | — | — | — | — | ✔ | guideline | — |

---

## Niche statement (for the paper)

**Veritas fills the gap between a workflow runner and a clinical-AI quality
program.** Workflow tools (Snakemake, NiPype, BIDS Apps) execute pipelines
beautifully but say nothing about *who is allowed to run them, against
which dataset, with what report, and where the audit trail lives*. MedPerf
nails the federated benchmarking story but is purpose-built for the
benchmark; it isn't a per-researcher "submit your pipeline, here's your
report" surface. FUTURE-AI gives the **principles**; Veritas is one
implementation. MONAI Label solves a different problem (annotation, not
evaluation).

A site standing up Veritas + Atlas today gets:

- A **researcher portal** (submit a request, watch it progress, download
  the PDF, share a leaderboard entry).
- A **policy enforcement layer** between that researcher and the cluster
  (RBAC, PATs, append-only audit, password reset, bootstrap).
- A **dataset access layer** (Atlas — shared secret to the platform, IRB-
  / consent-gated where applicable).
- A **clean OpenAPI surface** programmatic users can hit instead of the
  UI (so federation, CI, and notebook clients all work).

That's the slot the paper claims, and that's where each of the six tools
above doesn't quite fit.

---

## What the paper should *not* claim

- That Veritas implements better pipelines than NiPype, BIDS Apps, or
  Snakemake. It doesn't write pipelines — it runs whatever you containerize.
- That Veritas replaces MedPerf for cross-institution benchmarking. It
  doesn't — its current single-API design can support multi-site, but
  federation is not the headline.
- That Veritas implements MONAI Label's annotation loop. Different problem.
- That Veritas is itself a regulated SaMD or a substitute for one. It's
  the validation infrastructure *around* a candidate SaMD. The paper
  should map onto FDA's Predetermined Change Control Plan and FUTURE-AI
  *traceability* (T) + *robustness* (R) categories, not claim equivalence.

---

## Honest weaknesses to cite

- Single-cluster Slurm path is well-trodden; the *interesting* deployment
  question is multi-cluster, which we haven't done.
- No active-learning / annotation UI (cf. MONAI Label).
- The audit log is append-only at the application layer, not at the storage
  layer; a Postgres superuser could in principle alter rows. The retention
  script archives off-site, but bucket immutability (S3 Object Lock) is
  a deployment-side choice we recommend but don't enforce.
- OIDC is scaffolded on the Atlas side but not yet wired end-to-end.
- We have not yet run Veritas through a third-party penetration test.

---

## Suggested citations for the comparison section

```
Gorgolewski et al. (2011). NiPype: a flexible, lightweight and extensible
neuroimaging data processing framework in Python. Frontiers in Neuroinformatics.

Gorgolewski et al. (2017). BIDS Apps: improving ease of use, accessibility,
and reproducibility of neuroimaging data analysis methods. PLOS Computational
Biology.

Karargyris et al. (2023). MedPerf: open benchmarking platform for medical
artificial intelligence. Nature Machine Intelligence 5(7).

Diaz-Pinto et al. (2024). MONAI Label: A framework for AI-assisted interactive
labeling of 3D medical images. Medical Image Analysis.

Lekadir et al. (2023). FUTURE-AI: international consensus guideline for
trustworthy and deployable AI in healthcare. arXiv:2309.12325.

Köster & Rahmann (2012). Snakemake — a scalable bioinformatics workflow
engine. Bioinformatics 28(19).

Spitzer et al. (2022). Interpretable surface-based detection of focal
cortical dysplasias: a Multi-centre Epilepsy Lesion Detection study. Brain.
```
