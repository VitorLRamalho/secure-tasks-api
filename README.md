# secure-tasks-api
Reference DevSecOps pipeline for a FastAPI service: secrets scanning, SAST, SCA, container scanning, authenticated DAST, SBOM and Cosign-signed images on GitHub Actions.

   ## Shift-left: blocked before the commit exists

   Every `git commit` runs Ruff, Gitleaks and basic hygiene hooks locally.
   Here Gitleaks stops a commit containing an AWS-style access key:

   ![Gitleaks blocking a commit that contains an AWS access key](docs/img/gitleaks-precommit.png)
