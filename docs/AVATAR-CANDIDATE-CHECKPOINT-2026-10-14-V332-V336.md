# Lý Lâm Lam avatar candidate checkpoint — 2026-10-14 (V332–V336)

## Release decision

**No candidate in this checkpoint is approved for production replacement.** The production `lam-default.glb` is unchanged. Work is isolated on branch `avatar/v313-repair-candidate-20261014`.

## V332 — baked human morph candidate
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38553205785
- Technical gates passed: 0 glTF skins; 9 embedded images; 8 materials; 12 expected composite morphs; `Lam_Idle_GentleSway`; browser smoke at 390×844 with no browser page/console errors and animation advancing.
- GLB: `lam-v332-baked-human-candidate.glb`, 20,168,800 bytes; SHA-256 `6ae293a9f975f7ccbedfad5f001291a400a0c5cae1b0bb0c96c4cfa06168e38d`.
- Windows ZIP: `ly-lam-lam-v332-experimental-windows.zip`, 21,345,994 bytes, 81 entries, ZIP integrity passed; SHA-256 `94bcd1616e51f5ded25b55caa581e4f807b525340092ecc909fbf24682394036` matched its sidecar.
- Visual decision: NOT APPROVED. Blender render showed a default-scene cube occluding the lower body, and the browser view showed pronounced red/black facial patches.

## V333 — render cleanup and evaluated world transform
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38561847422
- Technical gates passed; factory-startup `Cube`, `Camera`, and `Light` removed before render, and evaluated mesh world transforms were used while baking.
- GLB: `lam-v333-render-fix-candidate.glb`, 20,168,800 bytes; SHA-256 `ff48fb0df3f3d02612896c84b1379b16de24dd3094f826a5d3f77109c29dcaa9`.
- Windows ZIP: `ly-lam-lam-v333-experimental-windows.zip`, 21,345,991 bytes, 81 entries, ZIP integrity passed; SHA-256 `a46902d34f4672dcd2b93d579482bce7f99b81a4deea62418f42c8dd6813dee8` matched its sidecar.
- Visual decision: NOT APPROVED. The Blender framing issue was fixed, but browser facial patches persisted.

## V334 — face accessory isolation
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38562895451
- Removed `eyebrow001`, `eyelashes01`, `high-poly`, `teeth_base`, and `tongue01` from the candidate web GLB while preserving 12 base-mesh morphs and idle animation.
- GLB: `lam-v334-accessory-isolated-candidate.glb`, 16,565,776 bytes; SHA-256 `0dc87a937ac2dd32172938a55c4de8a73e49b47261368633bb8538d000c7a7a7`. Contains 0 skins, 4 images and 3 materials.
- Windows ZIP: `ly-lam-lam-v334-experimental-windows.zip`, 17,932,639 bytes, 81 entries, ZIP integrity passed; SHA-256 `8a5491e1b4e89c57a8d3b397c49f283f3c9f033c91f8b011028856ef3b2aac2b` matched its sidecar.
- Visual decision: NOT APPROVED. The patches remained after all five accessory meshes were removed; this narrowed the issue to the base skin mesh/material/export path.

## V335 — skin material and UV diagnostic
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38563847327
- Technical gates passed; report recorded skin texture `young_lightskinned_female_diffuse3.png`, UV map `UVMap`, and a simplified export-only material `V335_GltfCompatibleSkin` using explicit `UVMap → Image Texture → Principled BSDF → Material Output` nodes.
- GLB: `lam-v335-gltf-skin-uv-candidate.glb`, 16,565,768 bytes; SHA-256 `2fe482930ba9d44c8c664a9e13f0ffe1634e1572f34cf180b65c605c9f0be271`. Contains 0 skins, 4 images, 3 materials, 12 morphs, and `Lam_Idle_GentleSway`.
- UV finding: the source body material had diffuse and alpha image nodes referring to the same image but no explicit Vector links; V335 used the single skin diffuse image and an explicit UV map. The report says UV-map choice fell back to the active UV layer `UVMap`, which was also marked active-render on source and baked meshes.
- Browser smoke: passed at 390×844 with no page/console errors and bounds within view.
- Windows ZIP: `ly-lam-lam-v335-experimental-windows.zip`, 17,932,708 bytes, 81 entries, ZIP integrity passed; SHA-256 `ccc2039d2269602149d36815cdef754809c659af8ced908f29e5520079447342` matched its sidecar.
- Visual decision: NOT APPROVED. The pronounced blotches were greatly reduced, but the texture-only face still lacks 3D eyes, lashes, brows, teeth and tongue; the eye region reads as thin printed lines at the full-body scale.

## V336 — restore face accessories with glTF-safe materials (running)
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38564972623
- Script: `tools/blender_v336_gltf_face_accessory_candidate.py`.
- Keeps the simplified skin material from V335 and restores five 3D face accessory meshes with one image and an explicit UV map per material; RGBA alpha is retained for transparent meshes.
- Required gates: no excluded face accessories, all five accessories have image/UV/material audit entries, 0 skins, at least 12 morph names, `Lam_Idle_GentleSway`, mobile WebGL load and framing, clean browser page/console errors, ZIP integrity and matching SHA-256 sidecar.
- It is a diagnostic candidate, not a production replacement. Inspect the V336 browser screenshot before approving the avatar.

## Safety and rollback
- Do not copy any candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Keep all builds, renders, reports, and ZIPs under versioned candidate artifacts. Record SHA-256 only after checking actual bytes against the sidecar.
- A technical PASS means the automation gates succeeded; it does not, by itself, mean an avatar is visually approved.
