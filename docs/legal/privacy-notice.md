# Privacy notice — TEMPLATE (REQUIRES COUNSEL REVIEW)

> **Maintainer note:** Draft. Not legal advice. Replace bracketed
> placeholders. URMC counsel + privacy office must red-line before this
> is shown to a user.

**Effective date:** _[INSERT DATE]_
**Operator:** _[INSTITUTION NAME] (the "Operator")_

This notice explains what the Veritas & Atlas Data API ("the Service")
collects, how that information is used, and how long it is kept.

## 1. Data we collect about you

**Account data**
- Email address.
- Name (optional).
- Role (admin / researcher).
- Password (stored only as a bcrypt hash; the Operator cannot recover
  your plaintext password).
- Personal access token hashes (SHA-256 of the issued secret) and
  labels.

**Telemetry**
- Source IP address and user agent for every API request.
- Audit log entries for every state-changing request (action, target
  object, timestamp).
- Application metrics (Prometheus): aggregate request counts,
  latencies, error counts. These metrics are not tied to individual
  user identity.

**No clinical data**
- The Service does not store identifiable patient data in its
  application database. Clinical imaging stays on the HPC cluster
  filesystem governed by the relevant data-use agreement.

## 2. Why we collect it

- **Authentication and access control** — account data lets us
  authenticate you and enforce RBAC.
- **Audit and compliance** — the audit log supports incident
  investigation, IRB inquiries, and institutional record-retention
  obligations.
- **Operations** — telemetry supports performance monitoring,
  capacity planning, and security investigations.
- **Notifications** — your email address is used to send notifications
  about jobs you submit, password resets, and material policy changes.

## 3. Lawful basis

Use of the Service is conditioned on your acceptance of the Terms of
Service. Processing is governed by [INSTITUTION NAME]'s research
records policy and, where applicable, the HIPAA Privacy Rule, FERPA,
45 CFR §46 (Common Rule), and [STATE LAW].

## 4. Who we share it with

- **Inside [INSTITUTION NAME]:** authorized administrators, the
  internal security team during a confirmed incident, and the IRB on
  formal request.
- **Outside [INSTITUTION NAME]:**
  - The Pennsieve service (https://app.pennsieve.io), when you trigger
    a dataset staging action that requires a Pennsieve manifest.
    Only the dataset identifier and an institutional API token are
    sent; no user-level data is shared.
  - No third parties for advertising or analytics.

## 5. How long we keep it

| Category               | Retention                                |
|------------------------|------------------------------------------|
| Account record         | Until you request deletion or your institutional affiliation ends; then archived for [N] years per institutional records policy |
| Personal access tokens | Until you revoke, or 365 days, whichever comes first |
| Audit log              | [N] years (configurable via `scripts/audit_retention.sh`; default is to keep, prune is an operator choice) |
| Application metrics    | 30 days at full resolution; 1 year downsampled |
| Notifications          | 90 days |
| Report artifacts       | Per the artifact-retention policy of the registered dataset |

## 6. Your rights

You may:

- Request a copy of your account record and audit log entries.
- Request correction of an inaccurate account record.
- Request deletion of your account record (the audit log of past
  actions is retained for institutional records purposes; this is
  documented in §5).
- Revoke any personal access token from the API tokens panel.

Submit requests to _[DATA STEWARD CONTACT]_.

## 7. Security

The Service uses TLS in transit (managed by the Operator's reverse
proxy / load balancer), bcrypt for password storage, SHA-256 hashing
for tokens at rest, strict RBAC, application-layer rate limits, and an
append-only audit log. The architecture diagram lives in
`docs/architecture/`; the threat model lives in `docs/threat-model.md`.
This is not a substitute for the Operator's institutional security
posture (BAAs, network segmentation, key management, vulnerability
management).

## 8. Children

The Service is not directed at individuals under 18. No account is
provisioned for a user who has not been credentialed through the
Operator's identity provider.

## 9. Changes to this notice

Material changes will be announced through the Service's in-app
notification system at least 14 days before they take effect.

## 10. Contact

Questions: _[DATA STEWARD CONTACT]_.
Security: _[SECURITY CONTACT — see SECURITY.md]_.
Privacy office: _[PRIVACY OFFICE CONTACT]_.

---

_Generated from `docs/legal/privacy-notice.md` in the Veritas repository.
Last revised by privacy office: [DATE / NAME]._
