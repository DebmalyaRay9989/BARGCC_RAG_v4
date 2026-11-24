# Security, privacy and scientific limits

## Safeguards implemented

- Token required for protected data and research APIs in the Render Blueprint (`BARG_REQUIRE_TOKEN=1`). Token checks are constant-time comparisons. Secret is not committed.
- No LLM-generated response in the Free RAG path. Retrieved PDF passages remain *untrusted data* and never control tool execution.
- Chat answer snippets and citations are inserted with browser `textContent`, not unsanitized HTML. Security headers restrict scripts and resources to same origin.
- FTS5 queries are sanitized to quoted alphanumeric tokens, bound via prepared SQL parameters and executed against a read-only database.
- PDF sources are not publicly served unless `BARG_PUBLIC_SOURCE_PDFS=1` is explicitly set.
- CSV requests are capped at 3 MB and validated for finite numerical features, valid masks, bounded scores and nonempty views. No arbitrary file execution.
- Dataset sessions are stored in memory with random IDs and a TTL, and can be deleted. Runtime log access is disabled by default to minimize exposure to user URLs.
- One process and bounded dataset sizes reduce free-tier resource risk, but are **not a substitute for real rate limiting**.

## Known gaps

- A shared token is not per-user identity; do not share the token with strangers. There is no login, session isolation, audit log, MFA, revocation list or tenant management.
- No per-IP rate limiting or bot protection. Do not publicly advertise the live URL to untrusted users with the token.
- Uploaded CSV sessions are in process memory only. They are lost on Render spin-down or restart; no persistence, backups, deletion attestation or data tenancy guarantees.
- If you make the Git repository public, its `knowledge_sources/` PDFs are public even if `BARG_PUBLIC_SOURCE_PDFS=0`. **Use a private repository** if authors have not authorized public disclosure.
- Library scientific dependencies are version-bounded rather than locked to hashes. For regulated/production use, pin audited dependency versions, run SCA and security testing, and replace shared-token auth.
- Do not accept confidential datasets, private medical information, or licensed PDF sources for public use.

## Scientific limits

- The mask and gate implement fixed numerical features, not the full neural encoder training in the paper.
- `κ=0` is the availability-only comparator; changing κ reweights observed views, not necessarily semantic importance.
- Scores in CSVs are unvalidated proxies unless separately demonstrated. The demo uses derived views of the same public Digits images.
- The one-refit stability certificate is a sufficient geometric condition under its stated hypotheses, not an optimizer-convergence proof, a global optimum guarantee, or a semantic prediction guarantee.
- An inconclusive certificate does **not** imply a changed assignment. The coverage for actually dropped rows is essential; overall percentages alone can be misleading.
- The current upload's external ARI, if computed, is a descriptive transductive comparison, not a statistically established superiority result or independently evaluated deep-learning system.
- The RAG index is strictly an explanation layer grounded in the author's PDFs. It cannot upgrade unverified experimental results or prove scientific novelty.

## Recommended next steps before external launch

Use a private repo and access token; run code audit and dependency scanning; restrict who receives the token; use small, non-sensitive CSVs; independently evaluate the manuscript's quality proxies; and obtain author approval for any source PDF disclosure. Validate future neural and operator-like baselines on independent data before claiming operational reliability.
