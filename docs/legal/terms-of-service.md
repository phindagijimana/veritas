# Terms of service — TEMPLATE (REQUIRES COUNSEL REVIEW)

> **Maintainer note:** Draft. Not legal advice. Replace bracketed
> placeholders. URMC counsel must red-line before this is shown to a
> user.

**Effective date:** _[INSERT DATE]_
**Operator:** _[INSTITUTION NAME] (the "Operator")_
**Service:** the Veritas & Atlas Data API deployment hosted at
`[DEPLOYMENT URL]` (the "Service").

## 1. Acceptance

By creating or using an account on the Service, you ("User") agree to
these Terms. If you do not agree, you must not access the Service.

## 2. Eligibility

You must be:

- a research employee, trainee, faculty member, or affiliate of
  [INSTITUTION NAME], or of an institution with an executed data-use
  agreement with [INSTITUTION NAME] covering the Service; and
- credentialed by the Operator's identity provider; and
- in compliance with all institutional policies governing access to
  research data systems.

The Operator may suspend or terminate your access at any time, with or
without notice, for violation of these Terms, of institutional policy,
or of applicable law.

## 3. Authorized use

You may use the Service only for:

- evaluating registered AI / ML pipelines on registered datasets for
  which you have an explicit grant in the Atlas Data API;
- viewing and downloading reports generated from your own evaluation
  requests;
- managing your own personal access tokens.

You may not:

- attempt to access another user's data or audit-log entries except in
  your capacity as a Veritas administrator;
- attempt to bypass authentication, authorization, rate-limiting, or
  audit-logging mechanisms;
- upload identifiable patient data through any API surface (see
  §6 — Veritas processes references, not PHI);
- use the Service to evaluate pipelines that have not been registered
  and reviewed by the Operator;
- redistribute report artifacts in a way that would identify any
  research subject.

## 4. Personal access tokens (PATs)

PATs you create are credentials equivalent to your password. You are
responsible for:

- generating PATs with a unique label;
- revoking PATs you no longer need;
- not committing PATs to source control or sharing them with other
  users;
- notifying the Operator within 24 hours of any suspected PAT
  compromise.

## 5. Audit logging

The Service records every state-changing request to an append-only
audit log. Recorded fields include the requesting user, the action,
the target object, the source IP address, the user agent, and the
timestamp. The audit log is retained per §[RETENTION] of [INSTITUTION
NAME]'s research records policy. By using the Service you consent to
this logging.

## 6. Patient data

The Service is not a clinical system of record and does not store
identifiable patient data. All clinical imaging is staged on the
HPC cluster file system and accessed through the Operator-controlled
Slurm submission path. Report artifacts produced by registered
pipelines may contain de-identified summary metrics; you must not
attempt to re-identify any research subject from these artifacts.

## 7. Intellectual property

The Service software is licensed under the MIT License. Pipelines and
datasets registered on the Service remain the property of their
respective authors and the institutions that hold any applicable
licenses (e.g. the FreeSurfer license for MELD pipelines, the dataset
data-use agreement). Your use of a pipeline or dataset on the Service
does not transfer those licenses to you.

## 8. No warranty

The Service is provided "AS IS". The Operator makes no warranty of
fitness for any clinical purpose. Results from registered pipelines
are research outputs and must not be used to make clinical decisions
unless and until the relevant regulatory clearance has been obtained.

## 9. Limitation of liability

To the maximum extent permitted by [GOVERNING LAW], the Operator and
its officers, employees, and contractors are not liable for any
indirect, incidental, consequential, or punitive damages arising from
your use of the Service.

## 10. Changes

These Terms may be updated. Material changes will be announced through
the Service's in-app notification system at least 14 days before they
take effect. Continued use after the effective date constitutes
acceptance.

## 11. Contact

Questions about these Terms: _[DATA STEWARD CONTACT]_.
Security reports: _[SECURITY CONTACT — see SECURITY.md]_.

---

_Generated from `docs/legal/terms-of-service.md` in the Veritas
repository. Last revised by counsel: [DATE / NAME]._
