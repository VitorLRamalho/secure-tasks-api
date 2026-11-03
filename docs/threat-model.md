# Threat model — Secure Tasks API

Method: STRIDE, applied to the application and to the pipeline that builds it. Each row names the
control that exists today, where the evidence is (a test, a pipeline gate or a line in the
[findings log](findings.md)) and what is still open.

Last reviewed: 2026-11-03 (`main` at `9b6b4e0`). Review again when an endpoint, a class of
dependency or a pipeline job is added, and at least every 90 days.

## What we protect

| Asset | Where it lives | Why it matters |
| --- | --- | --- |
| User credentials | `users.password_hash` (bcrypt, cost 12) | account takeover |
| Users' tasks | `tasks` table, SQLite file under `/data` | integrity and privacy of user data |
| `APP_JWT_SECRET` | environment of the running container; never in the repository (`.env` is git-ignored) | whoever holds it can mint a token for any user |
| The published image `ghcr.io/vitorlramalho/secure-tasks-api` | GHCR, signed with Cosign | it is what people actually run |
| CI credentials (`GITHUB_TOKEN`, OIDC token) | GitHub Actions runner, scoped per job | push to GHCR, SARIF upload, keyless signing |

## Who we defend against

| Actor | Access | Typical goal |
| --- | --- | --- |
| Anonymous client | network access to the API | guess passwords, enumerate users, crash the service |
| Authenticated malicious user | a valid account and token | read or change other users' tasks, escalate |
| Attacker who can influence a pull request (compromised dependency, hijacked action, fork) | code and workflow changes proposed to `main` | sneak a backdoor or a secret past the gates, tamper with the image |
| Attacker between the registry and the user | network | serve a modified image as if it were ours |

## Trust boundaries

```
 anonymous / authenticated client
            │  HTTPS (TLS and rate limiting belong to the reverse proxy in production)
            ▼
 ┌─ container, unprivileged user `app` ─────────────────────┐
 │  FastAPI + security-headers middleware                    │
 │    JWT HS256, 30 min  ─►  ownership check  ─►  SQLite     │
 └───────────────────────────────────────────────────────────┘

 developer ─► pull request ─► secrets | SAST | SCA+IaC | tests+fuzz ─► build, image scan, SBOM
           ─► authenticated DAST ─► main ─► GHCR: image + Cosign signature + SBOM attestation
```

## STRIDE — the application

| Category | Threat | Control in place | Evidence | Known gap |
| --- | --- | --- | --- | --- |
| **S**poofing | password guessing; stolen or forged token | bcrypt cost 12; password 12–72 bytes; JWT expires in 30 min; algorithm pinned to HS256 (`algorithms=[...]`, so `alg=none` is rejected); a 32+ character secret is mandatory or the app does not start | `test_weak_password_is_rejected`, `test_tasks_require_authentication`; `app/security.py`, `app/config.py` | no rate limiting on `/auth/login` (backlog: `slowapi`); no token revocation, so a stolen token is valid until it expires |
| **T**ampering | change or delete another user's task (IDOR); lost update between concurrent requests | every read and write goes through `_get_owned_task`: wrong owner and missing row both answer 404; a `StaleDataError` on commit is rolled back and answered 404 | `test_user_cannot_access_another_users_task`; `test_update_of_task_deleted_concurrently_is_404` (DELETE/PUT race found by ZAP, findings 2026-10-28) | no optimistic locking: two updates by the same user are "last write wins" (accepted for a task list) |
| **R**epudiation | a user denies an action; nobody can tell who changed what | — | — | no structured audit log (backlog); only uvicorn access logs |
| **I**nformation disclosure | user enumeration through login; stack traces; responses cached by proxies; data read cross-origin | one `Invalid credentials` message and a dummy hash so timing is the same for unknown e-mails; Swagger UI only when `APP_ENV=dev`; `Cache-Control: no-store`, `Cross-Origin-Resource-Policy: same-origin`, CSP `default-src 'none'`, `nosniff`, no `Server` header | `test_wrong_password_and_unknown_email_look_identical`, `test_docs_disabled_outside_dev`, `test_security_headers_present`; ZAP scan with 0 FAIL (CORP header added after the scan, findings 2026-10-28) | `/auth/register` answers 409 for an existing e-mail (accepted: usability); ZAP 40014, `<script>` echoed inside JSON, accepted because of `nosniff` + CSP, review 2026-12-01 |
| **D**enial of service | oversized or malformed input; integer overflow; request floods | every field has a length limit (`title` ≤ 120, password ≤ 72 bytes); `task_id` validated as `1 ≤ id ≤ 2^63-1` (422, not 500); hypothesis property tests and a 30 s atheris fuzz run on every PR | `test_task_id_out_of_range_is_422`, `test_password_over_72_bytes_is_rejected`, `test_task_id_never_returns_500`, `fuzz/fuzz_models.py`; findings 2026-10-28 (64-bit id) | no rate limit and no body-size limit in the app: both expected from the reverse proxy |
| **E**levation of privilege | forged JWT; code execution in the app becoming root; code reaching production unreviewed | pinned JWT algorithm and mandatory strong secret; container runs as the unprivileged `app` user on a `slim` base image pinned by digest; `main` accepts only pull requests with the 5 required checks green | `Dockerfile`; branch ruleset (direct push rejected, findings 2026-10-27) | solo project: no second human reviewer (Scorecard Code-Review 0, Branch-Protection 4) |

