# Lý Lâm Lam avatar candidate checkpoint — 2026-10-14 (V332–V347)

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
- Next: V339 will return to the V337 macro baseline (`weight=0.56`) and test an explicit, smooth geometric adjustment only to dressed hip/upper-thigh/mid-thigh volume and rear hip projection. The adjustment will be applied consistently to skin and clothing meshes, with all facial, hair, material, morph and animation settings held constant. The V337/V338 candidates and production GLB remain untouched.## V339 — targeted hip/thigh geometry candidate
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38575983967 — **SUCCESS**.
- Artifact: [V339 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38575983967/artifacts/11899868405), ID `11899868405`, 54,031,175 bytes, digest `sha256:39ffcfa8f6e5ffb7cc6bd0822f9429f90ebd0868df45f5558e7724e5428dcdf3`.
- GLB: `lam-v339-gltf-materials-full-face-candidate.glb`, 20,168,936 bytes; SHA-256 `a3d6271fdc9e1a92b8f876cfd29829eee178fafa6a74b0ae72fb35fb99e8d58e`. It retains 0 glTF skins, 9 images, 12 morphs and `Lam_Idle_GentleSway`; macro `weight` remains `0.56`.
- Windows ZIP: `ly-lam-lam-v339-experimental-windows.zip`, 21,346,228 bytes, 81 entries; integrity passed. SHA-256 `dddbe8e5b79068a589749ced89c4476a302eabdd3d1306cda5c662c33c8a269a` matched the sidecar and was independently recomputed.
- Mobile browser: PASS at 390×844, WebGL/renderer ready, idle animation advanced, no page/console errors.
- Measured versus V337: hips width `0.31450 → 0.34010 m` (+8.1%) and depth `0.21384 → 0.23561 m` (+10.2%); upper-thigh width `0.33139 → 0.35563 m` (+7.3%); mid-thigh width `0.35003 → 0.37215 m` (+6.3%); waist width `0.28790 → 0.29599 m` (+2.8%).
- Visual decision: **NOT APPROVED**. The intended lower-body fullness is visible, but the vertical-only deformation also widened portions of the arms that happened to occupy the same height bands. This unintended silhouette change needs correction before using the model.
- Next: V340 adds central-x falloff to the same lower-body adjustment so arms remain outside the deformation zone. Production remains unchanged.## V340 — central-x falloff refinement
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38577074765 — **SUCCESS**.
- Artifact: [V340 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38577074765/artifacts/11900737119), ID `11900737119`, 54,039,693 bytes; digest `sha256:f230a768023fae13aada182440981580a8352500c4aca20517b68a8f78e8107b`.
- GLB: `lam-v340-gltf-materials-full-face-candidate.glb`, 20,168,940 bytes; SHA-256 `29ea7881708a78995d7f63156a1832af1e1e1d93c58de671c68ec892203fee89` (verified against downloaded bytes). Macro weight remains `0.56`; 0 glTF skins, 9 images, 12 morphs, `Lam_Idle_GentleSway`.
- Windows preview ZIP: `ly-lam-lam-v340-experimental-windows.zip`, 21,346,135 bytes, 81 entries; integrity passed. SHA-256 `43aa41619e299be0dca9a3590fe3b884a5c860fd625271c1f2983ac143dcb1d4` matched its sidecar and was independently recomputed.
- Mobile browser passed at 390×844: WebGL/renderer ready, animation advanced, no page or console errors; avatar visible in safe area.
- Profile compared with V337: hips width `0.31450 → 0.34010 m` (+8.1%) and depth `0.21384 → 0.23561 m` (+10.2%); upper-thigh width `0.33139 → 0.35563 m` (+7.3%); mid-thigh width `0.35003 → 0.37215 m` (+6.3%); waist width `0.28790 → 0.29599 m` (+2.8%). The outer character width returned to `0.983713 m` (V337 baseline) after adding central-x falloff, whereas V339 reached `1.051008 m` because arm vertices were also widened.
- Visual review: central hips/thighs are fuller than V337, while the arm spread is back near baseline and no obvious clothing gap is visible in the supplied front/browser/side images. **Shape experiment accepted for further work; whole avatar NOT APPROVED for production** because face likeness and hair rim remain unresolved.
- Next isolated target: audit and correct the bright hair rim at the material/lighting level without changing the accepted V340 lower-body geometry. Keep production `v312-work/lam-default.glb` unchanged.## V341 — hair diffuse highlight/material correction
- Final workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38580067114 — **SUCCESS**.
- Artifact: [V341 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38580067114/artifacts/11902229536), ID `11902229536`, 57,865,072 bytes; digest `sha256:8989c581460b8307e354a13627dbb289b2c44aabc32c6c005ec6db86dad52a1e`.
- GLB: `lam-v341-gltf-materials-full-face-candidate.glb`, 20,483,064 bytes; SHA-256 `0a3917b6b90be0b1400911536e6677dec60b6e1b56d5407f532c85dff94f4abe` verified from the downloaded artifact. It retains 0 glTF skins, 9 images, 12 expected morphs, `Lam_Idle_GentleSway`, 1.60 m body height and the V340 central-gated lower-body shape.
- Hair audit: source `long01_diffuse.png` (2048² RGBA) became `V341_HairDiffuse_Darkened`; channel alpha preserved, same UVMap, roughness `0.86`, specular IOR level `0.12`. The original source mean linear RGB was `0.10221`, processed texture mean `0.06316`, and the actual embedded GLB texture mean `0.06321`; the embedded-pixel audit passed. The glTF image label still says `long01_diffuse` because the exporter preserves the source filepath label, so verification is based on decoded embedded pixels rather than that label.
- Windows preview ZIP: `ly-lam-lam-v341-experimental-windows.zip`, 21,652,163 bytes, 81 entries, ZIP integrity passed. SHA-256 `0e08a534b706cf52527c0996158220a15581ed1a3e0f9161eb8b5f1b43c4425f` matched its `.sha256` sidecar and was independently recomputed.
- Mobile browser: `PASS_BROWSER_WEBGL_CANDIDATE_ONLY` at 390×844; WebGL/renderer ready, `Lam_Idle_GentleSway` advanced, no page/console errors, avatar visible within safe area.
- Visual review: V341 substantially reduces the pale/white crown rim; hair remains dark brown with strand detail. The face still looks like a generic MPFB base and the facial expression is neutral/stiff. **Hair-material experiment accepted for further work; full avatar remains NOT APPROVED for production.**
- Next target: V342 addresses the neutral face expression with a small, documented default smile while preserving all 12 morph controls. Do not change the face mesh, body, hair or clothes in the same experiment. Production `v312-work/lam-default.glb` remains unchanged.## V342 — gentle smile neutral face pose
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38581370585 — **SUCCESS**.
- Artifact: [V342 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38581370585/artifacts/11903896107), ID `11903896107`, 57,867,261 bytes; digest `sha256:59fde7815f2a5f9e4ec5bf750a81d5e721da953f1f89c9d4a5da5595635677bc`.
- GLB: `lam-v342-gltf-materials-full-face-candidate.glb`, 20,483,060 bytes; SHA-256 `31c9298744de0df9c96558931f086541ff7d77aab41d27b47525a0052d4e19e8`. Body bounds, V340 lower-body shaping and V341 hair pixel audit remain unchanged.
- Default face pose: `gentle_smile`, strength `0.12`, applied to 19,532 coordinates across the body and face accessory objects that carry a smile shape key; maximum neutral face displacement on the base head mesh was approximately 1.59 mm. The full-smile endpoint is preserved and all 12 glTF morph names remain present.
- Hair audit passed: source mean linear RGB `0.10221`, processed image `0.06316`, embedded GLB image `0.06321`; RGBA alpha retained, roughness `0.86`, `alphaMode=BLEND`.
- Windows preview ZIP: `ly-lam-lam-v342-experimental-windows.zip`, 21,652,678 bytes, 81 entries; integrity passed. SHA-256 `236952a3892b15c793c6b312546a6c64adb66ee712f9aa710c8f40a5117e01f3` matched its `.sha256` sidecar and was independently recomputed.
- Mobile browser: PASS at 390×844, WebGL/renderer ready, `Lam_Idle_GentleSway` advanced, no page/console errors, visible avatar within safe area.
- Visual decision: **technical PASS; smile effect too subtle for final approval**. Side-by-side face close-ups show only a small lift at the mouth corners. Keep this version as the verified baseline; V343 will use strength `0.20` while preserving the same full-smile endpoint and all other settings. Full avatar remains NOT APPROVED for production.## V343 — gentle smile tuning, strength 0.20
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38582318943 — **SUCCESS**.
- Artifact: [V343 tuning artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38582318943/artifacts/11902964067), ID `11902964067`, 57,868,154 bytes; digest `sha256:5f2296773fb5704b4cc0a885d66bc3913cbb0123343aca920c170fbd00d9e765`.
- GLB `lam-v343-gltf-materials-full-face-candidate.glb`, 20,483,064 bytes; SHA-256 `ace103c54dde6cb9f6d16ab32a73357ba67e24a939758537420fcb8a1d5aa6b5`.
- The neutral smile factor is `0.20`; all 12 morphs and the original full-smile endpoint are retained. Windows ZIP: `ly-lam-lam-v343-experimental-windows.zip`, 21,652,907 bytes, 81 entries, integrity passed; SHA-256 `6b87d04ebd961fe1d720cf8b7bf1db2aacec12a319f31c35619cd9d28097eb14` matched the sidecar.
- Visual review: the mouth corners lift only slightly and the default face still reads close to neutral in the full-face crop. **Technical PASS; default-smile visual improvement insufficient for approval.** Keep V343 as baseline and test a stronger amount.

