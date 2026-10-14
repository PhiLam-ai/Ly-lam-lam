# Lý Lâm Lam avatar candidate checkpoint — V348–V351 (2026-10-14)

## Release decision

**No candidate here is approved as the production avatar.** Production `v312-work/lam-default.glb` is not to be replaced by this experimental eye-material branch. All work remains on `avatar/v313-repair-candidate-20261014`.

## V348 — front eye surface response experiment

- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38592942741 — **FAILED at a validation assertion after GLB export and render generation**.
- Script: `tools/blender_v348_eye_front_surface_response.py`.
- Artifact: [V348 diagnostic artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38592942741/artifacts/11908337440), ID `11908337440`; workflow artifact digest `sha256:0168c8b872475bce2cdb1d25eb1238364c74f718ec4c2dcb10a7833e8bb78272`.
- The visual evidence includes `v348-eye-closeup.png`. It shows brown iris texture and eyelash detail; the front eye-shell component is assigned a restrained glTF-compatible response (roughness 0.18, specular IOR level 0.50, clearcoat 0.30, clearcoat roughness 0.14), while the base eye material and image are preserved.
- Root cause of the failing gate: it compared `pbrMetallicRoughness.baseColorTexture.index` between the base eye and front eye materials. In glTF this is a **texture-object index**, not an image identifier. The exported GLB legitimately has two texture entries that both point to the same embedded `brown_eye` image: base texture index `5` → image source `5`, front texture index `6` → image source `5`. Thus the check rejected a valid shared-image mapping.
- The fix must compare `gltf.textures[textureIndex].source` values, validate each source index, and record both texture and image-source indices. The evidence indicates a faulty assertion, not proof that the wrong diffuse image was used.

