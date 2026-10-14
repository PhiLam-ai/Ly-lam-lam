# Legacy package-integrity test cleanup — current V312 deployment

## Decision

The previous broad diagnostic reported **71/88 passing and 17 failures** on workflow run [38507117893](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38507117893). The failed set mixed a real runtime-policy inconsistency with tests pinned to a retired Pages build architecture.

The real runtime policy issue was fixed on this PR branch: an omitted `three` query parameter now selects the bundled `./vendor/three/` modules, matching the diagnostics and the local-first contract. The V309 test now checks this current expression, and the V241 test was rewritten to verify the effective runtime behavior plus the actual vendor files rather than a build-time tool under the deployed package directory.

Sixteen tests asserted obsolete packaging mechanics and paths: `v312-work/.github/workflows/deploy.yml`, a build-time vendor-acquisition pipeline living inside `v312-work`, a generated `dist` folder, or legacy public-package manifests. They were removed from the active diagnostic suite and preserved verbatim in [`automation/legacy/legacy-package-integrity-tests.md`](legacy/legacy-package-integrity-tests.md). They are not silently deleted; they are archived because the current repository workflow is `.github/workflows/main.yml` and uploads `./v312-work` directly.

## Retired test blocks (16)

1. `deploy package contains required root files and workflow` — wrong root: requires old build/deploy orchestration files inside the public payload.
2. `GitHub Pages workflow gates deployment on passing regression tests` — reads the retired workflow path; the current workflow and pre-deploy test ordering are checked by the target-specific suite.
3. `V244 GitHub Pages deployment stages pinned Three.js and defaults to self-hosted imports`.
4. `V244 deployment preparation fails closed without a complete pinned local vendor`.
5. `V246 Pages preparation is fail-closed, idempotent, and preserves the explicit CDN override`.
6. `V275 Pages deployment fails closed unless pinned Three.js is self-hosted`.
7. `V277 caches npm downloads across Pages runs to reduce repeated Three.js registry dependence`.
8. `V280 saves npm cache only after successful acquisition and skips immutable exact cache hits`.
9. `V276 npm network failures emit no fallback output and keep deployment fail-closed`.
10. `V262 Pages preparation validates the import map before any HTML mutation`.
11. `V281 workflow_dispatch supports a repository-supplied pinned Three.js tarball`.
12. `V270 GitHub Pages workflow uploads the isolated dist artifact, not the repository root`.
13. `V274 runs the HTTP smoke test against the assembled Pages artifact`.
14. `V270 Pages artifact contains runtime assets but excludes development tooling`.
15. `V271 Pages artifact recursively validates nested vendor imports and rejects symlinks`.
16. `V272 Pages artifact rejects root-level symlink inputs without replacing a valid artifact`.

These tests target tools and workflow contracts no longer used by the active deployment path. The previous artifact-builder symlink protections are not assumed to protect the current path: a new check now scans the **actual** `v312-work` Pages payload and fails if it contains symlinks.

## What remains active

The actual deployment test suite covers:
- the real root Pages workflow and confirms blocking tests occur before deployment;
- bundled Three.js runtime modules are present and over 1 KB;
- the deployed payload contains no symbolic links;
- iPhone viewport/safe-area and avatar controls;
- the app's normal GLB URL and opt-in diagnostics;
- valid GLB structure plus all 12 expected morph names.

The historical suite remains useful evidence but is no longer used as if its old build-pipeline assumptions were requirements of today's application.

## Verification status

The latest run before this cleanup reported core tests **46/46 passing** and actual-target tests **5/5 passing**; the new edits still require a fresh CI run. No claim is made yet that the post-cleanup suite is green, nor that structural checks establish coherent avatar geometry or real iPhone Safari behavior. The PR remains a draft and production deployment has not been performed by these edits.
