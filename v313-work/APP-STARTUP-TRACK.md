# LÝ LÂM LAM V313 — App Startup Track

Status: IN PROGRESS — NOT A RELEASE.

## Parallel workstreams
- App startup track: this branch, based on `main`. Keep the V312 web preview path as the current baseline; improve startup diagnostics, static hosting, browser smoke coverage, and iPhone HTTPS deployment readiness.
- Avatar repair track: `avatar/v313-repair-candidate-20261014`. Investigate mesh coordinate spaces, skin/bind context, and disconnected body parts in isolation.

## Safety and release rules
- Never modify or replace the original V312 `lam-default.glb` from the app-startup branch.
- Do not merge experimental avatar geometry into the startup track until it passes visual review and retains the original rig/skin plus all 12 expected morph targets.
- A successful CI smoke test proves only that the page boots and the GLB loads; it does not prove the avatar looks anatomically connected or that the conversation API works.
- Do not label V313 PASS or create a release ZIP until the package is reproducible, startup checks pass, the visual avatar is accepted, SHA-256 is recorded, and rollback files are preserved.

## Current confirmed baseline
- Repository default branch: `main`.
- V312 preview files live under `v312-work/` (including `index.html`, `module.mjs`, and `lam-default.glb`).
- The browser workflow serves `v312-work/`; verify the workflow's DOM selectors and boot flags against that exact app before relying on its result.
- The GLB loads in prior smoke evidence, but the rendered model has visibly disconnected mesh parts.
- API conversation integration and real-device iPhone/Safari acceptance are not complete.

## Execution order
1. Validate browser smoke test selectors, boot flags, request status, WebGL readiness, and JavaScript errors against `v312-work/`.
2. Run browser checks against the candidate branch; save screenshot/log evidence as workflow artifacts.
3. Audit HTTPS/static deployment instructions and confirm all required files are colocated.
4. In parallel, repair the avatar only on the isolated avatar branch; compare front/side/three-quarter renders and test rig/morph preservation.
5. Combine only a verified avatar candidate with the startup track, then produce V313 ZIP, test report, SHA-256 manifest, and rollback copy.

## Version record
- Baseline: V312 — preserved.
- Candidate: V313.
- App startup track: in progress.
- Avatar visual acceptance: blocked.
- Conversation API: not integrated.
- Physical iPhone acceptance: pending.
- Release ZIP / SHA-256 manifest: not created / pending.
