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


## Latest diagnostic evidence — 2026-10-14

- Per-mesh bind-pose localization workflow: [run 38497152314](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38497152314) — **workflow success**; diagnostic artifact only, not a repaired avatar.
- Artifact contains front render of the original GLB and a separate coherent-body prototype. Original render confirms the head, arm pieces, hands, pelvis and lower legs are visibly disconnected.
- The original GLB still has 85 mesh objects, one armature and 17 bones. Skin-weight audit reports no unweighted meshes, no meshes missing an armature modifier, and no vertex-group names missing from the armature. This narrows the issue: the visible failure is not explained by absent armature modifiers or missing bone-name mappings alone.
- Per-mesh weighted-centroid heuristic flags facial meshes against `Lam_Joint_Hips`: left/right brows about 4.24 units, eyes about 4.06, mouth about 3.78. These are diagnostic clues only; facial meshes can have legitimate rigid weights and centroid distance is not a proof of incorrect binding.
- The original mesh bounds span roughly Z=-2.74 at feet to Z=6.28 at hair, while torso is Z=1.5..4.4. Several body regions are not spatially connected in the render. This strongly warrants investigation of object transforms, imported coordinate basis, and skin bind matrices before changing weights.
- The coherent-body prototype is visually connected and approximately 1.584 m tall, but it is **not releasable**: the report explicitly says the production armature and 12 facial morphs have not been transferred. Do not replace the production GLB with it.

## Next safe action

Build a transform/bind-matrix comparison report per mesh: object transform, armature modifier settings, skin/bind relationship, and local-vs-world bounds. Use that report to select a reversible repair on a copy. Do not move the original GLB parts or reweight production meshes based solely on centroid distance.
