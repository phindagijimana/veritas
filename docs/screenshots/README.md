# Veritas UI screenshots (for paper figures)

Curated set captured with Playwright (headless Chromium, 1280×900) against
the seeded SQLite dev API. Numbering follows the order a reader would
encounter the surfaces in a tour of the platform.

| # | File | What it shows |
|---|------|---------------|
| 01 | `01_home.png` | Landing page after sign-in, with the seven-item nav and "?" help link in the user chip. |
| 02 | `02_user_dashboard.png` | Researcher's submit-evaluation-request flow + selected-request phase timeline. |
| 03 | `03_pipeline_registered.png` | Pipeline page with the **Register pipeline** button having just succeeded — inline green success message + new entry in the live catalog. |
| 04 | `04_first_admin_bootstrap.png` | LoginGate's one-shot "Set up the first admin" form on a fresh production DB (no admins exist yet). The amber banner explains the one-shot nature. |
| 05 | `05_home_after_login.png` | Home immediately after the first admin is bootstrapped — chip shows ADMIN role. |
| 06 | `06_leaderboard.png` | Live `GET /leaderboard` rendered as per-disease tables with a Share-deep-link button per row. Two real entries from the screenshot session. |
| 07 | `07_veritas_admin.png` | Admin view including HPC connection card, Submitted requests table, **Users** panel (promote/demote, reset password with one-shot reveal), and **Audit log** panel with Export CSV / Export JSON / Refresh. |
| 08 | `08_api_tokens.png` | Personal access token management — create form, one-shot plaintext reveal, list with Revoke action. |
| 09 | `09_compare_runs.png` | Compare-runs `/compare` view with two requests' pipeline / dataset / phase / report side by side. |
| 10 | `10_help_page.png` | In-app `/help` page with the four-section walkthrough (researchers, programmatic, admins, troubleshooting). |

For higher-resolution exports for camera-ready submission, regenerate with
`/tmp/paper_screenshots.py` (committed to the dev session's transcript, not
the repo) — the script is ~50 lines and trivial to recreate.

## Reproducibility notes

- Auth on screenshots 01-03 and 06-10 was disabled (`AUTH_ENABLED=false`)
  for capture speed; the layout is identical when auth is on.
- The DB was seeded via `SEED_DEMO_DATA_ON_STARTUP=true` plus two
  synthetic leaderboard entries (`paper seed 1` and `paper seed 2`).
- The bootstrap screenshot (04) used a separate fresh DB with auth on
  and zero admin rows.
