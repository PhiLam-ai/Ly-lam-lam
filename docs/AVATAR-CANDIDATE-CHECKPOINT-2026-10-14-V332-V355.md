# Lý Lâm Lam avatar candidate checkpoint — V332–V355 (2026-10-14/15)

## Release decision

**No current candidate is approved as the production avatar.** Production `main/v312-work/lam-default.glb` and the production viewer remain separate from the experimental branch `avatar/v313-repair-candidate-20261014`. A technical PASS does not substitute for Phi's visual approval of the complete Lam likeness.

## Accepted experimental building blocks

- **V340 body silhouette:** central-x falloff keeps the fuller hips and thighs while preserving the arm width. Visual shape experiment accepted for further candidate work; not a full-avatar approval.
- **V341 hair:** luminance-compressed darkened hair diffuse, alpha/UV preserved, glTF material verified from embedded image pixels. Visible pale crown rim substantially reduced.
- **V345 smile baseline:** the later closed-lip gentle-smile experiment at strength 0.40 is the adopted smile baseline for the eye-material work. This is distinct from V342's earlier 0.12 smile, which was technically successful but too subtle to read reliably in the full-body mobile view.
- **V350 eye front-surface material:** the existing high-poly eye mesh's four connected components are kept in place and two front components per side receive a restrained glTF-compatible specular/clearcoat response. No eye geometry is changed.
- **V352 fill lighting:** an isolated browser-only lighting change (no GLB change) brightens the eye/nose/mouth area and softens hard shadows. The A/B was judged a provisional viewer-lighting improvement; the face still does not match the chosen Lam likeness.
- **V353 Windows preview:** successful 81-entry package `ly-lam-lam-v353-experimental-windows.zip`; SHA-256 `23fce310d69e73cd78389ddb2f50c4557985a59e84c6d6f31f578a3563ed4b81` verified against the sidecar and downloaded bytes. It contains the exact V350 model GLB (20,484,436 bytes; SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`) plus the V352 viewer-only fill-lighting change. The V353 package is preview-only and is not a production promotion.

Detailed previous checkpoint evidence:
- [V332–V342 build, geometry, hair and early smile work](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v313-repair-candidate-20261014/docs/AVATAR-CANDIDATE-CHECKPOINT-2026-10-14-V332-V342.md)
- [V348–V353 eye, browser lighting and preview package review](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v313-repair-candidate-20261014/docs/AVATAR-CANDIDATE-CHECKPOINT-2026-10-14-V348-V349.md)

## V343 parallel smile experiment — duplicate, not adopted

A separate V343 run was created from the earlier V342 conversation checkpoint after the branch had already progressed through V344–V353. The run `38607779884` is a duplicate experiment and must not replace the later closed-lip smile baseline or be treated as the latest avatar candidate. Compare by workflow/run ID and source script, not version label alone; some experiment tracks reused V343 labels.

## V354 — necklace accessory candidate (first build PASS; preview correction in progress)
- First workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38608109632 — **SUCCESS**. Artifact [V354 model and preview](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38608109632/artifacts/11916582610), ID `11916582610`, 58,926,828 bytes, digest `sha256:85c8fc28331495dce142fa9a3c3df320fa093638c7a90b317ddd62a7da52039d`.
- GLB `lam-v354-gltf-materials-full-face-candidate.glb`: 20,558,512 bytes, SHA-256 `afbf18bb80132d9f9c5b79055d8157291dd10a8f7c1d9f7abe2a6af5669b0bac`. Export retained 0 glTF skins, all 12 morphs, `Lam_Idle_GentleSway`, V340 lower-body shaping, V341 dark hair, V345 smile and V350 eye-front material response.
- Necklace report: two exported meshes (`V354_NecklaceChain`, 1,164 vertices; `V354_NecklacePendant`, 362 vertices). Seven chain points and the pendant position were sampled from the current front surface. Gold material: metallic `0.55`, roughness `0.28` and both GLB nodes were verified.
- Windows ZIP `ly-lam-lam-v354-experimental-windows.zip`: 21,696,939 bytes, 81 entries; integrity passed. SHA-256 `0ba9c458bc059976f289634ef190e47a6067c67da35ed7afae091e6be4e013c4` matched the sidecar and was independently recomputed. The first run's browser/preview package did **not** carry the V352 fill-light patch, which made the browser face darker than V353.
- Visual review: the necklace is visible, but the pendant sits over the orange human-shaped shirt logo and looks partly integrated into the printed graphic. **Accessory position not approved.** Do not promote the first V354 ZIP.
- Workflow correction: `.github/workflows/v354-necklace-accessory.yml` now patches only its temporary viewer copy with the V352 fill lighting before browser capture and packages that patched copy. It explicitly verifies the fill-light block in the temporary viewer and Windows ZIP. This rerun keeps the GLB/model unchanged: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609085207 (in progress).

## V355 — necklace logo-clearance experiment (run in progress)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609383368.
- Script: `tools/blender_v355_necklace_logo_clearance.py`; workflow: `.github/workflows/v355-necklace-logo-clearance.yml`.
- V355 changes one parameter family only: all seven chain centerline z positions and the pendant center move upward by `0.06 m`, from the V354 chain z values `[1.183, 1.188, 1.202, 1.226]` to `[1.243, 1.248, 1.262, 1.286]`; pendant center z becomes `1.243 m`. Every point is still placed using a measured front-surface sample, so the chain remains fitted to the shirt/skin rather than using a guessed Y coordinate.
- All body/face/hair/clothing/eye geometry, materials, smile/morph controls, idle animation and the gold necklace PBR values remain unchanged. The V352 fill-light patch is included in the temporary browser test and Windows preview package.
- Gates verify necklace mesh export, the exact z adjustment, seven valid chain samples, pendant sample, all 12 morphs, eye/hair audits, mobile WebGL, no browser/console errors, fill-light patch presence, ZIP integrity and SHA-256. Visual decision pending: inspect front/face-closeup/browser captures to verify it clears the shirt graphic without floating or clipping.
## Safety and rollback

- Do not copy any experimental GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Always inspect the actual V354 images and browser capture, not only the green workflow status.
- Record SHA-256 only after recomputing the downloaded file's bytes and matching the package sidecar.
- Preserve the previous successful preview and stable production files.