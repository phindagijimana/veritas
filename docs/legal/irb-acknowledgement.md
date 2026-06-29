# IRB acknowledgement — TEMPLATE (REQUIRES IRB REVIEW)

> **Maintainer note:** Draft. Not legal advice. Replace bracketed
> placeholders. [INSTITUTION NAME] IRB must red-line before this is
> shown to a researcher.

## Researcher acknowledgement of platform use

**Study title:** _[STUDY TITLE]_
**Principal investigator:** _[PI NAME], _[PI DEPT]_
**IRB protocol number:** _[IRB #]_
**Platform deployment:** Veritas & Atlas Data API at _[DEPLOYMENT URL]_

By signing below the PI acknowledges:

### 1. Dataset use

The dataset(s) accessed through this platform are governed by the
data-use agreement(s) listed in Atlas (see "My grants" in the
researcher portal). I have read each applicable agreement and will
abide by its terms (subject-identification limits, redistribution
limits, citation requirements, retention limits).

### 2. Pipeline use

The pipeline(s) I run on this platform are research instruments. The
report artifacts they produce are not clinical decisions and will not
be used to alter patient care unless and until separate regulatory
clearance has been obtained for that purpose under this protocol.

### 3. PHI handling

No identifiable PHI is uploaded to the platform through any API
surface. Clinical imaging remains on the institutional HPC cluster
under the access controls of the data steward. Report artifacts
contain only de-identified summary metrics and shall not be used to
attempt re-identification of any subject.

### 4. Personnel

Only personnel listed on the active IRB protocol (above) will hold
researcher accounts on this platform for this study. New personnel
will be added to the protocol before they are credentialed to the
platform. Personnel departures will result in account deactivation
within 5 business days.

### 5. Reporting

I will notify the IRB and the platform administrator within 24 hours
of becoming aware of:

- Any disclosure of dataset content outside the personnel listed
  above.
- Any compromise of a personal access token used for this study.
- Any inadvertent re-identification of a research subject.
- Any other event that would constitute an unanticipated problem
  involving risk to subjects or others under 45 CFR §46.108(a)(7).

### 6. Audit and records

I understand that every state-changing action I take on the platform
is recorded in an append-only audit log. The audit log is the system
of record for this study's platform-related activity and is subject
to the IRB's audit rights.

### 7. Withdrawal

I may discontinue use of the platform at any time. On notification,
the platform administrator will deactivate my account; the audit log
of prior actions is retained per institutional records policy.

---

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Principal Investigator |    |       |      |
| Co-Investigator        |    |       |      |
| Co-Investigator        |    |       |      |
| Co-Investigator        |    |       |      |
| Platform Administrator |    |       |      |

_Generated from `docs/legal/irb-acknowledgement.md` in the Veritas
repository. Last revised by IRB: [DATE / NAME]._
