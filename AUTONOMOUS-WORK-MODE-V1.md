# Lý Lâm Lam — Autonomous Work Mode V1

## Purpose

This is the first bounded automation layer for the project. It turns the nightly checks into a repeatable, evidence-producing work cycle. It is **not yet an AI coding agent**: this workflow does not infer new fixes, rewrite application code, use an LLM API, or claim that an avatar visually works on iPhone.

## What runs automatically

1. Check the application entry page, bundled Three.js dependencies, GLB file integrity, and the stable-version registry.
2. Run core avatar logic and GLB structural tests as blocking checks.
3. Run the retained package-integrity suite against the current `v312-work` target. Sixteen test blocks for a retired `deploy.yml`/`dist` packaging pipeline are preserved in `automation/legacy/legacy-package-integrity-tests.md`, outside the active test path; the remaining current compatibility tests and target-specific tests are blocking/diagnostic evidence.
4. Publish JSON and Markdown reports plus the raw test logs as a GitHub Actions artifact and workflow summary.
5. Choose the next safe recommendation from predefined rules: investigate failed blocking tests first; otherwise return to the known avatar visual/rigging blocker; the legacy test-harness reconciliation is completed on the draft automation branch.
6. Keep every execution read-only with respect to repository contents and stable-version pointers.

## Autonomy boundaries

- **Allowed without asking:** read repository source, run deterministic tests, generate reports/artifacts, and prepare an isolated patch on a non-release branch.
- **Approval required:** external service credentials, paid API/model calls, permissions expansion, deployments, stable-version promotion, deletion/replacement of originals, or actions that could incur material cost.
- **Must not be claimed:** a green file-integrity test is not proof of correct 3D geometry, full face expressions, iPhone Safari behavior, or a complete V313 release.
- **Fail closed:** any missing prerequisite or failed regression suite makes the cycle fail and the report retains the failed item. No failed candidate is promoted.

## What V1 does not do yet

The scheduled cycle is a deterministic safe executor, not a background AI programmer. A bounded AI coding stage needs an approved model/service credential and explicit spending limits; those are deliberately not assumed or requested by this workflow. Until that stage is added, this workflow does not edit code by itself.

## Evidence

Each run attaches `autonomous-work-mode-<run id>-<attempt>` containing:
- `autonomous-work-report.json`
- `REPORT.md`
- `baseline-checks.json`
- `core-regression.log`
- `package-integrity.log`

## Next stages

- V1: scheduled safety preflight, blocking core tests, legacy package-test diagnostics, recommendations, and durable run evidence.
- Completed on the automation branch: `AUTO-004` reconciles current tests to the active Pages target. Sixteen old-pipeline assertions are preserved verbatim in a non-executable archive; the current test set passes 72/72, core tests 46/46, and target-specific tests 6/6 in run [38507518716](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38507518716). These changes are still in draft PR #3 and are not active on `main` until reviewed and merged.
- V2: bounded AI task execution on a disposable branch, with file/path allowlists, diff-size limits, repeatable tests, and a patch artifact; never promote automatically.
- V3: human-reviewed merge/promotion and rollback verification. iPhone visual review remains an explicit acceptance gate until it can be reliably tested.
