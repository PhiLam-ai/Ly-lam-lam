# V386-R9 Visual and Technical Review — 2026-10-17

## Source run

- Workflow: [V386-R9 run #80](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38997553610)
- Branch: `avatar/v386-r9-profile-integrated-overlap`
- Build commit: `61902b5dead4bc175425469a3208a01f34f798ad`
- Result: **CI PASS — experimental candidate only; not approved for production**
- Artifact: [download candidate package](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38997553610/artifacts/12087143468)
- GLB: `lam-v386-gltf-materials-full-face-candidate.glb`
- GLB size: 14,653,748 bytes
- GLB SHA-256: `7a118ac0f73bda9d8aeec61db164e72b76d82797d8fe3c071cb5b0e65997e9cc`

## What passed

- Blender 4.5.3 build and render completed.
- Candidate report, editable `.blend`, GLB and six reference renders were produced.
- Armhole profile validation passed after aligning the smooth-profile tolerance to 0.11 mm; the measured smooth interpolation deviation was previously 0.10021 mm.
- GLB contains 31 mesh nodes, 20 materials, 9 textures, 12 expected facial morph names, and the `Lam_Idle_GentleSway` animation clip.
- Browser smoke test passed at a 390 × 844 viewport: WebGL renderer ready, model request returned HTTP 200, no page/console errors or failed requests, and the avatar fit the tested safe area.
- Face accessory UV/material checks and asset-pack checksum checks passed.

## Visual review of the generated reference renders

The six rendered views show a more coherent, fully dressed human-shaped character than the prior fragmented blockout. The shoulder/armhole contour is smoother and the necklace, hair, eyes and wardrobe textures are present.

However, the candidate is **not photorealistic yet** and must not be described as finished:
- Face and skin still read as a smooth game/CG character, with limited fine skin detail and subtle facial asymmetry.
- Hair reads as broad, relatively uniform strands rather than detailed layered individual hair.
- Hands/fingers and some garment contours still look simplified.
- The current outfit is a cropped short-sleeve top with exposed midriff; confirm this wardrobe is intentional against the saved reference before any final approval.
- Reference renders are useful for diagnosis but are not a likeness approval; compare directly against the saved Lam portrait reference.

## Blocking technical limitation

The report explicitly says `skin_count_gltf = 0` and describes the body as a baked neutral evaluated mesh. The idle clip is a subtle root sway, not a full-body skeletal animation. The source rig diagnostic lists 53 bones, but the exported character is **not skinned to that rig**. Facial morph names exist, but their actual deformations still need individual visual tests in the target viewer.

Thus, the browser smoke test proves loading/rendering only; it does not prove full-body rigging, animation deformation, or photorealism.

## Required next steps

1. Keep `lam-default.glb` on the production branch untouched.
2. Add a dedicated rig/skinning phase to an experimental branch: preserve the armature and valid vertex groups through export, and make the GLB report prove a non-zero skin count and correct skin joints/inverse bind matrices.
3. Validate deformation at shoulders, elbows, wrists, fingers, hips, knees and ankles; check that the armhole trim does not cause tearing when the arms move.
4. Exercise all 12 morph controls individually and in combinations in the browser, especially blinks, jaw/mouth opening, lip shapes and tongue movement.
5. Improve face/skin/hair material realism and compare front, three-quarter, profile and close-up against the reference portrait.
6. Review outfit choice and silhouette before calling the candidate visually approved.
7. Only propose a production swap after technical checks, visual comparison and explicit approval.

## Decision

**Keep V386-R9 as a successful technical candidate build, not an approved avatar.** The next engineering priority is real skeletal skinning and deformation validation, while photorealistic likeness/material work remains open. No production asset was changed by this review.
