# Version 3.0 verified changes

1. Replaces legacy V1 interface with boot-tested multi-tab Research Studio.
2. Removes ambiguity in cluster-label agreement: uses optimal one-to-one label matching; preserves raw ID agreement as diagnostic.
3. Adds `/api/source-private/{doc_id}` authenticated download for citation-to-page navigation; no anonymous PDFs.
4. Adds `/api/self-test` with exact-zero, uniform baseline, participation floor, view-loss and RAG checks; not scientific validation.
5. Adds `/api/evidence.zip` (scope README, JSON, PDF, capped 150 affected-row audit entries).
6. Adds `Run system check`, protected PDF buttons, `Evidence ZIP`, focus-visible navigation and reduced-motion support.
7. Preserves Render Free Blueprint, private-indexed PDF sources, single worker and fail-closed token environment.
8. Adds explicit guidance about private source control, ephemeral storage and the paid-plan gate for *new* HF Docker Spaces.

## Explicit limitations

- No trained neural encoders, independently validated quality scores or semantic reliability guarantees.
- JSON reflects only this run; the ZIP's CSV ledger is capped at first 150 affected records.
- Hosted server is a shared-token research demo with in-memory sessions; there are no per-user accounts.
- A successful self-test checks internal identities, not theoretical generalization or deployment safety.
- No cloud deployment is claimed until actually performed.