## STRIDE — the pipeline and the supply chain

| Category | Threat | Control in place | Evidence | Known gap |
| --- | --- | --- | --- | --- |
| Spoofing | an action tag re-pointed to malicious code (as happened to `trivy-action` in March 2026) | every action pinned to a 40-character commit SHA; Semgrep rule `github-actions-mutable-action-tag` blocks any `@vN` reference; the Scorecard publisher rejects tag-object SHAs ("imposter commit") | `devsecops.yml`; findings 2026-10-28 | — |
| Tampering | a dependency with a known CVE or a replaced wheel; a modified base image | `pip install --require-hashes` from `pip-compile --generate-hashes` output; pip-audit fails on any known CVE; base image by digest; Trivy on the Dockerfile and on the image (CRITICAL/HIGH with a fix block the build); Dependabot with a 7-day cooldown, majors one PR at a time | PR checks `sca` and `build`; findings 2026-10-27 and 2026-10-29 | Dependabot majors are merged after reading the release notes, but still by one person |
| Repudiation | an image in the registry that nobody can trace back to a build | keyless Cosign signature with the OIDC identity of the workflow on `main`, plus a CycloneDX SBOM attestation; both recorded in the Sigstore transparency log; anyone can run `cosign verify` | README, "Verify the published image"; verified externally with Cosign 3.1.4 | tags are `latest` and the commit SHA; no semver release yet (Scorecard Signed-Releases not applicable) |
| Information disclosure | a secret committed by mistake; a token leaking through a workflow | Gitleaks on pre-commit and over the full history in CI; `GITHUB_TOKEN` is `contents: read` by default and each job adds only what it needs (`security-events: write`; `packages: write` and `id-token: write` on `release` only); no long-lived secret exists, signing uses OIDC | `secret-scan` job; `permissions:` blocks; Scorecard Token-Permissions 10 | — |
| Denial of service | a flaky or hijacked scanner blocking every merge | scanners run from vendor images pinned by digest (Semgrep, ZAP); `concurrency` cancels superseded runs; every exception is explicit and dated (`.trivyignore`, `nosemgrep`, ZAP `IGNORE` with a reason) | findings 2026-10-28 (advisories in Semgrep's own dependencies) | a GitHub outage still blocks merges, by design |
| Elevation of privilege | a pull request that edits the workflow to grant itself permissions or skip a gate | workflow files are part of the reviewed diff; `pull_request` runs from forks get a read-only token and no secrets; the ruleset requires the 5 checks on a branch up to date with `main`; `CODEOWNERS` routes every change, `.github/` included, to the owner | branch ruleset; `.github/CODEOWNERS` | same single-maintainer gap as above |

## Accepted risks

Every accepted risk above also has a line in the [findings log](findings.md) with the reason and a
review date. Items marked "backlog" (rate limiting, audit log, a signed semver release) are the
next changes planned after this version.
