# Lý Lâm Lam avatar candidate checkpoint — V332–V356 (2026-10-14/15)

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
- Workflow correction: `.github/workflows/v354-necklace-accessory.yml` patches only its temporary viewer copy with the V352 fill lighting before browser capture and packages that patched copy. Its validation rerun https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609085207 — **SUCCESS**. Artifact [V354 lighting-corrected preview](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609085207/artifacts/11916273859), ID `11916273859`, 58,951,617 bytes; digest `sha256:3904a29991faa1466ddaed056910b0d2b597c5f1f5a74e551166db0195bc35a3`.
- Corrected Windows ZIP `ly-lam-lam-v354-experimental-windows.zip`: 21,697,103 bytes, 81 entries; integrity passed. SHA-256 `d02eb6f5ca70ac3b06bfc687e7b9431cbe14d96dd108c26ab635e973f98458d3` matched its `.sha256` sidecar and was independently recomputed. The packaged viewer was verified to contain the V352 `faceFill` light block.
- Corrected build GLB: `lam-v354-gltf-materials-full-face-candidate.glb`, 20,558,512 bytes; SHA-256 `cc4c255639ff96d9ac3716362b7030c71400723c27581efe09b200dd05062a3b` (per this run's actual bytes). Browser test passed: WebGL ready, 12 morphs present, animation advanced, no page/console errors.
- Visual decision remains **NOT APPROVED for necklace placement**: the gold pendant is still centered directly over the shirt's orange logo. The corrected fill lighting is in place, but it does not change the necklace/model geometry.

## V355 — necklace logo-clearance experiment
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609383368 — **SUCCESS**.
- Artifact: [V355 tested model/preview](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609383368/artifacts/11916744125), ID `11916744125`, 58,960,107 bytes; digest `sha256:841489998ebb0e32e35b3c44392d949e1e4dfaa7302fc8f9313c7c8a24489cd0`.
- GLB `lam-v355-gltf-materials-full-face-candidate.glb`: 20,558,512 bytes; SHA-256 `bad4e0dbc81d76f9745455576a79f54adc693a8af54a8f3ecf6a842218b2002b`. It retains the 12 morphs, `Lam_Idle_GentleSway`, V340 body silhouette, V341 dark hair, V345 closed-lip smile and V350 eye material response.
- Windows ZIP `ly-lam-lam-v355-experimental-windows.zip`: 21,698,158 bytes, 81 entries; integrity passed. SHA-256 `1a9949099f651977c5a7a998136b97cb81b1ee5c6ac5c3c739d662c16b708b47` matched the sidecar and was independently recomputed. Packaged viewer contains the V352 fill-light patch.
- Placement audit: chain z values are `[1.243, 1.248, 1.262, 1.286]` metres; pendant center is at `1.243 m`, all surface sample counts are nonzero, and both necklace mesh nodes/material passed export. Mobile browser passed at 390×844, animation advanced, no page/console errors.
- Visual decision: **POSITION IMPROVED, NOT YET APPROVED**. The gold pendant now sits above the shirt icon's head, but the chain/pendant still intersects the white circular outline around the logo. V356 will move the same chain shape and pendant a further `0.04 m` upward; no other model property should change.## V356 — necklace collar-clearance experiment (run in progress)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38609650284.
- Script: `tools/blender_v356_necklace_collar_clearance.py`; workflow: `.github/workflows/v356-necklace-collar-clearance.yml`.
- V356 is a second isolated position correction from V355: the same chain curve and pendant move upward by another `0.04 m`. Candidate chain z values become `[1.283, 1.288, 1.302, 1.326]` metres and pendant center z is `1.283 m`; all points are still sampled against front surfaces.
- Gold material stays at metallic `0.55` and roughness `0.28`. No body, face, hair, clothes, eye-material, morph or animation changes are intended. The temporary viewer and Windows ZIP keep the V352 fill-light patch, and the workflow verifies it is present.
- Gates check baseline V355 and exact 4 cm shift, valid chain/pendant mesh export, seven chain samples, pendant sample, all 12 morphs, eye/hair materials, mobile WebGL/no browser errors, preview lighting, ZIP integrity and SHA-256. Visual approval is pending; compare the logo ring clearance against V355 and reject if the chain appears detached or clipped.
## Safety and rollback

- Do not copy any experimental GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Always inspect the actual V354 images and browser capture, not only the green workflow status.
- Record SHA-256 only after recomputing the downloaded file's bytes and matching the package sidecar.
- Preserve the previous successful preview and stable production files.