## V343-strength alternate attempt — 0.24 (failed before model build)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38582896994 — FAILURE because the workflow called the stale script path `tools/blender_v343_gentle_smile_base_pose.py`, which does not exist. This is a workflow path fault, not an avatar or morph failure. No valid candidate package was produced from this run.
- To avoid two experiments with the same version number, the `0.24` attempt is tracked as **V344** below.

## V344 — stronger default gentle smile, strength 0.24
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38583341070 — **SUCCESS**.
- Artifact: [V344 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38583341070/artifacts/11903488722), ID `11903488722`, 57,867,391 bytes; digest `sha256:2fb1f333cbd3f5425d7ad87fa64fa352188b3936f46c034481c6e855e63f4da2`.
- GLB `lam-v344-gltf-materials-full-face-candidate.glb`, 20,483,064 bytes; SHA-256 `7357baab143e891620a9e54af72002a1b7f29ae371efe05351747d26476cb7ce`. It retains 0 glTF skins, 9 images, all 12 expected morphs, `Lam_Idle_GentleSway`, V340 central-gated body shape and V341's embedded hair pixel verification.
- Default-smile factor `0.24`; max neutral head displacement `0.00317227 m` (about 3.17 mm). The original full-smile endpoint was preserved. Hair source/processed/embedded mean RGB values remain `0.10221/0.06316/0.06321`; alpha mode is `BLEND` and roughness `0.86`.
- Windows ZIP `ly-lam-lam-v344-experimental-windows.zip`, 21,652,928 bytes, 81 entries, integrity passed. SHA-256 `9ae81acb2a22fb2d0dbf5a3f9cbd16660e1b4c6ce7dce2e73b211f60783cabc2` matched the sidecar and was independently recomputed.
- Mobile browser passed at 390×844: WebGL/renderer ready, idle animation advanced, no page/console errors, visible within safe area.
- Visual decision: **TECHNICAL PASS, SMILE VISUAL STILL NOT APPROVED**. The close-up still looks near-neutral and the mouth-corner lift is hard to see. V344 remains a stable technical checkpoint, not a production-ready avatar.

