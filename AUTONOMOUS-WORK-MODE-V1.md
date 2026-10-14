# Lý Lâm Lam — Autonomous Work Mode V1

## Purpose

This is the first bounded automation layer for the project. It turns the nightly checks into a repeatable, evidence-producing work cycle. It is **not yet an AI coding agent**: this workflow does not infer new fixes, rewrite application code, use an LLM API, or claim that an avatar visually works on iPhone.

## What runs automatically

1. Check the application entry page, bundled Three.js dependencies, GLB file integrity, and the stable-version registry.
2. Run the repository's Node.js regression/structural test suite without adding project dependencies.
3. Publish a JSON and Markdown report as a GitHub Actions artifact and workflow summary.
4. Choose the next safe recommendation from predefined rules: investigate failing checks first; otherwise continue the known avatar visual/rigging blocker.
5. Keep every execution read-only with respect to the repository contents and stable-version pointers.

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
- `regression-tests.log`

## Next stages

- V1: scheduled safety preflight, regression tests, recommendations, and durable run evidence.
- V2: bounded AI task execution on a disposable branch, with file/path allowlists, diff-size limits, repeatable tests, and a patch artifact; never promote automatically.
- V3: human-reviewed merge/promotion and rollback verification. iPhone visual review remains an explicit acceptance gate until it can be reliably tested.
