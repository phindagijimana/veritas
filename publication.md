# Publishing Veritas & Atlas — candidate journals + what's missing

A frank assessment of where this codebase could be published as a research-software
or clinical-informatics paper, and what we'd have to add or finish for each venue
to take it seriously.

> Honest framing first: as it stands today, Veritas + Atlas is a well-engineered
> **clinical-AI biomarker validation platform** with auth, RBAC, audit, an HPC
> submission path, an Atlas dataset registry, an in-app + email notification
> system, leaderboards, a deploy guide, an ops runbook, and ~155 automated tests
> (126 Veritas + 29 Atlas) plus a Vitest UI suite. What it does **not** yet have
> is one published end-to-end clinical run, an independent validation, a real
> user cohort, or third-party benchmarks. Most journals on this list want at
> least one of those before they'll publish a software paper.

---

## Candidate journals, ranked by realistic fit

### Tier 1 — fits the codebase **as it stands today** (after 1-2 small additions)

#### 1. Journal of Open Source Software (JOSS)
- **URL:** https://joss.theoj.org/
- **Format:** ~250-1000 words; a `paper.md` + `paper.bib` lives in the repo.
- **Review style:** open, on GitHub; reviewers actually run the software.
- **Why it fits:** JOSS evaluates the **software**, not the science. They check
  that it works, is documented, is tested, has an LICENSE, and has clear
  install/usage. Veritas already passes ~all of those: tests pass, the deploy
  guide and ops runbook are committed, the README explains how to run it.
- **What we'd need to add:**
  - A `paper.md` (the JOSS template; under 1000 words).
  - A `paper.bib`.
  - A `LICENSE` file at the repo root (currently — verify whether one exists;
    JOSS rejects without it).
  - A statement of need and a "Statement of Field" — what gap Veritas fills
    vs. NiPype, BIDS Apps, Snakemake, the Clinical AI Evaluation framework, etc.
  - One reproducible example a reviewer can run end-to-end (the existing
    `scripts/test_meld_ideas_smoke.sh` works if there's a public synthetic
    BIDS subject).
- **Verdict:** ✅ realistic submission target within 2-3 weeks.

#### 2. Software Impacts (Elsevier)
- **URL:** https://www.journals.elsevier.com/software-impacts
- **Format:** 3-6 page short-form software paper + a Code Ocean / GitHub link.
- **Review style:** fast, focused on impact + reproducibility.
- **Why it fits:** Designed for research software that has demonstrable usage.
  Veritas's deploy guide, ops runbook, audit log, leaderboard, and pipeline
  registration are tangible "impacts" they like.
- **What we'd need to add:**
  - A *named* user / use case beyond "internal demo." Even one external research
    group's pipeline evaluated through Veritas counts.
  - A short "how it advances the field" section comparing to NiPype + BIDS Apps.
  - A demo video or recorded screen capture of the User Dashboard → request →
    report flow.
- **Verdict:** ✅ realistic within 4-6 weeks if we can get one external user.

#### 3. SoftwareX (Elsevier)
- **URL:** https://www.sciencedirect.com/journal/softwarex
- **Format:** Structured 4-6 page format; mandatory metadata block.
- **Review style:** peer review + reproducibility check.
- **Why it fits:** Same family as Software Impacts but slightly more academic.
  They like tools that wrap HPC submission and reproducibility, which is
  exactly the niche.
- **What we'd need to add:** same as Software Impacts, plus a documented
  reproducible benchmark (e.g., MELD-Graph numbers matching the original
  Spitzer et al. paper on the public IDEAS cohort).
- **Verdict:** ✅ realistic within ~2 months.

#### 4. Frontiers in Neuroinformatics
- **URL:** https://www.frontiersin.org/journals/neuroinformatics
- **Format:** Full-length tools paper (4-10 pages), open access (APC ~$2400).
- **Review style:** rigorous; they want demonstrable neuroinformatics value.
- **Why it fits:** Veritas's biomarker / MELD / IDEAS positioning is squarely
  in neuroinformatics. The "Atlas dataset registry + audit log + Slurm
  integration + leaderboard" framing matches papers they've published.
