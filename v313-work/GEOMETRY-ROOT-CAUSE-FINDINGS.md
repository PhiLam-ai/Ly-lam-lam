# V313 geometry root-cause findings — 2026-10-14

Status: DIAGNOSTIC ONLY — production GLB is unchanged; no candidate is approved.

## Confirmed from Blender 3.6.23 artifact
- Source GLB SHA-256: `0aa06eb23754d72eec1e7b6db91c72014b0f4dd571dd2625d9d7e6b9c886b37a`.
- 85 mesh objects and one 17-bone armature import; expected 12 facial morph names are present across facial meshes.
- The source render is visibly disconnected (head, arms/hands, pelvis/legs). Resetting armature pose channels does not repair it.
- Most mesh object transforms are identity and meshes are parented to `Lam_Humanoid_Root`; this rules out a simple object-transform-only correction.
- Pose-channel anomaly: `Lam_Joint_LeftShoulder` has quaternion `[0.983158, 0, 0, 0.174908]` (about 20 degrees around local Z); resetting it in an isolated copy did not solve the whole-body separation.
- The geometry itself has inconsistent part placement relative to the rig and each other. Examples from imported mesh world bounds: torso Z 1.50–4.40; pelvis Z 0.53–1.57; head Z 4.63–6.07; hair Z 4.72–6.28; feet Z -2.74–-2.36; thigh bounds Z -0.77–0.78. Arms/hand pieces span X values as far as roughly -2.40 to +1.55. The front render confirms these are actual visible gaps, not just a numerical AABB concern.
- The audit's rest bones are laid out around hips Z 0.98, spine Z 2.15–3.55, chest Z 3.55–4.37, neck Z 4.45–5.35, head Z 5.35–6.25. This is inconsistent with the foot and thigh geometry placement, and some left-arm pose endpoints differ from rest endpoints.

## Interpretation
The evidence points to a malformed/inconsistent source geometry layout and/or mesh vertex positions in the original GLB, with an additional left-shoulder pose offset. It is not safe to "fix" this by moving every object from bounding boxes alone: object bounds are only coarse and a blind translation could break vertex weights and morphs.

## Safe next experiment
Create a separate diagnostic candidate that compares each mesh's vertex coordinates and weighted vertex centroids against the matching rig bones, while keeping the original GLB hash unchanged. Any proposed per-part correction must be based on named mesh/bone mapping and visible renders, then re-audit all 12 morphs, skinning and browser render. Do not replace `lam-default.glb` or mark V313 PASS until these gates succeed.

## Current release decision
NOT APPROVED. No production GLB replacement and no V313 release ZIP.
