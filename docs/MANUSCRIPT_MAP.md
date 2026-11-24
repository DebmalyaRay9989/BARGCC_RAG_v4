# BARG-CC manuscript-to-application research map

Reference: user-provided *BARG-CC: reliability-constrained information fusion with certified view-loss stability and failure diagnostics*, corrected November 2026 IJSS draft.

| Paper | App implementation | In-scope guarantee | Excluded scope |
|---|---|---|---|
| §3, availability `aᵢᵐ`, scores `rᵢᵐ` | `core.from_csv` | Binary present mask, real-valued scores in [0,1], reject all-missing | No inference of why a view disappeared |
| §4.1, Eq. (2) | `core.masked_gate` | Numerically stable masked-softmax, zero absent weight, normalization | No learned quality predictor or semantic calibration |
| §4.1, share floor Proposition 2 | `core.floor_bound`, config cap | For M observed views with floor ρ, κ≤0.5 log((1/ρ−1)/(M−1)) | If enforcement off, floor is not guaranteed |
| §4.4, block geometry | `core.fuse` | Distinct view subspaces | Unit-norm blocks used for mask-switch mechanism, not common-space sum fusion |
| §4.9, Eq. (22) | `core.view_loss_audit` | Exact `√[2(1−√(1−q))]` distance under nonempty view removal, fixed logits, unit-norm blocks | No new view, encoder retraining, score drift or residual modulation |
| §4.9, Eq. (24) | `core.view_loss_audit` | Sufficient one-step membership-preserving Lloyd centroid-refit certificate | Not arbitrary Lloyd iterations or global optimum |
| Baseline-first empirical analysis | `core.analyze` | Same data + random seed for availability-only and gated K-means | Descriptive, transductive; no confidence interval or causal superiority |
| Independent audit bar, Figure 1 | `agent.run_agent` and dashboard | Transparent trace, conditional warnings, no silent promotion | No automatically learned or verified new claims |

## Important source evidence and known weakness

In the manuscript's archive-based Digits pseudo-view audit at 10% view-loss probability, **77.1% of all rows** are certified but **none of the 189 actually dropped rows** are certified. These archival percentages are not hardcoded as live application results: the app recomputes metrics on the currently loaded data. The live demo represents a smaller, separate exploratory demonstration, **not a replication of archived IJSS figures**.

The manuscript warns that gate weighting may degrade semantic utility, even with sensible-looking geometric proxies. Accordingly, default recommendations explicitly prioritize matched availability-only controls; positive ARI change in an upload is not treated as validated deployment benefit.

## Definition of 'agentic' here

A bounded orchestrator performs a multi-step plan, calls real analytical tools, checks preconditions and proof scope, and produces an evidence trail and next-step decision. This is agentic workflow **without a language model**. An optional local Ollama model may be configured to explain summaries, but it cannot execute tools or alter proof results. No hosted LLM provider is configured by default. Hooks can be added later, but a model-mediated free-form control loop would require prompt-injection defenses, permissions, evaluations and user consent.
