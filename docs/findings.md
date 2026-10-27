# Findings log

Everything the pipeline (or the process around it) has caught, newest first.
One line per finding: what was found, how severe, what was decided and where the evidence is.
Accepted risks stay here with a justification; nothing is silently ignored.

Severity follows the tool's own rating; "—" means a process finding with no CVSS.

| Date | Stage | Tool | Finding | Severity | Decision | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-27 | Governance | Rulesets | Direct push to `main` rejected (GH013), 5 required checks enforced | — | Verified; pipeline cannot be bypassed | `docs/img/branch-protection.png` |
| 2026-10-27 | Build | Trivy | SARIF output ignores the `severity` filter by default: gate failed on LOW/MEDIUM Debian CVEs; 0 HIGH/CRITICAL with a fix | LOW/MEDIUM | Fixed: `limit-severities-for-sarif: true`. Policy: CRITICAL/HIGH with a fix block the build; LOW/MEDIUM are monitored | PR #1 |
| 2026-10-27 | Build | build-push-action | Base image not re-pulled on each build; stale layers could hide fixed CVEs | LOW | Fixed: `pull: true` | PR #1 |
| 2026-10-27 | SCA | pip | `--require-hashes` mode rejected an unpinned `pip-audit` on the command line | — | Fixed: installed from hash-pinned `requirements-dev.txt`; dev tools are now audited too | PR #1 |
| 2026-10-26 | SAST | Semgrep | 18 GitHub Actions referenced by mutable tags (`github-actions-mutable-action-tag`) | HIGH | Fixed: every action pinned to a 40-char commit SHA with a version comment; Dependabot will keep them current | PR #1 |
| 2026-10-26 | CI | trivy-action | Action referenced by tag `0.28.0`, removed after the March 2026 tag-hijacking supply-chain attack; job failed at *Set up job* | CRITICAL (supply chain) | Fixed: pinned to the signed commit of v0.36.0 | PR #1 |
| 2026-10-26 | Process | pip | Installing a global tool (Semgrep) into the project venv downgraded `opentelemetry-api`, `click`, `tomli` (`pip check` failed) | — | Fixed: venv recreated from hashed requirements; global tools via pipx | — |
| 2026-10-26 | Process | Docker | Local build and image scan were skipped in week 1 (Docker Desktop WSL integration disabled); CI caught what the local step would have | — | Fixed: integration enabled; local build + Trivy scan before every push | — |
| 2026-10-26 | Process | Gitleaks | AWS documentation example key is allow-listed by Gitleaks (keys ending in `EXAMPLE`), so the first pre-commit test gave a false pass | — | Fixed: test with a randomly generated AWS-format key; documented in README | `docs/img/gitleaks-precommit.png` |
| 2026-10-26 | Application | bcrypt 5 | Passwords over 72 bytes raise `ValueError` (would be HTTP 500); `max_length=72` counted characters, not bytes | MEDIUM | Fixed: byte-length validator on register, `verify_password` returns False; regression test added | `tests/test_api.py` |
| 2026-10-26 | Tests | pytest | Test result depended on the developer's `.env` (`APP_ENV=dev` enabled `/docs`) | LOW | Fixed: `conftest.py` pins `APP_ENV=production` | `tests/conftest.py` |
| 2026-10-26 | Tests | Starlette | Deprecation warning: `httpx` with `starlette.testclient` | INFO | Accepted: revisit when `httpx2` is stable; review 2026-12-01 | — |