- **What we'd need to add:**
  - A **case study chapter** showing MELD-Graph results on IDEAS reproduced
    end-to-end through Veritas, with metrics matching the literature within
    confidence intervals.
  - Comparison table vs. NiPype, BIDS Apps, Reproschema, OHIF.
  - Architecture diagram (which we don't have committed).
  - Discussion of FAIR data principles compliance.
- **Verdict:** ✅ strong fit; needs one good case study to be competitive.

---

### Tier 2 — fits **after the externally-blocked items** land (deploy, real Slurm run, one real cohort)

#### 5. JAMIA (Journal of the American Medical Informatics Association)
- **URL:** https://academic.oup.com/jamia
- **Format:** Methods / brief communications.
- **Review style:** wants real clinical impact, not just software.
- **Why it fits:** JAMIA loves "infrastructure that makes clinical AI safer"
  papers. Veritas's audit log, RBAC, password reset, role gating, evaluation
  request → review → report workflow maps directly onto their interests.
- **What we'd need to add:**
  - Deployment at a real institution.
  - Real clinical users (researchers, clinicians) with consent / IRB if data
    is identifiable.
  - At least one **independently-evaluated pipeline** with results that have
    clinical interpretation, not just AUC numbers.
  - Comparison to other clinical AI validation frameworks already in JAMIA
    (e.g., MedPerf, MONAI Label, FUTURE-AI).
  - Compliance posture: data residency, HIPAA / GDPR position, audit
    retention policy.

#### 6. npj Digital Medicine (Nature)
- **URL:** https://www.nature.com/npjdigitalmed/
- **Format:** Full research article.
- **Review style:** highly selective; wants demonstrable patient-care impact.
- **Why it fits:** If we can position Veritas as solving the "AI-as-medical-device"
  validation gap (FDA's evolving SaMD framework + EU AI Act's "high-risk AI"
  obligations), this becomes a methods + impact paper.
- **What we'd need:** Tier 2 baseline plus a credible study showing that
  pipelines validated through Veritas show measurable improvement (e.g.,
  reduced false positives) vs. unvalidated pipelines, or that the audit
  trail caught at least one real regression in a deployed model.

#### 7. NeuroImage
- **URL:** https://www.sciencedirect.com/journal/neuroimage
- **Format:** Methods paper, ~10-15 pages.
- **Review style:** very rigorous; needs novel methodology.
- **Why it fits:** Only if we position the contribution as **methodological** —
  e.g., a reproducible benchmark protocol for epilepsy lesion detection that
  Veritas implements, with statistical validation across N runs / N sites.
- **What we'd need:** the full Tier 2 baseline plus a multi-site reproducibility
  study showing that Veritas's audit + replication infrastructure delivers
  measurably better cross-site agreement.
- **Verdict:** stretch — only realistic after a multi-institution pilot.

---

### Tier 3 — fits as **preprint or workshop** while we're building Tier 1/2

| Venue | Why |
|-------|-----|
| **arXiv (cs.CY / cs.SE)** | Drop a preprint now to establish priority; no review. |
| **medRxiv** | If we frame Veritas as a clinical-AI safety paper. |
| **MICCAI workshops** (BraTS, AutoPET, COMP) | Workshop papers accept work-in-progress with one good case study. Veritas naturally pairs with these challenge papers. |
| **CHIL (Conference on Health, Inference, and Learning)** | Open to infrastructure papers; closer to the AI/ML community. |
| **AMIA Annual Symposium** | Has an "infrastructure" track that's friendly to system papers. |
| **OHBM (Organization for Human Brain Mapping)** | Poster/abstract route while we mature the manuscript. |

---

### Tier 4 — software journals worth knowing about

| Journal | Note |
|---------|------|
| **Bioinformatics (OUP) Application Notes** | Short format, software focus. Veritas is borderline — they prefer biology-tooling over clinical-AI infrastructure, but worth a query letter. |
| **BMC Bioinformatics** | Same comment. |
| **Computer Methods and Programs in Biomedicine** | Solid mid-tier home for medical informatics tools. Fits Veritas. |
| **GigaScience** | Software + data, FAIR-leaning, open access. Fits if we pair Veritas with a curated dataset release. |
| **PLOS Computational Biology** | Software-as-method works here when paired with a real use case. Open access ($2500-ish APC). |
| **Frontiers in Digital Health** | Newer venue, faster turnaround, good fit. |

---

## Improvements required **before** any submission

### Engineering improvements (we control these)

#### Code-side, doable from here

- [ ] **LICENSE** at the repo root. Pick MIT or Apache-2.0; everything in this
      codebase is permissively-styled already. JOSS hard-requires it; all
      others recommend.
- [ ] **CITATION.cff** so GitHub renders a "Cite this repository" button.
- [ ] **Architecture diagram** committed under `docs/architecture/`. A clean
      Mermaid or draw.io export showing: researcher → UI → API → Atlas → HPC
      → reports → leaderboard, plus the auth/audit cross-cuts.
- [ ] **Public API documentation page** — link to `/api/v1/docs` from the
      Help page; consider a static export checked into the repo for
      reviewers who don't run the API.
- [ ] **Synthetic test BIDS subject** committed to a separate
      `test-data` repo or a release artifact, so reviewers can run
      `scripts/test_meld_ideas_smoke.sh` end-to-end without IDEAS credentials.
- [ ] **Comparison table** in the paper showing how Veritas differs from:
      NiPype, BIDS Apps, MONAI Label, MedPerf, fMRIPrep, MONAI Bundle, OHIF,
      FUTURE-AI guidelines, Snakemake-medical.
- [ ] **Load-test numbers** (we have the script; run it against a real
      Postgres instance and quote actual RPS / p95 numbers).
- [ ] **Reproducibility statement** in the README pointing to the deploy
      guide + ops runbook + the dev-stack script.
- [ ] **Versioned API contract** — pin a tag for the paper submission; ensure
      `/api/v1/openapi.json` is stable across the paper's revision cycle.
- [ ] **Static UI screenshots** in `docs/screenshots/` for the figures.
      (We have several in `/tmp/veritas_*_shots/` from this session.)

#### Code-side, needs externalities

- [ ] **One real end-to-end run.** MELD-Graph on a real IDEAS subject on a
      real Slurm cluster, with FreeSurfer license, GPU, and the report
      pipeline producing real metrics that match published numbers.
      Required for Tier 1 (4, 5) and all of Tier 2.
- [ ] **One external user.** At least one research group outside the authors'
      institution submitting a pipeline through Veritas. Required for
      Software Impacts, SoftwareX, JAMIA.
- [ ] **First CI run green on GitHub Actions.** Just landed in this session's
      push; verify the workflow at `https://github.com/phindagijimana/veritas/actions`.
- [ ] **Production deploy** at a stable URL. JAMIA / npj Digital Medicine
      effectively require this.

### Methodological improvements (research, not engineering)

- [ ] **Benchmark replication.** Re-run MELD-Graph on IDEAS through Veritas
      and show metrics match Spitzer et al. (2022) within published CIs.
      Required for SoftwareX, Frontiers in Neuroinformatics, NeuroImage.
- [ ] **Cross-site / multi-run reproducibility.** Same pipeline + same
      dataset, two independent runs, compare metric agreement. Veritas's
      audit log + dataset versioning is the differentiator here.
- [ ] **At least two pipelines** evaluated through Veritas (so the
      leaderboard isn't trivially populated).
- [ ] **A statistical evaluation of the audit/RBAC story.** Toy attacks
      (researcher tries to submit as admin, PAT tries to mint another PAT,
      etc.) showing the gate holds and the audit log records each attempt.
      Maps onto the "AI safety" framing for JAMIA / npj DM.

### Compliance / clinical improvements (needs people)

- [ ] **IRB / ethics review.** Required at most institutions before clinical
      data flows. JAMIA / npj DM / NeuroImage expect this in the manuscript.
- [ ] **Data governance documentation.** Where PII lives, retention,
      consent flow, right-to-deletion. We have the audit-log retention
      script; the policy doc is missing.
- [ ] **Security review.** Independent audit of auth/RBAC. Even an internal
      InfoSec sign-off helps the manuscript credibility.
- [ ] **Comparison to regulatory frameworks** — FDA SaMD action plan,
      EU AI Act high-risk obligations, ISO 14971. Cite where Veritas
      implements each one.

### Editorial improvements

- [ ] **Position the contribution clearly.** Software paper? Infrastructure
      paper? Methods paper? Each tier wants a different framing.
- [ ] **Pick one anchor case study.** Don't dilute the story across MELD +
      TBI + HS + AD. Pick MELD-Graph on IDEAS as the lead and the others
      as "also evaluated."
- [ ] **Acknowledge limitations explicitly.** Single-site, single-modality
      (MRI-anatomical), mock vs. real cluster results in different sections.
- [ ] **Open data + open code.** GitHub repo permanent, Zenodo DOI minted,
      LICENSE clear, synthetic test data downloadable.

---

## Recommended path

1. **Right now:** drop a preprint on arXiv (cs.CY) or medRxiv. Establishes
   priority while the manuscript matures.
2. **Within 2-3 weeks:** submit to **JOSS**. JOSS is fast, focused on software
   quality, and Veritas already largely meets their bar. The reviewers will
   surface engineering gaps we can fix iteratively.
3. **Within 2 months:** after one real MELD-on-IDEAS run lands, submit to
   **Software Impacts** *or* **SoftwareX** with the case study attached.
   These journals accept incremental improvements vs. a JOSS-published
   foundation.
4. **Within 6 months:** with one external user + a benchmark replication,
   target **Frontiers in Neuroinformatics**. This is the realistic upper
   bound without a multi-institution pilot.
5. **Long horizon (12+ months):** with multi-site adoption, target **JAMIA**
   or **npj Digital Medicine**.

---

## Concrete next-step task list

```
[ ] Add LICENSE (MIT) and CITATION.cff at repo root
[ ] Draft paper.md (JOSS template, ~600 words) + paper.bib
[ ] Commit architecture diagram under docs/architecture/
[ ] Commit screenshots under docs/screenshots/
[ ] Carve a synthetic BIDS test subject + tag a v0.1.0 release
[ ] Mint a Zenodo DOI from the release tag
[ ] Run scripts/loadtest_veritas.py against a real Postgres, paste numbers
[ ] Run MELD-Graph on at least one IDEAS subject through Veritas end-to-end
[ ] Write the comparison table (NiPype / BIDS Apps / MedPerf / MONAI Label /
    FUTURE-AI / Snakemake-medical) — what's the gap Veritas closes?
[ ] Open an arXiv preprint to lock priority
[ ] Submit to JOSS once paper.md + LICENSE + reproducible smoke land
```

The codebase is in better shape than most software-paper submissions get.
The gap is in the research narrative + one real clinical run, not in the
engineering. Once those land we have a credible Tier 1 paper.
