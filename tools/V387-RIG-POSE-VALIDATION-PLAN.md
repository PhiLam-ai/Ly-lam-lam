# V387 — Rig and deformation pose-validation plan

Status: STRUCTURAL RIG FOUND; POSE DEFORMATION NOT YET VERIFIED.
Baseline asset: `lam-default.glb`.
Structural run: [GitHub Actions run 39099497733](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/39099497733).

## Evidence from the structural audit
- 1 armature: `Lam_Humanoid_Root`
- 17 bones, including shoulders, elbows, wrists, hips, knees, ankles, neck and head
- 85 mesh objects; all 85 have an armature modifier targeting the armature and at least one non-zero vertex weight
- Six facial meshes expose 12 shape-key names each: smile, blink_left, blink_right, mouth_open, brow_raise, jaw_open, jaw_hinge, cheek_raise, lip_press, lip_fv, lip_round, tongue_tip
- Audit status: `RIG_PRESENT_REQUIRES_POSE_VALIDATION`

## What this evidence does NOT prove
- That the 17-bone hierarchy has correct parent/rest transforms
- That vertex weights are anatomically sensible (the structural script counts non-zero weights, it does not validate their distribution)
- That raising arms produces acceptable shoulder/armpit deformation
- That facial shape keys visibly deform the intended region
- That separated source meshes visually form a continuous body
- That the GLB has passed real iPhone Safari testing

## Required next checks
1. Import the actual baseline GLB in Blender and record the bone hierarchy, parent relations and rest-pose transforms.
2. Generate isolated pose renders at neutral, arm raise 45°, and arm raise 90° for left and right arms. Do not rotate the entire root as a substitute for joint deformation.
3. Save pose-specific JSON diagnostics and front/side/three-quarter renders.
4. Test representative facial keys (blink_left, blink_right, smile, mouth_open) independently, recording whether evaluated mesh coordinates change.
5. Review the images for clipping, detached parts, dark pockets, and shoulder/armhole silhouette.
6. Keep all results diagnostic. Do not replace production unless the visual and mobile acceptance gates are explicitly passed.

## Acceptance
A structural PASS is not an artistic or deformation approval. Pose renders and human visual review are mandatory.
