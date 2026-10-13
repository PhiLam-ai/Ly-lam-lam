# Stable version registry

The machine-readable pointers are stored in [stable.json](stable.json).

- `current`: most recently promoted candidate.
- `previous`: the prior current candidate, retained for rollback.
- A candidate is promoted only when the manual **LLL Stable Version Promotion** workflow succeeds.
- The workflow creates a source ZIP, checks ZIP integrity, validates the GLB v2 header and declared length, verifies SHA-256, then updates the pointer registry.
- The ZIP is retained as a GitHub Actions artifact for 90 days. The commit SHA in the registry is the durable source-of-truth for rebuilding the same source snapshot.
- A successful package-integrity check is **not** proof that the avatar renders correctly in a browser or on iPhone. Review the relevant app/browser/Blender checks before promoting a candidate.
- Failed promotion must leave the stable registry unchanged because the pointer update occurs only after the candidate checks pass.
- Do not delete the current or previous commit/tag while either is used as a recovery target.
