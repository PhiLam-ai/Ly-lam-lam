# Lý Lâm Lam — Reference Reconstruction V1

## Goal
Rebuild the experimental character from the user's two selected reference sheets. This is a new reconstruction track, not approval of the existing procedural blockout.

## Reference hierarchy
1. **Primary identity/outfit reference:** the second uploaded sheet, showing long black layered hair, warm brown eyes, soft East Asian facial proportions, a dark teal fitted crop top, charcoal cargo trousers, and white sneakers.
2. **Body proportion reference:** the first uploaded sheet for front/side/back body continuity and long-hair length. The bikini is a proportion reference only; the everyday outfit should follow reference 1 above.
3. Preserve the chosen identity's face silhouette, eye spacing and shape, nose bridge/tip, lip shape, jaw/chin, hairline, and long layered hair. Do not treat an unrelated generated image as the final character.

## Modeling plan
- V1: revise the experimental Blender builder to follow the everyday outfit palette and add layered hair flow/detail. Produce a fresh GLB and front/three-quarter/profile face renders.
- V2: replace the simple ellipsoid head with a deliberately sculpted, topology-aware face surface; shape the eye sockets, eyelids, nose, lips, cheek planes, jaw and chin against the reference.
- V3: build separate layered hair clumps/strands with natural direction, volume and silhouette; review front, three-quarter, profile and rear.
- V4: improve hands, feet, shoulder/hip transitions and garment tailoring; then refine rig weights and facial morphs.
- V5: test the actual exported GLB in the web viewer and on iPhone.

## Acceptance gates
- Visual comparison uses the user's reference images, not generic style examples.
- Review at least front, three-quarter and profile, plus expression close-ups.
- Verify GLB export, rig/morph deformation and web/mobile display independently.
- Keep `lam-default.glb` unchanged until the user approves a candidate after visual review.
- A passing CI workflow proves build/audit success only; it does not prove photorealism or user acceptance.

## Known limitation
The current procedural candidate is still a blockout. V1 is an incremental reconstruction pass, not a claim of exact likeness. If the procedural surface cannot reproduce the reference face closely enough, use a dedicated sculpt/retopology workflow rather than endlessly tweaking primitive sizes.


## Mandatory visual acceptance gate (added 2026-10-18)
The current procedural blockout is explicitly **NOT APPROVED**. CI must fail the release gate until all of the following are true: the face matches the selected reference in front, three-quarter and profile; the hair silhouette and layers look natural; anatomy and proportions are credible; skin/eyes and expressions are reviewed; the exported GLB is checked in the web viewer and on iPhone; and the user explicitly approves the candidate. Passing geometry, rig, export or render tests is not visual approval. The production `lam-default.glb` must remain unchanged until all criteria pass.