## V349 — validate shared eye image by glTF source index (rerun in progress)
- First workflow attempt: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38599437117 — **FAILED** in the audit/report code after successful GLB export and eye-closeup render. The GLB had the expected source-image mapping (base texture index 5 → image source 5; front texture index 6 → image source 5), but the new report tried to read `eye_image_source_index` before it had been initialized.
- Fix commit: `9a9f0306a6be5b68bf22882baa55e4c7ef9aa75c` moves base-image source resolution before building the base-eye report. It changes no geometry or material values.
- Current validation rerun: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38600138150.
- Script: `tools/blender_v349_eye_front_surface_texture_source_fix.py`.
- V349 carries forward the V348 front-eye material experiment, V340 body silhouette, V341 darkened hair material, and a closed-mouth gentle default smile from the later smile branch. It changes only validation/reporting of the eye's shared diffuse image; it does not increase eye size or move eye geometry.
- New report fields include `base_color_image_source_index`, `base_color_image_name`, and `same_image_source_as_base_eye` for the two eye materials. The workflow gate verifies source-index equality, both material extensions, roughness values, transparency mode, 12 expected morphs, idle animation, mobile WebGL load, no browser/console/failed-request errors, ZIP integrity and SHA-256 sidecar.
- Visual review is pending until the rerun produces its report, GLB, eye close-up and browser capture. A technical PASS would validate the export and test path; it would not by itself approve the full avatar likeness.
## V350 — front-eye specular extension export fix (validation rerun)
- Earlier workflow attempts: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38600818409 (first had a duplicated comma in the summary) and its rerun https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601219481 (second had two missing commas in the embedded report dictionary). Both reached GLB export; neither ran the mobile/browser gates.
- The GLB from the initial attempt (`lam-v350-gltf-materials-full-face-candidate.glb`, 20,484,436 bytes, SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`) was independently inspected. It contains `V350_GltfEyeFrontSurface` with `KHR_materials_specular.specularFactor ≈ 0.96`, clearcoat `0.30`, roughness `0.18`, and `alphaMode=BLEND`. Both the base and front eye texture entries map to image source index `5` (`brown_eye`).
- Latest validation run after fixing both summary syntax issues: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601681760.
- Script: `tools/blender_v350_eye_front_surface_specular_export.py`; workflow: `.github/workflows/v350-eye-front-surface-specular-export.yml`.
- New front-eye specular setting is `0.48` in Blender so glTF exports a non-default factor near `0.96`; the base material is unchanged (`0.38` / `0.76`). Clearcoat remains `0.30`, coat roughness `0.14`, front roughness `0.18`. Eye size/position, `brown_eye` image/UV/alpha, V340 body shape, V341 hair, the 0.40 closed-mouth smile and the 12 morphs are unchanged.
- Final workflow run: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601681760 — **SUCCESS**.
- Artifact: [V350 GitHub Actions artifact](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38601681760/artifacts/11914695268), ID `11914695268`, 58,716,807 bytes; digest `sha256:b55ba21fe7ec2d4555216b6b06f2163b6a1d6bcf8ce3e6be92493575d5b05334`.
- Re-downloaded artifact verification: GLB `lam-v350-gltf-materials-full-face-candidate.glb`, 20,484,436 bytes, SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`; Windows preview ZIP `ly-lam-lam-v350-experimental-windows.zip`, 21,653,923 bytes, SHA-256 `a5c48d6c84c156bb5831e5b6c0c05def86ea1fec431b793711a524c4cacea304`, matched its sidecar and passed ZIP integrity.
- V350 browser smoke passed at 390×844: GLB HTTP 200, WebGL ready, `Lam_Idle_GentleSway` advanced, no page/console/failed-request errors and avatar within the mobile safe area.
- Visual review of `v350-eye-closeup.png`: eye texture/eyelash detail is visible and the front-shell specular response creates modest natural catchlights without obvious washed-out irises. **Eye-material experiment accepted for further work; whole avatar remains NOT APPROVED for production** because the face is still generic and its overall likeness/proportions need more work.

## V351 — browser face quick-view audit (V350 model unchanged)
- Workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38604800989 — **SUCCESS**. First workflow attempt `38604499942` was blocked by an overstrict Python assertion that rejected a known benign GLB `net::ERR_ABORTED` already classified by the browser script; the gate was corrected to allow only this specific abort when GLB HTTP 200, viewer boot and renderer readiness are all confirmed.
- Artifact: [V351 browser audit evidence](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38604800989/artifacts/11914598351), ID `11914598351`, 515,192 bytes, digest `sha256:8666cfe77ae2141dd8cc5528776afc21df5c99ac66a21ff81d8014f0c21aed44` (re-downloaded and SHA-256 independently verified; ZIP integrity passed).
- Exact source model: V350 run `38601681760`, GLB 20,484,436 bytes, SHA-256 `9e36f37c6e12dfbded9c47dcbf0cfbbfd7e339112aa5a32bcc4d11d9bc0f05ee`. V351 makes **no model or production-code modification**; it uses the same bundled Three.js viewer and GLB in an isolated temporary folder.
- Browser result: `PASS_BROWSER_WEBGL_CANDIDATE_ONLY` at 390×844; WebGL and renderer ready; 12 morphs reported; `Lam_Idle_GentleSway` advanced; `#view-face` found once and clicked; face-view canvas 390×844, 159,931 bytes and 144,984 foreground pixels; no page errors or console errors. One canceled GLB request is retained as a classified benign abort after HTTP 200, and the strict gate rejects any other request failure.
- Evidence files: `v351-candidate-canvas.png` (full-body view), `v351-eye-face-closeup-canvas.png` (after tapping “Khuôn mặt”), `v351-eye-face-closeup-browser.png`, and `v351-candidate-browser-report.json`.
- Visual review: the browser face-view button does work, and the eyes are clearly visible at a useful close-up scale. Compared with Blender, browser shading is darker and harsher around the nose/mouth, and the face remains a generic base. **Audit PASS, visual likeness not approved.**
- Next: V352 will test one isolated lighting adjustment in a temporary candidate viewer copy only, using the same V350 GLB and the same face-close-up capture. Do not modify the main/production `v312-work/index.html` unless the comparison clearly improves the browser rendering; keep the original viewer as rollback.
## Separate smile-strength experiments

The repo has parallel experimental tracks that reused some V34x version numbers. Use the workflow run ID and exact script path as the unique identifier rather than the version label alone.
- An additional V343 strength-0.20 rerun was accidentally started from the earlier V342 chat checkpoint after later V343–V350 experiments already existed: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38603515911 succeeded; its superseded concurrent run `38603453132` was cancelled. Treat it as a duplicate experimental artifact only, not the latest candidate and not a promotion. The successful V345 strength-0.40 closed-lip-smile line remains the adopted smile baseline. The successful closed-lip smile track reached V345 at strength 0.40; the V346 eye-material diagnostic is a separate run from the later “V346 stronger smile with lip closure” candidate. Keep these checkpoints distinct when comparing assets.

## Safety and rollback

- Do not copy a candidate GLB into production `v312-work/lam-default.glb` or promote it through the stable registry.
- Record file checksums only after recomputing actual downloaded bytes and matching the sidecar.
- Preserve the stable avatar and previous successful candidate artifacts; visual review remains mandatory after every material/geometry change.
