# Lý Lâm Lam avatar candidate checkpoint — 2026-10-14 (V332–V338)

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

## V336 — restore face accessories with glTF-safe materials
- Run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38564972623 — SUCCESS; artifact ID `11895095803` (about 54 MB).
- Script: `tools/blender_v336_gltf_face_accessory_candidate.py`.
- Keeps the simplified skin material from V335 and restores five 3D face accessory meshes with one image and an explicit UV map per material; RGBA alpha is retained for transparent meshes.
- Technical gates passed: all five accessory meshes are present and audited, 0 glTF skins, 12 expected morphs, `Lam_Idle_GentleSway`, mobile WebGL load and framing, no browser page/console errors, ZIP integrity and SHA sidecar included.
- Visual review of `v336-face-closeup.png`, `v336-front.png`, and `v314-candidate-canvas.png`: the severe red/black patches are no longer apparent, and brows, eye geometry, lashes and hair are visible. However, the face remains low-detail/stiff at full-body scale, the hair has a conspicuous pale rim/highlight, eye/iris realism is limited, and the overall body/clothing is still a generic MPFB base rather than the approved Lam likeness and desired proportions. **Visual decision: NOT APPROVED for production.**
- Next work: V337 should target a measured visual audit first (face/hair/eyes/body proportions and browser-versus-Blender consistency), then make one isolated improvement at a time and compare renders. Keep the production GLB unchanged.


## V337 — baseline geometry and proportion audit
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38573867301 — **SUCCESS**.
- First run `38573301972` failed only the new measurement gate: skin topology was masked under clothes at the thighs, and arm vertices inflated some torso slices. V337 was fixed to sample garment geometry for dressed lower-body bands and central x windows for torso bands; second run passed.
- Artifact: [V337 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38573867301/artifacts/11899850651), artifact ID `11899850651`, 54,023,804 bytes, digest `sha256:4be2ca01ef828a8cc8cfc9890b59908115e539d0d0dbb436462b54ec6aeb2f42`.
- GLB: `lam-v337-gltf-materials-full-face-candidate.glb`, 20,168,936 bytes; SHA-256 `4210fb9bc1a874424e0704e4ecc26aca9ed5365c04f18397d0cc8c8c9e38c040` (recomputed from downloaded artifact). The model's base-body height is 1.600 m; whole character bounds are about 1.609 m. It contains 0 glTF skins, 9 images, 12 expected morphs and `Lam_Idle_GentleSway`.
- Windows preview ZIP: `ly-lam-lam-v337-experimental-windows.zip`, 21,346,079 bytes, 81 entries; integrity test passed. SHA-256 `81f2cc1dbebe9847eeb00e2488102a88329525c75f722afcc9cb8367e0ff57bc` matched the `.sha256` sidecar and was independently recomputed.
- Mobile browser: `PASS_BROWSER_WEBGL_CANDIDATE_ONLY` at 390×844; WebGL/renderer ready, `Lam_Idle_GentleSway` advanced, no page or console errors; model was visible inside the tested safe area.
- Measurement baseline (robust widths/depths in metres): head `0.138/0.146`; neck `0.212/0.113`; shoulders `0.495/0.190`; upper torso `0.415/0.186`; waist `0.288/0.217`; hips `0.315/0.214`; upper thigh `0.331/0.156`; mid-thigh `0.350/0.129`. The metric is a comparative proxy using defined mesh bands and filters, not precise anatomy or a likeness score.
- Visual decision: **NOT APPROVED for production**. The V337 render is still essentially the V336 base appearance: a generic MPFB human, conspicuous pale hair rim, and body/face proportions that do not yet match the chosen Lam reference. V337 adds measurement and repeatability, not an appearance improvement.
- Next: V338 isolates a modest MPFB body-weight parameter change from `0.56` to `0.62`, reports the parameter value and repeats the same metrics/tests. All other geometry/material settings remain unchanged so we can judge whether the thighs/hips/body silhouette improve. Production `v312-work/lam-default.glb` stays untouched.## V338 — controlled body-weight comparison
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38574704072 — **SUCCESS**.
- Artifact: [V338 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38574704072/artifacts/11898967693), artifact ID `11898967693`, 54,025,982 bytes; digest `sha256:5737d0905181ae2a099df61026f2f44dcf1c07157de699d32e968506123d80bf`.
- Controlled change verified in report: MPFB macro `weight` is `0.62` rather than V337's `0.56`; all other macro parameters match the V337 baseline.
- GLB: `lam-v338-gltf-materials-full-face-candidate.glb`, 20,168,940 bytes; SHA-256 `78d9bcc519d88148c7a463aa4fc15460e5031dd93fa98420763bee7856f4e13e` (verified against downloaded bytes); 0 glTF skins, 9 images, 12 morphs, `Lam_Idle_GentleSway`.
- Windows preview ZIP: `ly-lam-lam-v338-experimental-windows.zip`, 21,344,726 bytes, 81 entries, ZIP integrity passed. SHA-256 `677e91cefe83ae8253867c0101496dcd0e58ed84d4526ee12e2b626383a152a4` matched its sidecar and was independently recomputed.
- Mobile browser passed at 390×844: WebGL and renderer ready, animation advanced, no browser page/console errors, and avatar remained within the safe area.
- Geometry comparison against V337: waist width `0.28790 → 0.29249 m` (+1.6%); hips `0.31450 → 0.31698 m` (+0.8%); upper thigh `0.33139 → 0.33406 m` (+0.8%); mid-thigh `0.35003 → 0.35102 m` (+0.3%). Depth changes were similarly small. The weight parameter change had only a subtle measurable effect on the dressed silhouette.
- Visual decision: **NOT APPROVED for production**. The V338 render is visually almost unchanged from V337; the generic base appearance, bright hair rim, and not-yet-matched face/body remain. Passing the technical pipeline does not mean the likeness is acceptable.
- Next: V339 will return to the V337 macro baseline (`weight=0.56`) and test an explicit, smooth geometric adjustment only to dressed hip/upper-thigh/mid-thigh volume and rear hip projection. The adjustment will be applied consistently to skin and clothing meshes, with all facial, hair, material, morph and animation settings held constant. The V337/V338 candidates and production GLB remain untouched.
## Safety and rollback
- Do not copy any candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Keep all builds, renders, reports, and ZIPs under versioned candidate artifacts. Record SHA-256 only after checking actual bytes against the sidecar.
- A technical PASS means the automation gates succeeded; it does not, by itself, mean an avatar is visually approved.
