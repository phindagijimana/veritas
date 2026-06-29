# Data processing addendum (DPA) — TEMPLATE (REQUIRES COUNSEL REVIEW)

> **Maintainer note:** Draft. Not legal advice. Replace bracketed
> placeholders. Both contracting institutions' counsel must red-line
> before execution.

This Addendum is incorporated into the agreement (the "Agreement")
between:

- _[CONTROLLER — e.g. the dataset-holding institution]_ ("Controller"),
- _[PROCESSOR — e.g. the Veritas-operating institution]_ ("Processor"),

effective _[DATE]_.

## 1. Scope

This Addendum applies whenever the Processor uses the Veritas & Atlas
Data API ("the Service") to evaluate a registered AI / ML pipeline
against a dataset whose data-use agreement names the Controller as the
data steward.

## 2. Roles

- The Controller determines the purposes and means of processing the
  dataset for clinical research.
- The Processor operates the Service on Controller's behalf, limited
  to the activities defined in §3.

## 3. Permitted processing activities

The Processor may, **only**:

- accept evaluation requests from credentialed researchers approved by
  the Controller through Atlas grants;
- stage the dataset on the Processor's HPC cluster for the duration of
  the evaluation;
- submit the registered container to the cluster (Slurm + Apptainer)
  for execution;
- store the resulting report artifact (PDF / JSON / CSV / HTML /
  run-manifest) in the Processor-controlled storage backend;
- expose the artifact to the requesting researcher and to the
  Processor's administrators, subject to the audit log.

Any other processing requires Controller's written authorization.

## 4. Sub-processors

The Processor uses the following sub-processors:

| Sub-processor          | Purpose                                   |
|------------------------|-------------------------------------------|
| _[CLOUD PROVIDER]_     | Object storage of report artifacts (if S3 backend enabled) |
| Pennsieve              | Dataset manifest retrieval (Atlas live mode) |
| _[SMTP RELAY]_         | Email delivery of notifications           |
| _[OBSERVABILITY VENDOR, IF ANY]_ | Application metrics / logging   |

The Processor must give the Controller 30 days' notice before adding a
new sub-processor that materially changes processing locations or
categories of data handled.

## 5. Security measures

The Processor maintains, at minimum:

- TLS for all data in transit between user, API, Atlas, and HPC
  cluster.
- Encrypted-at-rest storage backend for report artifacts.
- Role-based access control (admin / researcher) with mandatory
  authentication on every request.
- Append-only audit logging of every state-changing action.
- Application-layer rate limiting on authentication endpoints.
- Bcrypt hashing for passwords; SHA-256 hashing for personal access
  tokens.
- Documented patch process (see `SECURITY.md`) with 90-day disclosure
  timeline.
- Network segmentation between the Service and the wider institutional
  network, including a documented firewall posture and SSH key
  management for cluster access.

A current architecture diagram is at `docs/architecture/`; the
formal threat model is at `docs/threat-model.md`; the most recent
internal security review summary is at
`docs/security/internal-review.md`.

## 6. Sub-processor monitoring

The Processor must:

- maintain an inventory of all sub-processors and review it at least
  annually;
- maintain executed BAAs (where applicable) with each sub-processor
  that handles any data covered by HIPAA;
- notify the Controller within 72 hours of confirmation of any
  Personal Data breach affecting the Service or any sub-processor.

## 7. Audit rights

The Controller may, with 30 days' notice, request a copy of:

- the audit log entries pertaining to the Controller's dataset;
- the Processor's internal security review summary;
- the Processor's BAA inventory;
- the Processor's sub-processor list with current contracts redacted
  for confidentiality.

The Controller may conduct an on-site audit no more than once per
calendar year.

## 8. Data return and deletion

On termination of the Agreement or at the Controller's written
request:

- All copies of the dataset are removed from the Processor's HPC
  cluster within 30 days.
- All report artifacts derived from the dataset are removed within
  90 days, retaining only an audit-log entry recording the deletion.
- The audit-log entries themselves are retained per institutional
  records policy of the Processor.

## 9. Liability and indemnification

The liability and indemnification terms of the underlying Agreement
govern, subject to any limitations imposed by [GOVERNING LAW] or the
parties' insurance policies.

## 10. Term

This Addendum is effective from the Effective Date and remains in
force for the duration of the Agreement.

---

| Party        | Name | Title | Signature | Date |
|--------------|------|-------|-----------|------|
| Controller   |      |       |           |      |
| Processor    |      |       |           |      |

_Generated from `docs/legal/data-processing-addendum.md` in the Veritas
repository. Last revised by counsel: [DATE / NAME]._
