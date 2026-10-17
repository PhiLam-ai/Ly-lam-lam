# V387 Skinning Implementation Plan — 2026-10-17

## Goal

Replace V386's deliberately baked, unskinned GLB export with a true glTF skeletal skin while preserving the successful V386 geometry, materials, UVs, face morphs, accessories, and armhole contour. This is an engineering plan, not a claim that skinning is implemented.

## Verified baseline

- Source branch: `avatar/v386-r9-profile-integrated-overlap`
- Source build commit: `61902b5dead4bc175425469a3208a01f34f798ad`
- Successful run #80: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38997553610
- Candidate report explicitly states `body_skinning = Baked neutral evaluated mesh; exported skin_count must be zero`.
- Current export calls `bake_character_to_morph_meshes(...)` and `bpy.ops.export_scene.gltf(... export_skins=False ...)`. The idle clip is added to the armature before the geometry is baked, so the exported animation does not prove body deformation.
- Production `lam-default.glb` must remain untouched.

## Implementation design

### 1. Preserve the source rig and deformable meshes

- Keep the MPFB human base mesh, armature, original vertex groups, modifiers and object-to-armature relationship alive until after export.
- Ensure every deformable body/arm/hand mesh has an Armature modifier referencing the exact exported armature.
- Ensure wardrobe meshes are weighted to the same rig, or explicitly classify rigid accessories as attached to stable bones (necklace to chest/neck; hair to head; shoes to feet).
- Never apply the armature modifier or convert the primary body to evaluated static geometry before glTF export.
- Preserve the current baked-copy path as an optional visual diagnostic only; it must not be the source of the skinned production-candidate body.

### 2. Vertex-weight validation

Before export, generate a report per deformable mesh:
- vertex count and group count;
- fraction of vertices with at least one positive valid bone weight;
- vertices with zero weights (must be zero for body/arms/hands; rigid accessory exceptions must be documented);
- per-vertex weight sums (normalized to 1 within tolerance);
- all referenced groups map to real deform bones;
- no accidental influence from helper/mask groups.
- inspect shoulder cap and armhole seam weights from front, side and three-quarter views.

### 3. glTF export and structural assertions

- Export with `export_skins=True` and skeletal animation enabled.
- Parse the exported GLB JSON and assert:
  - `skins` has at least one entry;
  - each skin has a valid skeleton/joints list and inverse bind matrices;
  - body mesh nodes reference a valid skin;
  - each joint index resolves to a node;
  - at least one animation channel targets a joint transform;
  - the idle clip contains multiple keyframes and is not only a scene/root object transform.
- Preserve facial morph targets and their names.
- Keep texture/material and UV audits; reject any regression to missing face accessory meshes or materials.

### 4. Deformation tests

Run deterministic poses by changing bone rotations in Blender, then render at least:
- neutral rest pose;
- arms raised to 45° and 90°;
- elbows flexed;
- wrists and fingers flexed;
- one-leg hip/knee flex;
- shoulders crossed in front.
Compare silhouettes and inspect for tearing, collapsing shoulders, detached hands, body/clothing intersections and implausible volume loss. Record each pose and its measurements in the candidate report.

### 5. Browser validation

Extend the existing 390 × 844 Three.js smoke test to:
- load the skinned GLB;
- enumerate skins, joints, animations and morph influences;
- play `Lam_Idle_GentleSway` and verify the body mesh visibly deforms with the rig;
- activate each of the 12 face morphs individually, reset to neutral, then test selected combinations;
- capture screenshots for neutral, animated and facial-expression states;
- fail if the mesh stays static while a skeletal animation plays, or if the console/network reports errors.

## Acceptance gates

The next candidate may be called **skinned technical candidate** only if all structural, weight, deformation and browser checks pass. That label still does not mean photorealism or likeness approval.

Photorealism gate remains separate: human review of actual candidate renders against the saved reference portrait, including front, three-quarter, profile and face close-up, with explicit review of skin detail, eyes, hair strand layering, hands, wardrobe and overall likeness.

## Immediate next implementation step

Create a separate experimental branch from the successful V386-R9 branch, implement and test the rig-preserving export there, and keep all changes isolated from `main`. Do not loosen acceptance checks to make a failing build green; update tolerances only when supported by measured geometry and a documented reason.
