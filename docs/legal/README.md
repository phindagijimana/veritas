# Legal templates — REQUIRES COUNSEL REVIEW

The documents in this directory are **drafts** prepared by the
maintainer for institutional / counsel red-line. They are **not legal
advice** and must not be deployed as-is.

| File | Purpose | Status |
|------|---------|--------|
| `terms-of-service.md` | Terms researchers agree to when accessing a Veritas deployment | Draft — needs URMC counsel review |
| `privacy-notice.md` | What Veritas + Atlas collect, store, share, and retain | Draft — needs URMC privacy + counsel review |
| `data-processing-addendum.md` | DPA template for inter-institutional data flow (e.g. dataset hosted at site A, model evaluated at site B) | Draft — needs site-specific counsel review |
| `irb-acknowledgement.md` | One-page IRB-acknowledgement form for the researcher PI | Draft — needs URMC IRB review |

## Why these exist as drafts

Reviewers (institutional, JOSS, IRB) repeatedly ask whether a clinical
research platform has *thought about* these documents. Saying "we have
not engaged counsel yet" is fine; saying "we have draft text in
`docs/legal/` ready for counsel red-line" is materially better, both
for the submission and for shortening the counsel turnaround when the
review does happen.

## What URMC counsel still has to do

- Replace bracketed placeholders (`[INSTITUTION NAME]`, `[GOVERNING LAW]`,
  `[DATA STEWARD CONTACT]`, etc.).
- Verify alignment with current HIPAA Privacy Rule and any URMC
  institutional policies.
- Verify alignment with FERPA (for trainee usage), 45 CFR §46
  (Common Rule), and any state-level health-privacy statutes for the
  deployment jurisdiction.
- Review whether Atlas's Pennsieve integration triggers
  cross-institutional data-flow obligations (likely yes — that's why
  the DPA template exists).
- Decide on the governing law / venue clauses.

## What this directory is NOT

- A legal opinion. The maintainer is a clinical informatics researcher,
  not an attorney.
- A substitute for IRB review when a deployment processes any
  identifiable data.
- An assurance that the underlying platform is HIPAA-compliant. The
  platform exposes the technical controls needed for compliance
  (RBAC, audit log, configurable retention, TLS-only, no PHI in the DB,
  signed report manifests); the *programmatic* compliance posture
  depends on how the operator deploys it and what BAAs are in place.
