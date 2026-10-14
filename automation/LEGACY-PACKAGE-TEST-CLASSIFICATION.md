# V312 package-integrity diagnostic — failure classification

Reviewed against workflow run 38504699669 and the raw `package-integrity.log` from that run.

## Summary

The broad legacy suite reported 70/88 passing and 18 failing assertions. These are not all proof of defects in the deployed V312 application: the test file lives under `v312-work/tests`, sets `root = path.resolve(__dirname, '..')`, and then interprets that deployed application directory as if it were the historical repository root. Several tests consequently search for repository-level workflows and build-time tools that are intentionally outside the GitHub Pages payload. The suite also expects old import-map/default-CDN policy and an older `deploy.yml` workflow while the current repo uses `.github/workflows/main.yml`.

This classification does not delete or skip these tests. The raw test file and log remain available as diagnostic evidence until each historic expectation is either migrated to a current requirement or explicitly retained as a historical test with its own fixture/target.

## Failure-by-failure classification

| Failing test | Classification | Evidence / next action |
|---|---|---|
| 2 — V309 defaults to bundled Three.js locally | Stale behavior expectation for the current V312 entry page. The entry's import-map comment says local bundling is opt-in with `?three=local`; the test insists omitted mode means local. Keep the separate current-target test for assets and the supported import paths. |
| 5 — required root files and workflow | Wrong target root. It demands repository/build files such as `.nojekyll`, `module.mjs`, and `.github/workflows/deploy.yml` inside the deployed `v312-work` directory. The actual deployment uploads `v312-work`; build orchestration is not part of that payload. Current-target tests check the files needed by this actual payload. |
| 9 — Pages workflow gates deployment | Old workflow path. It opens `v312-work/.github/workflows/deploy.yml`, which is not the repository deployment workflow. The current workflow at repository root is `.github/workflows/main.yml`. A real safety issue was confirmed: the main workflow lacked blocking tests; this branch adds core and current-target test gates before deploy. |
| 32 — V241 local Three.js/staging tool | Mixed historical expectation and wrong target root: it expects an older default-mode policy and build-time `tools/vendor-three.cjs` inside the deployed directory. Verify the deployed asset/runtime behavior via current-target tests instead. |
| 37 — V244 deployment stages pinned Three.js | Old workflow path and packaging architecture: expects `v312-work/.github/workflows/deploy.yml` and preparation tools under `v312-work/tools`; those are not the current deployment configuration. |
| 38 — V244 fail-closed preparation | Build-time `prepare-pages-deploy.cjs` is not present under the deployed payload root, so the historical test invokes a nonexistent tool. Preserve the intended fail-closed behavior as a separate repository-level tooling test only if that workflow is reintroduced. |
| 40 — V246 idempotent Pages preparation | Same obsolete tool-root/packaging contract as V244; the fixture runs against the wrong application root. |
| 42 — V275 fail-closed deployment | Expects the retired `deploy.yml` workflow and its exact old step names. The current deployment workflow is `main.yml`; the branch now gates deployment on core and actual-payload tests. |
| 43 — V277 npm cache | Expects npm acquisition/cache steps in the retired `deploy.yml`. The current deploy package already carries its runtime vendor files and current workflow does not use that build step. |
| 44 — V280 cache save conditions | Same retired workflow and step names as V277; it is not evidence of a current Pages payload failure. |
| 45 — V276 npm network failure fallback | Expects the retired workflow/build tool paths under `v312-work`; the deployed page test should not claim that a build-time npm fetch script ships with the app. |
| 57 — V262 import-map preparation | Expects `tools/prepare-pages-deploy.cjs` within the deployed directory. This test should be relocated to a repository-level build-tool test if that tool remains supported; otherwise retain as historical evidence. |
| 71 — V281 supplied Three.js tarball | Expects a `workflow_dispatch` contract on the retired `deploy.yml`; current deploy workflow is `main.yml` and publishes the preassembled V312 directory. |
| 72 — V270 isolated dist artifact | Expects the older `prepare-pages-artifact.cjs dist` build pipeline and `deploy.yml`. Current deployment intentionally uploads `v312-work` directly. |
| 73 — V274 HTTP smoke test of dist | Expects older `dist` assembly tooling and workflow steps, not the current upload path. Add a smoke test for the current deployed target separately if wanted; do not assume `dist` exists. |
| 74 — V270 artifact contains runtime files only | Invokes the old artifact preparation tool from the wrong root; the expected `.nojekyll` / `module.mjs` manifest belongs to an older package format. |
| 75 — V271 nested vendor import/symlink fixture | Fixture setup fails before testing imports because it tries to copy `v312-work/.nojekyll`, absent in the current package. Preserve the desired security property in a repository-level artifact-builder test if that builder remains supported. |
| 76 — V272 root symlink fixture | Same setup failure caused by missing `v312-work/.nojekyll`, before the symlink-safety behavior can be meaningfully evaluated. |

## Corrective action completed on the automation branch

The current repo Pages workflow was changed to run:
1. `node --test v312-work/tests/avatar-core.test.cjs v312-work/tests/glb-structural-audit.test.cjs`
2. `node --test automation/tests/v312-package-integrity.test.cjs`

Both run before `actions/deploy-pages@v4`. The second suite checks the actual `v312-work` payload, the existing local vendor files, viewport controls, GLB structure and all 12 expected morph names. It also asserts that the two blocking test gates appear before the deployment step.

## Remaining work

Refactor or clearly isolate the historical tests so a developer can run a clean current-target suite without losing the original assertions. Do not edit the old tests merely to manufacture a green result; keep the warning visible until each assertion has a reviewed disposition.

## Important boundary

A green structural test or workflow gate does not prove the avatar looks coherent, face morphs animate correctly, or iPhone Safari works. Those remain independent visual/device acceptance tasks.
