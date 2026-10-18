# V387 Facial Shape-Key Audit — Interpretation and Next Gate

Date: 2026-10-18  
Source model: `lam-default.glb`  
Workflow: [Blender 3.6 real-model audit](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/39099849813)  
Branch: `avatar/v387-rig-skinning-audit`

## Result

The automated geometry-only audit completed successfully. It found six mesh objects with shape keys and 72 mesh/key combinations (12 keys on each of six meshes).

- 16 combinations changed at least one vertex.
- 56 combinations did not change the mesh geometry.
- All 12 key names have a geometric effect on at least one mesh.
- The audit is diagnostic only. It does not establish that the correct facial region moves, that the motion looks natural, or that the expressions are suitable for animation.

## Observed active combinations

| Shape key | Meshes with vertex changes | Maximum local vertex delta |
|---|---|---:|
| `blink_left` | `left_eye` | 0.06227422 |
| `blink_right` | `right_eye` | 0.06227422 |
| `brow_raise` | `left_brow`, `right_brow` | 0.07595375 |
| `smile` | `mouth` | 0.05147821 |
| `mouth_open` | `mouth` | 0.09340785 |
| `jaw_open` | `mouth`, `chin` | 0.07712958 (mouth) |
| `jaw_hinge` | `mouth`, `chin` | 0.05336671 (mouth) |
| `cheek_raise` | `mouth`, `chin` | 0.02059137 |
| `lip_press` | `mouth` | 0.02163336 |
| `lip_fv` | `mouth` | 0.02912041 |
| `lip_round` | `mouth` | 0.01077039 |
| `tongue_tip` | `mouth` | 0.02236076 |

The eye blink keys affect only their expected eye mesh in this static report. The smile, mouth and lip keys affect the mesh named `mouth`; this is a signal to inspect the actual mesh topology and rendered result, not proof of a correct expression.

## Next required gate: visual expression review

Do not merge this audit PR or promote any experimental avatar to production based on a successful CI run alone. The next validation pass should render the neutral face and each expression at the same camera, lighting and framing, with each key isolated at value 1.0. At minimum inspect:

1. Left blink and right blink separately; check for eye closure, clipping, and symmetry.
2. Smile; check mouth corners, lips, teeth/tongue visibility and cheek deformation.
3. Mouth open and jaw open/hinge; check jaw continuity, chin separation and mouth cavity.
4. Brow raise and cheek raise; check whether the correct facial regions move.
5. Lip press, lip-fv, lip-round and tongue-tip; check whether each is visibly distinct and anatomically plausible.
6. Return every key to zero and confirm the neutral face restores exactly.
7. Test combined expressions and confirm no clipping or mesh intersections.

Record images and an explicit pass/fail for each expression. If an expression is not visibly distinguishable or deforms the wrong region, fix the source shape keys rather than relabeling the audit as a pass.

## Current decision

**NOT APPROVED — VISUAL REVIEW REQUIRED.** The CI job proves the script can inspect the model and record geometric deltas; it does not certify facial quality, rig deformation quality, or production readiness. Production remains unchanged.