## V345 — visible gentle smile, strength 0.40
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38584422127 — **SUCCESS**.
- Artifact: [V345 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38584422127/artifacts/11904701856), ID `11904701856`, 57,868,450 bytes; digest `sha256:eef74e13cc8c9e1d7cf5579354f33c0f399493fbee1f8bd0c0431b39b71417d1`.
- GLB `lam-v345-gltf-materials-full-face-candidate.glb`, 20,483,060 bytes; SHA-256 `a365be787131cbfefe5da33687e61c5f2df5aab8f1b3ee333e17c799d617752a` independently recomputed and matched report.
- Default smile factor `0.40`; maximum neutral displacement on the main head mesh `0.00528712 m` (about 5.3 mm). The original full-smile endpoint is preserved. All 12 expected morph names remain exported.
- Windows ZIP `ly-lam-lam-v345-experimental-windows.zip`, 21,653,007 bytes, 81 entries, ZIP integrity passed. SHA-256 `3fd5d90d1386c08ab82dcb954e2fd31279f2944684cca701e0eee65fc332548f` matched the sidecar and was independently recomputed.
- Mobile browser: `PASS_BROWSER_WEBGL_CANDIDATE_ONLY` at 390×844; GLB returned HTTP 200, WebGL loaded, `Lam_Idle_GentleSway` advanced, no page errors, console errors or failed requests, model visible in safe area.
- Visual decision: **default gentle-smile improvement accepted for further work**. Compared with V342–V344, the mouth corners now read as a small closed-mouth smile without obvious pinching/asymmetry in the face close-up. The whole avatar remains **NOT APPROVED for production** because the face still looks generic and eye/iris realism is weak.

