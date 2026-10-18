# V392 — Face-First Refinement and Visual Acceptance

Status: EXPERIMENTAL / NOT APPROVED  
Branch: `avatar/v388-face-neck-refinement`  
Production: unchanged; do not replace the production GLB from this branch.

## Objective

Refine the face first, as requested, before moving on to hair, body polish, rigging, or mobile integration. Preserve the existing candidate and its outputs as a reproducible baseline.

## Face work order

1. **Overall facial silhouette:** inspect frontal, left/right three-quarter, and side views. Refine forehead-to-nose bridge, cheek volume, jaw taper, chin projection, and face width as one coherent silhouette.
2. **Eyes and brows:** adjust eye size, depth, spacing, height, and brow shape together. Avoid protruding or oversized eyes; check that both eyes sit naturally in the face from all views.
3. **Nose:** refine bridge, tip, nostril width, and projection. The profile must read naturally rather than as a detached primitive.
4. **Mouth and lips:** refine width, lip volume, philtrum, corners, and placement relative to nose and chin. Keep the neutral mouth convincing before adding speech expressions.
5. **Cheeks and jaw transitions:** avoid abrupt intersections between separate feature meshes and head surface. Preserve editability of individual features.
6. **Neutral expression review:** render a consistent lighting/camera set before any expression or rig work.

## Required render set

- Neutral frontal face close-up.
- Left and right three-quarter close-ups.
- Left and right profile close-ups.
- A consistent full-head render for scale and proportion comparison.

Record exact image paths and candidate GLB path in the generated report. Use the same camera framing and lighting across iterations so changes can be compared fairly.

## Acceptance gates — all required

- [ ] Face proportions are coherent in frontal and three-quarter views.
- [ ] Forehead, nose, lips, and chin form a plausible continuous profile.
- [ ] Eyes do not look excessively protruding and remain aligned from all views.
- [ ] Nose, lips, ears, and other features do not visibly float, detach, or intersect incorrectly.
- [ ] Cheek, jaw, and chin transitions are smooth enough for the intended visual style.
- [ ] No visible holes, degenerate geometry, or unexpected facial gaps in the rendered set.
- [ ] A human visual review explicitly approves the neutral face before the project advances to hair/body polish and rigging.

## Guardrails

- Do not infer visual quality from a green CI/workflow result alone.
- Do not claim a render was visually reviewed unless the actual artifact images were opened and inspected.
- Do not transfer rigging or facial morphs until the static face passes visual review.
- Do not modify or replace the production avatar until all required visual, geometry, rig, and viewer checks pass.
- If any gate fails, record the defect, the view where it appears, and the next targeted adjustment; do not declare completion.
