# Lý Lâm Lam Avatar — visual audit findings (P0)

Audit source: `lam-default.glb`, imported and rendered by Blender 3.6.23 in GitHub Actions run 38362595425.

## Technical checks
- GLB import: PASS
- Three preview renders (front, side, three-quarter): PASS
- Round-trip GLB export: PASS
- Original source integrity: PASS; SHA-256 before and after both `0aa06eb23754d72eec1e7b6db91c72014b0f4dd571dd2625d9d7e6b9c886b37a`
- 85 mesh objects, 8,036 vertices, 11,268 polygons
- 4 materials (dress, hair, shoes, skin); 0 texture images
- 12 morph targets detected
- Round-trip GLB size: 1,800,360 bytes

## Visual findings (blocking)
The generated orthographic previews show the source avatar is visibly fragmented:
- large gaps between pelvis/hips and lower legs;
- arms/hands appear detached from the torso;
- head and torso/neck are separated by a visible gap;
- limbs and clothing read as disconnected low-poly parts rather than one coherent adult female character;
- materials are flat and no texture images are embedded.

The overall mesh bounds are approximately 3.948 x 1.333 x 9.020 Blender units. This is a diagnostic measurement, not a validated real-world scale.

## Decision
**Do not approve the current GLB as the finished avatar.** The technical audit PASS means only that Blender can import, render, and export the file. It does not mean the model passes visual quality. Preserve `lam-default.glb` as the untouched baseline. Next work should create a separate candidate model, prioritize continuous body silhouette and joined-looking limbs, then render and visually inspect before any replacement of the web asset.
