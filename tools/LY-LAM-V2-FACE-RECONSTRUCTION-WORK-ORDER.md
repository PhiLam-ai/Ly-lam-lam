# Lý Lâm Lam — V2 Face Reconstruction Work Order

Status: REQUIRED / NOT YET IMPLEMENTED
Branch: avatar/reference-reconstruction-v1
Production safety: do not modify or replace `lam-default.glb`.

## Non-negotiable reference rule
Use only the two user-selected reference sheets already provided in the project conversation. The everyday dark-teal top / charcoal cargo pants / white sneaker sheet is the identity and outfit reference. The second sheet is a supporting proportion reference. Do not substitute generated mood boards or unrelated faces for the references.

## Why the current candidate fails
The exported front render shows a primitive, egg-shaped face; detached, wire-like hair strips under a cap-like crown; a narrow tube-like neck; small protruding nose geometry; and simplified eye/mouth pieces. This is a visible failure against the selected photographic reference. A successful Blender export, rig audit, or CI run is not evidence of likeness.

## Required V2 implementation
1. Stop treating the current UV sphere plus facial attachments as an acceptable head.
2. Build a continuous face surface with explicit control over forehead, temples, cheek planes, jaw taper, chin, eye sockets, eyelids, nose bridge/alar wings, philtrum and lip volume. Prefer a sculpted source mesh with clean retopology; if that source cannot be made, document the blocker rather than labeling a primitive approximation complete.
3. Reconstruct the long layered hairstyle as a coherent scalp cap plus overlapping, broad hair masses and tapered locks. No exposed handful of uniform tubes as the main hair silhouette. Match the reference hairline, part, side framing, back length and volume from front, three-quarter, profile and rear.
4. Keep eye spacing, almond-shaped lids, iris scale, nose/lip proportions, jaw and chin under reference-led review. Avoid exaggerated anime proportions.
5. Improve neck-to-shoulder transitions and make materials/rendering suitable for judging skin and hair, not only flat workbench shading.
6. Render front, three-quarter, profile and rear views from the actual exported GLB. Produce a side-by-side comparison against the two exact reference images; never use a substitute reference.
7. Test the exported GLB in the web viewer and on iPhone.
8. Leave every visual acceptance field false until an actual visual review passes and the user explicitly approves.

## Acceptance gate
V2 is rejected if any of the following remain: generic/stylized face, cap-like hair, tube-strand silhouette, implausible neck/body transitions, or inability to compare directly against the two chosen references. Keep production `lam-default.glb` unchanged until explicit approval.
