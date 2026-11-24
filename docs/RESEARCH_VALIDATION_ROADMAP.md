# Research validation and quality roadmap (proposed; not executed experiments)

## What current package implements
- Masked gate, κ=0 comparison, share floor cap, block fusion
- Exact dropped-view geometry and one-refit certificate
- Source-cited RAG, bounded profile/compare/certify/assess tool chain
- Transductive numerical preprocessing and exploratory validation metrics

## Steps required before empirical superiority claims
1. Collect or permission genuine independently acquired information views, documenting modalities and acquisition.
2. Use subject-level independent train/validation/test splits; fit every normalizer and quality predictor without test leakage.
3. Evaluate strong, matched availability-only and reliability-aware specialist baselines, identical encoders and information budgets.
4. Calibrate or externally justify reliability score predictions under real corruptions; measure quality ranking and OOD drift.
5. Repeat across seeds, missingness families and domain shifts; report paired confidence intervals and failure cases.
6. Report affected-only certification coverage, non-certification, and false-certificate checks separately from all-record aggregate coverage.
7. Run independent fairness, privacy, security and deployment load tests before real users upload sensitive data.

The original paper's 77.1% all-record and 0% affected-record Digits certifications remain historical reported values. This project does not regenerate those published results as an independent replication.