## V346 — eye material/iris realism diagnostic
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38589926509 — **SUCCESS**.
- Artifact: [V346 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38589926509/artifacts/11906878183), ID `11906878183`, 57,869,623 bytes; digest `sha256:fb285149ca468acc48e3d72b199fe51020470ea5b8b517fd00b02005f8ddc8e8`.
- GLB `lam-v346-gltf-materials-full-face-candidate.glb`, 20,483,280 bytes; SHA-256 `2db32c9f84a79b77b913282990b541d2961f4e567039597b09b09c9cd8c2c839` independently recomputed. It retains all 12 expected morphs, `Lam_Idle_GentleSway`, V340 body shape, V341 hair material and V345 default-smile strength 0.40.
- Eye material is `V346_GltfCompatibleAccessory_high-poly`; existing texture `brown_eye.png`, UVMap and RGBA alpha behavior are unchanged. Roughness `0.32`, specular IOR level `0.38` (glTF `KHR_materials_specular` factor `0.76`), clearcoat `0.10`, clearcoat roughness `0.24`. glTF audit confirms the image/UV link and both specular/clearcoat extensions were exported.
- Windows ZIP `ly-lam-lam-v346-experimental-windows.zip`, 21,653,047 bytes, 81 entries, ZIP integrity passed; SHA-256 `1792e7108c8d3b7ea2a2fedb7c5b2318008dc5d7009137c8c88a2e45f20c53d7` matched the `.sha256` sidecar and was independently recomputed.
- Mobile browser passed at 390×844: WebGL ready, HTTP 200, `Lam_Idle_GentleSway` advanced, no page/console/failed-request errors, avatar visible in safe area.
- Visual review: compared eye crops side by side with V345. The slightly lower-roughness/clearcoat response creates a modest added eye highlight/depth without obvious plastic glare or washed-out iris. **Eye-material experiment accepted for further work; whole avatar remains NOT APPROVED** because facial likeness and overall eye prominence/detail still need improvement.
- Next: V347 should diagnose eye mesh scale/position relative to the visible face and produce a dedicated tighter eye/face comparison capture before any geometry change. Keep texture and material values at V346 baseline during that measurement-only step; do not promote to production.## V347 — eye geometry measurements and dedicated close-up
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38591394703 — **SUCCESS**.
- Artifact: [V347 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38591394703/artifacts/11907408592), ID `11907408592`, 58,713,205 bytes; digest `sha256:26aaf95cdd7cbda32244c9ab3fead289e92a82ed9395a60d808b5477358e011a`.
- GLB: `lam-v347-gltf-materials-full-face-candidate.glb`, 20,483,280 bytes; SHA-256 `539d2f169986e6e8208ae0d2df941021a2584d59876583cfd8ab4cdec0a25782` independently recomputed. Retains 12 morphs, `Lam_Idle_GentleSway`, V340 body silhouette, V341 hair and V346 eye material. `eye_geometry_diagnostic.geometry_changed` is `false`.
- Measurement: eye mesh `Human.high-poly`, 1,064 vertices, four connected components of at least 20 vertices (two nearly overlapping components per side). Combined eye bounds span `0.090434 m` in X, `0.021453 m` in Y, `0.028626 m` in Z; center `(0, -0.122154, 1.494041) m`. Head-band width is `0.224369 m`, so eye-pair-span/head-band-width ratio is `0.40306`. These are mesh diagnostics, not an anatomy score or direct comparison against a face-reference photograph.
- New image `v347-eye-closeup.png` captures the eyes at 1000×700; it shows the brown iris texture and eyelid/lash relation clearly. The V346 specular/clearcoat material still produces only restrained catchlights in this lighting, so the eye surface may require a component-specific front-shell response rather than arbitrary enlargement of the whole eye mesh.
- Windows ZIP `ly-lam-lam-v347-experimental-windows.zip`, 21,653,013 bytes, ZIP integrity passed. SHA-256 `1ffb60bf93b97021a010536bfb15b78b565ca68d4ce8b10336b8fe8b22c0ed5b` matched its sidecar and was independently recomputed.
- Mobile browser passed at 390×844: WebGL ready, `Lam_Idle_GentleSway` advanced, no page/console/failed-request errors, avatar visible within safe area.
- Visual decision: **MEASUREMENT/CAPTURE PASS; FULL AVATAR NOT APPROVED**. The tighter image makes the remaining weakness clear: iris texture is present, but the eyes lack obvious natural catchlights and still read somewhat flat at the default view.
- Next: V348 will isolate the more forward of the two overlapping eye components on each side and give that surface a restrained higher-specular/lower-roughness response, while preserving the eye diffuse image/UV/alpha and leaving eye size/position, body, hair, smile and other morphs untouched. Compare before/after eye-closeup and mobile capture; if component separation is not confirmed safe, revert this branch of the experiment.
## Safety and rollback
- Do not copy any candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Keep all builds, renders, reports, and ZIPs under versioned candidate artifacts. Record SHA-256 only after checking actual bytes against the sidecar.
- A technical PASS means the automation gates succeeded; it does not, by itself, mean an avatar is visually approved.
