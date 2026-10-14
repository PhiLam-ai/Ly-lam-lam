# LÝ LÂM LAM V313 — Repair Candidate

Status: **IN PROGRESS — NOT A RELEASE**

## Parallel execution
The app-startup workstream is being developed separately on `v313/app-startup-20261014` so that runtime fixes can proceed without waiting for avatar geometry work. Keep this branch isolated and do not merge either workstream into `main` until release gates pass.

## Safety rules
- V312 remains the known baseline and must not be overwritten.
- Work only on this V313 branch until the candidate passes the release gates below.
- Never promote a generated replacement GLB solely because it looks connected; verify rig/skin bindings and all 12 expected facial morph targets.
- Preserve the original GLB and record its SHA-256 before/after any pipeline operation.

## Known blockers carried forward
- The current imported GLB renders as disconnected body parts in Blender/browser evidence.
- Browser smoke tests and workflow success are not visual acceptance.
- Chat/API integration is still not complete.
- Real iPhone testing has not been established by CI.

## V313 release gates
1. **Geometry diagnosis:** reproducible report of per-mesh axes, bounds, transforms, parent/skin relationships and morph-target counts.
2. **Isolated repair candidate:** never overwrite the baseline; document each coordinate/transform correction and why it is safe.
3. **Visual evidence:** front, side and three-quarter renders show a connected adult figure with no detached head/limbs or obvious intersections.
4. **GLB integrity:** valid glTF 2.0; skin/joints retained; expected 12 morph targets retained; no NaN/Inf vertex data; file opens in browser viewer.
5. **Runtime:** browser startup and WebGL smoke checks pass against the candidate GLB.
6. **Packaging:** versioned ZIP, test report, SHA-256 manifest, and rollback copy. Mark PASS only when every mandatory gate is verified.

## Next implementation step
Build an isolated coordinate/transform repair experiment against a copy of the V312 GLB. First establish the glTF-to-Blender axis conversion and each mesh's bind/skin context; do not apply blanket per-part rotations or translations until this evidence is available.

## Current version record
- Baseline: V312
- Candidate: V313
- Release ZIP: not created
- SHA-256 manifest: pending
- Visual acceptance: blocked
- iPhone acceptance: pending
