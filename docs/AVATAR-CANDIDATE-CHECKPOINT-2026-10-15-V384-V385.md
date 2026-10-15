# Avatar candidate checkpoint — V384 rejected visually; V385 technical pass (2026-10-15)

## Decision

- V384 is **not accepted visually**: the 35-degree arm rotation with an early lower fade left hand/finger points insufficiently transformed, producing visibly elongated finger streaks.
- V385 is **accepted as the next pose baseline for further candidate work** because the gentler 22-degree rotation and lower fade improve wrist/palm/finger continuity. This is not approval of the full avatar and is not a production promotion.
- Production `main/v312-work/lam-default.glb` remains unchanged. All changes and the Windows preview package are experimental and isolated to `avatar/v385-arm-pose-continuity`.

## V385 source and workflow

- Branch: [avatar/v385-arm-pose-continuity](https://github.com/PhiLam-ai/Ly-lam-lam/tree/avatar/v385-arm-pose-continuity)
- Builder: [tools/blender_v385_arm_pose_continuity.py](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v385-arm-pose-continuity/tools/blender_v385_arm_pose_continuity.py)
- Temporary viewer camera-fit helper: [tools/v385_apply_viewer_camera_fit.cjs](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v385-arm-pose-continuity/tools/v385_apply_viewer_camera_fit.cjs)
- CI workflow: [V385 Arm Pose Continuity Candidate](https://github.com/PhiLam-ai/Ly-lam-lam/blob/avatar/v385-arm-pose-continuity/.github/workflows/v385-arm-pose-continuity.yml)
- Final successful workflow: https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38675513285
- Final Actions artifact ID: `11946086826` (49,104,679 bytes; retained by GitHub Actions as of checkpoint).

## V385 geometry evidence

- GLB: `lam-v385-gltf-materials-full-face-candidate.glb`
- GLB size: `13,959,468` bytes
- GLB SHA-256: `7769c5abc6463fdea60ca3ae12097ae92004ae3ca0869a04f598cfe7db92852a`
- GLB structure: 30 meshes, 31 nodes, 0 glTF skins, 9 textures, 19 materials, 12 expected facial morphs, animation `Lam_Idle_GentleSway`.
- Arm pose: max angle `22°`; 3,852 measured weighted vertices; max lateral extent changed `0.492894 m → 0.397871 m`; mean lateral reduction `0.099259 m`; mean vertical drop `0.073558 m`; maximum displacement `0.155875 m`.
- Protected-region assertions passed: 16,569 torso guard vertices with max displacement `0`; 5,183 lower-body guard vertices with max displacement `0`.
- The builder report deliberately remains `EXPERIMENTAL_V385_GLTFSKIN_FACE_ACCESSORY_CANDIDATE_NOT_APPROVED`.

## Browser/mobile and package gates

- Browser test: `PASS_BROWSER_WEBGL_CANDIDATE_ONLY` at 390×844.
- Viewer booted; WebGL renderer ready; GLB HTTP 200; all local Three.js assets HTTP 200; 12 morph controls reported; `Lam_Idle_GentleSway` advanced; page errors, console errors and failed requests were empty.
- Projected bounds: `minY=-0.7836`, `maxY=0.7836`, vertical coverage `0.7836`, center `0`, `fitsNdc=true`; foreground coverage in unobstructed safe area `0.9656`.
- The first V385 browser run failed only on framing because the narrower arm silhouette triggered a too-close automatic camera fit (`verticalCoverage=0.8533 > 0.80)). The gate was not loosened. A preview-only camera patch changed the fit multiplier from 1.20 to 1.30, increasing distance by ~8.33%. It edits only the temporary preview HTML, not the GLB, repository production viewer, or main branch.
- Final Windows preview ZIP: `ly-lam-lam-v385-experimental-windows.zip`, `15,079,676` bytes, 81 entries, ZIP integrity passed.
- Windows ZIP SHA-256: `ba8963e96db21716bccbed1e7f4d6dbb29601999fc1b956114b3df8c746498bb`, independently recomputed and matched the included sidecar.

## Visual decision / remaining work

- **Pose:** accept V385 as the current arm/wrist continuity candidate. Front and three-quarter renders no longer show the long finger streaks seen in V384.
- **Overall avatar:** NOT APPROVED as final. The face is still generic compared with Phi's saved Lam reference. The top still reads as a short-sleeved crop shirt instead of the sleeveless dark-teal top, and the lower garment still reads too much like tight leggings rather than relaxed cargo trousers. Real-world-looking likeness and complete reference wardrobe remain outstanding.
- Next isolated experiment: improve the sleeveless upper-garment silhouette (remove or reshape the short sleeves without damaging the shoulder/torso seam), while preserving V385 face/eyes/iris/hair/necklace, lower-body shape, hands, 12 morphs, and idle animation. Keep changes on a separate candidate branch and use image evidence before any visual approval.
